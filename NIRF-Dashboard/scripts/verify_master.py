
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
MASTER_FILE = RAW_DIR / "nirf_2017_2025_raw.csv"

total_rows = 0
all_columns = set()
file_count = 0

# Check all original CSV files
for year in range(2017, 2026):
    year_folder = RAW_DIR / str(year)

    for file in year_folder.glob("*.csv"):
        df = pd.read_csv(file)

        total_rows += len(df)
        all_columns.update(df.columns)
        file_count += 1

# Read master dataset
master_df = pd.read_csv(MASTER_FILE)

# Row validation
rows_match = total_rows == len(master_df)

# Column validation
original_columns = all_columns
master_columns = set(master_df.columns)

missing_columns = original_columns - master_columns
extra_columns = master_columns - original_columns

print("Original CSV files:", file_count)
print("Original total rows:", total_rows)
print("Master dataset rows:", len(master_df))

print("\nRows match:", rows_match)
print("Columns match:", original_columns == master_columns)

print("Missing columns in master:", missing_columns)
print("Extra columns in master:", extra_columns)

if rows_match and not missing_columns:
    print("\nSUCCESS: All rows and original columns are covered!")
else:
    print("\nWARNING: Please check the differences.")
