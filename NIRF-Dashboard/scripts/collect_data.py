
import re
import time
import pandas as pd

from pathlib import Path
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT / "data" / "raw"

YEARS = range(2018, 2026)

RAW_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_NAMES = {
    "OverallRanking.html": "Overall",
    "UniversityRanking.html": "Universities",
    "CollegeRanking.html": "Colleges",
    "EngineeringRanking.html": "Engineering",
    "ManagementRanking.html": "Management",
    "PharmacyRanking.html": "Pharmacy",
    "MedicalRanking.html": "Medical",
    "ArchitectureRanking.html": "Architecture and Planning",
    "LawRanking.html": "Law",
    "DentalRanking.html": "Dental",
    "AgricultureRanking.html": "Agriculture and Allied Sectors",
    "ResearchRanking.html": "Research Institutions",
    "InnovationRanking.html": "Innovation",
    "StatePublicUniversityRanking.html": "State Public Universities",
    "OpenUniversityRanking.html": "Open Universities",
    "SkillRanking.html": "Skill Universities",
    "SDGRanking.html": "SDGs Institutions"
}


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def get_text(element):
    return " ".join(
        (element.get_attribute("textContent") or "").split()
    )


def to_float(value):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def extract_parameters(text):

    # Find parameter values after the last parameter heading
    match = re.search(
        r"PERCEPTION\s*\(\s*100\s*\)(.*)",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return [None] * 5

    values = re.findall(
        r"\d+(?:\.\d+)?",
        match.group(1)
    )

    if len(values) < 5:
        return [None] * 5

    return [float(x) for x in values[:5]]


# ==========================================
# 3. DISCOVER AVAILABLE CATEGORIES
# ==========================================

def discover_categories(driver, year):

    index_url = (
        f"https://www.nirfindia.org/"
        f"Rankings/{year}/Ranking.html"
    )

    print(f"\nChecking categories for {year}...")

    try:
        driver.get(index_url)
        time.sleep(2)

        links = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href]"
        )

        categories = {}

        for link in links:

            href = link.get_attribute("href")

            if not href:
                continue

            filename = Path(
                urlparse(href).path
            ).name

            if (
                filename in CATEGORY_NAMES
                and f"/{year}/" in urlparse(href).path
            ):

                categories[filename] = {
                    "name": CATEGORY_NAMES[filename],
                    "url": href
                }

        # Fallback if category directory links
        # cannot be discovered automatically
        if not categories:

            print("Using category URL fallback.")

            for filename, name in CATEGORY_NAMES.items():

                categories[filename] = {
                    "name": name,
                    "url": (
                        f"https://www.nirfindia.org/"
                        f"Rankings/{year}/{filename}"
                    )
                }

        return categories

    except Exception as error:

        print("Category discovery failed:", error)

        return {}


# ==========================================
# 4. EXTRACT ONE RANKING PAGE
# ==========================================

def extract_ranking_page(driver, year, category, url):

    print(f"Collecting {year} - {category}")

    try:

        driver.get(url)

        wait = WebDriverWait(driver, 20)

        table = wait.until(
            EC.presence_of_element_located(
                (By.ID, "tbl_overall")
            )
        )

        time.sleep(2)

        rows = table.find_elements(
            By.CSS_SELECTOR,
            "tbody > tr"
        )

        records = []

        for i, row in enumerate(rows):

            # IMPORTANT: ./td selects only direct cells.
            # It does not include nested detail-table cells.
            cells = row.find_elements(
                By.XPATH,
                "./td"
            )

            if len(cells) < 6:
                continue

            institute_id = get_text(cells[0])

            if not institute_id:
                continue

            # Main ranking columns
            name_text = get_text(cells[1])

            institution_name = re.split(
                r"More Details|Close|TLR\s*\(\s*100\s*\)",
                name_text,
                flags=re.IGNORECASE
            )[0].strip()

            city = get_text(cells[2])
            state = get_text(cells[3])

            score = to_float(get_text(cells[4]))

            rank_text = get_text(cells[5])

            rank = (
                int(rank_text)
                if rank_text.isdigit()
                else None
            )

            # Collect expanded detail information
            detail_text = get_text(row)

            # Details can be stored in the following
            # expandable child row.
            j = i + 1

            while j < len(rows):

                next_cells = rows[j].find_elements(
                    By.XPATH,
                    "./td"
                )

                if len(next_cells) >= 6:
                    break

                detail_text += " " + get_text(rows[j])
                j += 1

            # Extract five aggregate NIRF parameters
            tlr, rpc, go, oi, pr = extract_parameters(
                detail_text
            )

            records.append({

                "year": year,
                "category": category,
                "institution_id": institute_id,
                "institution_name": institution_name,
                "city": city,
                "state": state,
                "overall_score": score,
                "rank": rank,
                "rank_original": rank_text,
                "tlr": tlr,
                "rpc": rpc,
                "go": go,
                "oi": oi,
                "pr": pr,
                "source_url": url

            })

        if not records:
            print("No ranking records extracted.")
            return []

        df = pd.DataFrame(records)

        # Save individual category CSV
        category_file = re.sub(
            r"[^a-z0-9]+",
            "_",
            category.lower()
        ).strip("_")

        year_dir = RAW_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        file_path = (
            year_dir /
            f"nirf_{year}_{category_file}.csv"
        )

        df.to_csv(
            file_path,
            index=False,
            encoding="utf-8-sig"
        )

        missing_parameters = df[
            ["tlr", "rpc", "go", "oi", "pr"]
        ].isna().all(axis=1).sum()

        print("Records:", len(df))
        print("Saved:", file_path)
        print("Rows missing all parameters:", missing_parameters)

        return records

    except Exception as error:

        print(f"Failed: {year} - {category}")
        print("Reason:", error)

        return []


# ==========================================
# 5. MAIN DATA COLLECTION
# ==========================================

def main():

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    all_records = []

    try:

        for year in YEARS:

            categories = discover_categories(
                driver,
                year
            )

            print(
                f"Categories discovered: {len(categories)}"
            )

            for filename, information in categories.items():

                category = information["name"]
                url = information["url"]

                records = extract_ranking_page(
                    driver,
                    year,
                    category,
                    url
                )

                all_records.extend(records)

        # Save combined master dataset
        if all_records:

            master = pd.DataFrame(all_records)

            master = master.drop_duplicates(
                subset=[
                    "year",
                    "category",
                    "institution_id"
                ]
            )

            master_file = (
                RAW_DIR /
                "nirf_2017_2025_raw.csv"
            )

            master.to_csv(
                master_file,
                index=False,
                encoding="utf-8-sig"
            )

            print("\n================================")
            print("COLLECTION FINISHED")
            print("================================")

            print("Total records:", len(master))
            print(
                "Total categories:",
                master["category"].nunique()
            )

            print(
                "Parameter missing values:\n",
                master[
                    ["tlr", "rpc", "go", "oi", "pr"]
                ].isna().sum()
            )

            print("Master file:", master_file)

        else:

            print("No data collected. Check website URLs.")

    finally:

        driver.quit()


if __name__ == "__main__":
    main()
