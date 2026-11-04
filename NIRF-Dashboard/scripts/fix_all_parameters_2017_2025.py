
import re
import time
import shutil
import pandas as pd

from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==========================================
# STEP 1: CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

# Only these two columns will be updated
UPDATE_COLUMNS = ["oi", "pr"]

# Backup folder
BACKUP_DIR = (
    PROJECT_DIR / "data" /
    f"backup_oi_pr_{datetime.now():%Y%m%d_%H%M%S}"
)

# Direct category URL fallback
CATEGORY_URLS = {
    "overall": "OverallRanking.html",
    "universities": "UniversityRanking.html",
    "colleges": "CollegeRanking.html",
    "engineering": "EngineeringRanking.html",
    "management": "ManagementRanking.html",
    "pharmacy": "PharmacyRanking.html",
    "medical": "MedicalRanking.html",
    "architecture": "ArchitectureRanking.html",
    "architecture_and_planning": "ArchitectureRanking.html",
    "law": "LawRanking.html",
    "dental": "DentalRanking.html",
    "agriculture": "AgricultureRanking.html",
    "agriculture_and_allied_sectors": "AgricultureRanking.html",
    "research": "ResearchRanking.html",
    "research_institutions": "ResearchRanking.html",
    "innovation": "InnovationRanking.html",
    "state_public_universities": "StatePublicUniversityRanking.html",
    "open_universities": "OpenUniversityRanking.html",
    "skill_universities": "SkillRanking.html",
    "sdgs_institutions": "SDGRanking.html",
}


# ==========================================
# STEP 2: BASIC FUNCTIONS
# ==========================================

def get_text(element):
    return " ".join(
        (element.get_attribute("textContent") or "").split()
    )


def to_float(value):

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        str(value).replace(",", "")
    )

    if not match:
        return None

    try:
        number = float(match.group())

        if 0 <= number <= 100:
            return number

        return None

    except ValueError:
        return None


def get_source_url(df, file_path, year):

    if "source_url" in df.columns:

        for value in df["source_url"].dropna():

            match = re.search(
                r"https?://[^\s)\]]+",
                str(value)
            )

            if match:
                return match.group(0).rstrip(".,]")

    slug = file_path.stem.replace(
        f"nirf_{year}_", "", 1
    )

    page = CATEGORY_URLS.get(slug)

    if page:
        return (
            f"https://www.nirfindia.org/"
            f"Rankings/{year}/{page}"
        )

    return None


# ==========================================
# STEP 3: FIND PARAMETER TABLE
# ==========================================

def extract_oi_pr(driver, main_row):

    # Find the expanded detail row after the institution row
    detail_rows = [main_row]

    siblings = main_row.find_elements(
        By.XPATH,
        "following-sibling::tr[position() <= 6]"
    )

    for sibling in siblings:

        cells = sibling.find_elements(
            By.XPATH, "./td"
        )

        # Stop when next institution row starts
        if len(cells) >= 6:
            break

        detail_rows.append(sibling)

    table_rows = []

    for element in detail_rows:

        # Include a row itself if it is a TR
        if element.tag_name.lower() == "tr":

            cells = element.find_elements(
                By.XPATH, "./th | ./td"
            )

            if cells:
                table_rows.append(
                    [get_text(cell) for cell in cells]
                )

        # Include nested detail table rows
        nested_rows = element.find_elements(
            By.XPATH, ".//tr"
        )

        for tr in nested_rows:

            cells = tr.find_elements(
                By.XPATH, "./th | ./td"
            )

            if cells:
                table_rows.append(
                    [get_text(cell) for cell in cells]
                )

    # Locate parameter heading positions
    for index, headers in enumerate(table_rows):

        positions = {}

        for i, heading in enumerate(headers):

            heading = re.sub(
                r"[^A-Z]",
                "",
                heading.upper()
            )

            if "TLR" in heading:
                positions["tlr"] = i

            if "RPC" in heading:
                positions["rpc"] = i

            if heading.startswith("GO"):
                positions["go"] = i

            if "OUTREACH" in heading or heading.startswith("OI"):
                positions["oi"] = i

            if "PERCEPTION" in heading:
                positions["pr"] = i

        if len(positions) != 5:
            continue

        # Read the corresponding numeric row
        for value_row in table_rows[index + 1:index + 5]:

            oi_position = positions["oi"]
            pr_position = positions["pr"]

            if (
                oi_position >= len(value_row)
                or pr_position >= len(value_row)
            ):
                continue

            oi = to_float(value_row[oi_position])
            pr = to_float(value_row[pr_position])

            if oi is not None and pr is not None:

                return {
                    "oi": oi,
                    "pr": pr
                }

    # Fallback: inspect expanded row text
    full_text = " ".join(
        get_text(element)
        for element in detail_rows
    )

    header_pattern = re.compile(
        r"TLR\s*\(\s*100\s*\).*?"
        r"RPC\s*\(\s*100\s*\).*?"
        r"GO\s*\(\s*100\s*\).*?"
        r"OI\s*\(\s*100\s*\).*?"
        r"PERCEPTION\s*\(\s*100\s*\)",
        re.IGNORECASE
    )

    header = header_pattern.search(full_text)

    if header:

        remaining = full_text[header.end():]

        numbers = re.findall(
            r"\d+(?:\.\d+)?",
            remaining
        )

        if len(numbers) >= 5:

            values = [float(x) for x in numbers[:5]]

            if all(0 <= x <= 100 for x in values):

                return {
                    "oi": values[3],
                    "pr": values[4]
                }

    return None


