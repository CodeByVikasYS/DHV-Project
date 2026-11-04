
import re
import shutil
from datetime import datetime

import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Import the tested extraction function
from collect_data import (
    RAW_DIR,
    CATEGORY_NAMES,
    extract_ranking_page
)


# ==========================================
# STEP 1: CATEGORY LISTS
# ==========================================

YEAR_CATEGORIES = {
    2017: [
        "OverallRanking.html",
        "CollegeRanking.html",
        "EngineeringRanking.html",
        "ManagementRanking.html",
        "PharmacyRanking.html"
    ],

    2018: [
        "OverallRanking.html",
        "UniversityRanking.html",
        "CollegeRanking.html",
        "EngineeringRanking.html",
        "ManagementRanking.html",
        "PharmacyRanking.html",
        "MedicalRanking.html",
        "ArchitectureRanking.html",
        "LawRanking.html"
    ],

    2019: [
        "OverallRanking.html",
        "UniversityRanking.html",
        "CollegeRanking.html",
        "EngineeringRanking.html",
        "ManagementRanking.html",
        "PharmacyRanking.html",
        "MedicalRanking.html",
        "ArchitectureRanking.html",
        "LawRanking.html"
    ],

    2020: [
        "OverallRanking.html",
        "UniversityRanking.html",
        "CollegeRanking.html",
        "EngineeringRanking.html",
        "ManagementRanking.html",
        "PharmacyRanking.html",
        "MedicalRanking.html",
        "ArchitectureRanking.html",
        "LawRanking.html",
        "DentalRanking.html"
    ]
}


PROJECT_DIR = Path(__file__).resolve().parent.parent

# Backup folder
BACKUP_DIR = (
    PROJECT_DIR / "data" /
    f"backup_rpc_go_{datetime.now():%Y%m%d_%H%M%S}"
)


# ==========================================
# STEP 2: HELPER FUNCTION
# ==========================================

def category_slug(category):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        category.lower()
    ).strip("_")


# ==========================================
# STEP 3: MAIN FUNCTION
# ==========================================

def main():

    # Start browser
    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    total_updated = 0

    try:

        for year, filenames in YEAR_CATEGORIES.items():

            print("\n" + "=" * 55)
            print("PROCESSING YEAR:", year)
            print("=" * 55)

            for filename in filenames:

                category = CATEGORY_NAMES[filename]

                year_dir = RAW_DIR / str(year)

                csv_file = (
                    year_dir /
                    f"nirf_{year}_{category_slug(category)}.csv"
                )

                # Only update existing CSV files
                if not csv_file.exists():
                    print("File not found. Skipping:", csv_file.name)
                    continue

                # ----------------------------------
                # Load existing data into memory
                # ----------------------------------

                old_df = pd.read_csv(csv_file)

                old_df["institution_id"] = (
                    old_df["institution_id"].astype(str).str.strip()
                )

                if not {"rpc", "go"}.issubset(old_df.columns):
                    print("RPC/GO columns missing. Skipping.")
                    continue

                # ----------------------------------
                # Create backup before overwrite
                # ----------------------------------

                backup_file = (
                    BACKUP_DIR / str(year) / csv_file.name
                )

                backup_file.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(csv_file, backup_file)

                # ----------------------------------
                # Collect fresh official data
                # ----------------------------------

                url = (
                    f"https://www.nirfindia.org/"
                    f"Rankings/{year}/{filename}"
                )

                print("\nCategory:", category)
                print("Collecting:", url)

                records = extract_ranking_page(
                    driver,
                    year,
                    category,
                    url
                )

                if not records:
                    print("No fresh data. Existing values retained.")
                    shutil.copy2(backup_file, csv_file)
                    continue

                fresh_df = pd.DataFrame(records)

                fresh_df["institution_id"] = (
                    fresh_df["institution_id"].astype(str).str.strip()
                )

                # ----------------------------------
                # Update only RPC and GO
                # ----------------------------------

                updated_counts = {}

                for column in ["rpc", "go"]:

                    fresh_df[column] = pd.to_numeric(
                        fresh_df[column],
                        errors="coerce"
                    )

                    # Accept only values between 0 and 100
                    valid_values = fresh_df[
                        fresh_df[column].between(0, 100)
                    ][["institution_id", column]]

                    valid_values = valid_values.drop_duplicates(
                        subset="institution_id",
                        keep="last"
                    )

                    value_map = valid_values.set_index(
                        "institution_id"
                    )[column]

                    new_values = old_df["institution_id"].map(
                        value_map
                    )

                    updated_counts[column] = new_values.notna().sum()

                    # Replace only valid newly collected values.
                    # If no fresh value exists, retain old value.
                    old_df[column] = new_values.combine_first(
                        pd.to_numeric(
                            old_df[column],
                            errors="coerce"
                        )
                    )

                # ----------------------------------
                # Save to the SAME CSV file
                # ----------------------------------

                old_df.to_csv(
                    csv_file,
                    index=False,
                    encoding="utf-8-sig"
                )

                total_updated += 1

                print("Updated existing file:", csv_file.name)
                print("RPC rows updated:", updated_counts["rpc"])
                print("GO rows updated:", updated_counts["go"])

        print("\n" + "=" * 55)
        print("RPC AND GO UPDATE FINISHED")
        print("=" * 55)

        print("CSV files processed:", total_updated)
        print("Backup location:", BACKUP_DIR)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
