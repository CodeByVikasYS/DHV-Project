
from pathlib import Path
import pandas as pd

# Project root folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Folder containing year-wise CSV files
RAW_DIR = PROJECT_DIR / "data" / "raw"

# Output master dataset
OUTPUT_FILE = RAW_DIR / "nirf_2017_2025_raw.csv"

all_data = []

# Search CSV files inside each year folder
for year in range(2017, 2026):

    year_folder = RAW_DIR / str(year)

    if not year_folder.exists():
        print(f"Missing folder: {year}")
        continue

    for csv_file in year_folder.glob("*.csv"):

        df = pd.read_csv(csv_file)

        # Add year and category information
        df["year"] = year
        df["source_file"] = csv_file.name

        all_data.append(df)

        print(f"Added: {csv_file.name}")

# Combine all files
if all_data:
    master_df = pd.concat(
        all_data,
        ignore_index=True,
        sort=False
    )

    master_df.to_csv(OUTPUT_FILE, index=False)

    print("\nMaster dataset created!")
    print("Rows:", len(master_df))
    print("Columns:", len(master_df.columns))
    print("Saved to:", OUTPUT_FILE)

else:
    print("No CSV files found.")
