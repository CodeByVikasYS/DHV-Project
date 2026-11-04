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


# ---------------- CONFIGURATION ----------------

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"

YEARS = range(2017, 2026)

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
    "SDGRanking.html": "SDGs Institutions",
}


# ---------------- HELPER FUNCTIONS ----------------

def get_text(element):
    return " ".join((element.get_attribute("textContent") or "").split())


def to_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def extract_parameter_table(row):
    """
    Extract parameter scores from the expanded details table.
    Expected columns: TLR, RPC, GO, OI, PERCEPTION.
    """

    result = {
        "tlr": None,
        "rpc": None,
        "go": None,
        "oi": None,
        "pr": None,
    }

    tables = row.find_elements(By.TAG_NAME, "table")

    # Some NIRF pages may place the details in the next row.
    try:
        next_row = row.find_element(
            By.XPATH, "following-sibling::tr[1]"
        )
        tables.extend(next_row.find_elements(By.TAG_NAME, "table"))
    except Exception:
        pass

    for table in tables:
        rows = table.find_elements(By.TAG_NAME, "tr")

        for table_row in rows:
            cells = table_row.find_elements(
                By.XPATH, "./th | ./td"
            )

            headings = [get_text(cell).upper() for cell in cells]

            if not any("TLR" in heading for heading in headings):
                continue

            # Find the next row containing the parameter values.
            for value_row in rows[rows.index(table_row) + 1:]:
                value_cells = value_row.find_elements(
                    By.XPATH, "./th | ./td"
                )

                values = [get_text(cell) for cell in value_cells]

                if len(values) < 5:
                    continue

                result["tlr"] = to_float(values[0])
                result["rpc"] = to_float(values[1])
                result["go"] = to_float(values[2])
                result["oi"] = to_float(values[3])
                result["pr"] = to_float(values[4])

                return result

    return result


def discover_categories(driver, year):
    index_url = (
        f"https://www.nirfindia.org/Rankings/{year}/Ranking.html"
    )

    print(f"\nChecking categories for {year}...")

    try:
        driver.get(index_url)
        time.sleep(2)

        categories = {}

        for link in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = link.get_attribute("href")

            if not href:
                continue

            filename = Path(urlparse(href).path).name

            if (
                filename in CATEGORY_NAMES
                and f"/{year}/" in urlparse(href).path
            ):
                categories[filename] = {
                    "name": CATEGORY_NAMES[filename],
                    "url": href,
                }

        if not categories:
            print("No categories discovered for this year.")

        return categories

    except Exception as error:
        print("Category discovery failed:", error)
        return {}


# ---------------- EXTRACT ONE RANKING PAGE ----------------

def extract_ranking_page(driver, year, category, url):
    print(f"Collecting {year} - {category}")

    records = []

    try:
        driver.get(url)

        wait = WebDriverWait(driver, 20)

        table = wait.until(
            EC.presence_of_element_located((By.ID, "tbl_overall"))
        )

        time.sleep(2)

        rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")

        for row in rows:
            cells = row.find_elements(By.XPATH, "./td")

            # Main ranking rows contain at least six cells.
            if len(cells) < 6:
                continue

            institution_id = get_text(cells[0])

            if not institution_id:
                continue

            name_cell = cells[1]

            institution_name = get_text(name_cell)
            institution_name = re.split(
                r"More Details|Close",
                institution_name,
                flags=re.IGNORECASE,
            )[0].strip()

            city = get_text(cells[2])
            state = get_text(cells[3])

            overall_score = to_float(get_text(cells[4]))
            rank_text = get_text(cells[5])

            rank = int(rank_text) if rank_text.isdigit() else None

            # Open the institution's parameter details.
            try:
                details_link = name_cell.find_element(
                    By.XPATH,
                    ".//*[contains(normalize-space(text()), "
                    "'More Details')]",
                )
                driver.execute_script(
                    "arguments[0].click();", details_link
                )
                time.sleep(0.4)
            except Exception:
                # Details may already be expanded or unavailable.
                pass

            parameters = extract_parameter_table(row)

            records.append({
                "year": year,
                "category": category,
                "institution_id": institution_id,
                "institution_name": institution_name,
                "city": city,
                "state": state,
                "overall_score": overall_score,
                "rank": rank,
                "rank_original": rank_text,
                "tlr": parameters["tlr"],
                "rpc": parameters["rpc"],
                "go": parameters["go"],
                "oi": parameters["oi"],
                "pr": parameters["pr"],
                "source_url": url,
            })

        if not records:
            print("No ranking records extracted.")
            return []

        df = pd.DataFrame(records)

        category_file = re.sub(
            r"[^a-z0-9]+",
            "_",
            category.lower(),
        ).strip("_")

        year_dir = RAW_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        file_path = year_dir / f"nirf_{year}_{category_file}.csv"

        df.to_csv(
            file_path,
            index=False,
            encoding="utf-8-sig",
        )

        missing_count = df[
            ["tlr", "rpc", "go", "oi", "pr"]
        ].isna().all(axis=1).sum()

        print("Records:", len(df))
        print("Saved:", file_path)
        print("Rows missing all parameters:", missing_count)

        return records

    except Exception as error:
        print(f"Failed: {year} - {category}")
        print("Reason:", error)
        return []


# ---------------- MAIN COLLECTION ----------------

def main():
    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    all_records = []

    try:
        for year in YEARS:
            categories = discover_categories(driver, year)

            print("Categories discovered:", len(categories))

            for information in categories.values():
                category = information["name"]
                url = information["url"]

                records = extract_ranking_page(
                    driver,
                    year,
                    category,
                    url,
                )

                all_records.extend(records)

        if all_records:
            master = pd.DataFrame(all_records)

            master = master.drop_duplicates(
                subset=["year", "category", "institution_id"]
            )

            master_file = RAW_DIR / "nirf_2017_2025_raw.csv"

            master.to_csv(
                master_file,
                index=False,
                encoding="utf-8-sig",
            )

            print("\n========== COLLECTION FINISHED ==========")
            print("Total records:", len(master))
            print("Total categories:", master["category"].nunique())

            print(
                "Missing parameter values:\n",
                master[["tlr", "rpc", "go", "oi", "pr"]].isna().sum(),
            )

            print("Master file:", master_file)

        else:
            print("No data collected. Check the website URLs.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()