# ==========================================
# STEP 4: COLLECT OI AND PR FROM ONE PAGE
# ==========================================

def collect_oi_pr(driver, url):

    print("\nOpening:", url)

    driver.get(url)

    table = WebDriverWait(driver, 25).until(
        EC.presence_of_element_located(
            (By.ID, "tbl_overall")
        )
    )

    time.sleep(1)

    rows = table.find_elements(
        By.CSS_SELECTOR,
        "tbody > tr"
    )

    institution_ids = []

    for row in rows:

        cells = row.find_elements(
            By.XPATH, "./td"
        )

        if len(cells) >= 6:

            institution_id = get_text(cells[0])

            if institution_id:
                institution_ids.append(institution_id)

    fresh_data = {}

    for institution_id in institution_ids:

        try:

            row = table.find_element(
                By.XPATH,
                ".//tbody/tr[td[1][normalize-space()="
                f"'{institution_id}']]"
            )

            # Click More Details
            buttons = row.find_elements(
                By.CSS_SELECTOR,
                "a, button"
            )

            for button in buttons:

                if "more details" in get_text(button).lower():

                    driver.execute_script(
                        "arguments[0].click();",
                        button
                    )

                    time.sleep(0.3)
                    break

            values = extract_oi_pr(
                driver,
                row
            )

            if values is not None:
                fresh_data[institution_id] = values

        except Exception as error:

            print(
                "Could not process:",
                institution_id,
                str(error)[:80]
            )

    print("Institutions found:", len(institution_ids))
    print("Valid OI/PR records:", len(fresh_data))

    return fresh_data


# ==========================================
# STEP 5: UPDATE EXISTING CSV FILE
# ==========================================

def update_csv(driver, file_path):

    year = int(file_path.parent.name)

    print("\n" + "=" * 55)
    print("YEAR:", year)
    print("FILE:", file_path.name)

    df = pd.read_csv(
        file_path,
        dtype={"institution_id": str}
    )

    if "institution_id" not in df.columns:
        print("Institution ID missing. Skipping.")
        return False

    if not set(UPDATE_COLUMNS).issubset(df.columns):
        print("OI or PR column missing. Skipping.")
        return False

    url = get_source_url(
        df,
        file_path,
        year
    )

    if not url:
        print("Source URL not found. Skipping.")
        return False

    fresh_data = collect_oi_pr(
        driver,
        url
    )

    if not fresh_data:
        print("No valid values. Existing file retained.")
        return False

    ids = df["institution_id"].astype(str).str.strip()

    updated_counts = {}

    new_oi = ids.map({
        key: value["oi"]
        for key, value in fresh_data.items()
    })

    new_pr = ids.map({
        key: value["pr"]
        for key, value in fresh_data.items()
    })

    for column, new_values in [
        ("oi", new_oi),
        ("pr", new_pr)
    ]:

        valid_mask = new_values.notna()

        updated_counts[column] = int(
            valid_mask.sum()
        )

        df.loc[valid_mask, column] = (
            new_values[valid_mask].values
        )

    if sum(updated_counts.values()) == 0:
        print("No matching records. File not changed.")
        return False

    # Create backup
    backup_file = (
        BACKUP_DIR /
        str(year) /
        file_path.name
    )

    backup_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        file_path,
        backup_file
    )

    # Overwrite the SAME original file
    temp_file = file_path.with_name(
        file_path.stem + "_temp.csv"
    )

    df.to_csv(
        temp_file,
        index=False,
        encoding="utf-8-sig"
    )

    temp_file.replace(file_path)

    print("OI records updated:", updated_counts["oi"])
    print("PR records updated:", updated_counts["pr"])
    print("Existing CSV overwritten successfully.")

    return True


# ==========================================
# STEP 6: PROCESS BOTH YEAR GROUPS
# ==========================================

def main():

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        options=options
    )

    total_files = 0

    try:

        groups = [
            ("GROUP 1: 2017–2020", range(2017, 2021)),
            ("GROUP 2: 2021–2025", range(2021, 2026))
        ]

        for group_name, years in groups:

            print("\n\n")
            print("#" * 55)
            print(group_name)
            print("#" * 55)

            for year in years:

                year_folder = RAW_DIR / str(year)

                if not year_folder.exists():
                    print("Folder not found:", year)
                    continue

                files = sorted(
                    year_folder.glob(f"nirf_{year}_*.csv")
                )

                print(
                    f"\n{year}: {len(files)} CSV files"
                )

                for file_path in files:

                    if update_csv(driver, file_path):
                        total_files += 1

        print("\n" + "=" * 55)
        print("OI AND PR UPDATE COMPLETED")
        print("Files updated:", total_files)
        print("Backup folder:", BACKUP_DIR)
        print("=" * 55)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
