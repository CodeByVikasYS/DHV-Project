
from pathlib import Path
import pandas as pd

# ==========================================
# STEP 1: FILE PATH
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

CLEAN_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "nirf_clean.csv"
)

# ==========================================
# STEP 2: LOAD CLEAN DATASET
# ==========================================

df = pd.read_csv(CLEAN_FILE)

print("=" * 50)
print("NIRF DATASET VALIDATION")
print("=" * 50)

print("\nDataset shape:", df.shape)


# ==========================================
# STEP 3: CHECK REQUIRED COLUMNS
# ==========================================

expected_columns = [
    "year",
    "category",
    "institution_id",
    "institution_name",
    "city",
    "state",
    "overall_score",
    "rank",
    "rank_original",
    "tlr",
    "rpc",
    "go",
    "oi",
    "pr",
    "source_url",
    "source_file"
]

missing_columns = set(expected_columns) - set(df.columns)
extra_columns = set(df.columns) - set(expected_columns)

print("\nMissing columns:", missing_columns)
print("Extra columns:", extra_columns)

if not missing_columns:
    print("Column validation: PASSED")
else:
    print("Column validation: FAILED")


# ==========================================
# STEP 4: CHECK MISSING VALUES
# ==========================================

print("\nMissing values in each column:")
print(df.isnull().sum())

print("\nTotal missing values:", df.isnull().sum().sum())


# ==========================================
# STEP 5: CHECK DUPLICATE ROWS
# ==========================================

duplicate_count = df.duplicated().sum()

print("\nDuplicate rows:", duplicate_count)

if duplicate_count == 0:
    print("Duplicate validation: PASSED")
else:
    print("Duplicate validation: CHECK REQUIRED")


# ==========================================
# STEP 6: CHECK DATA TYPES
# ==========================================

print("\nColumn data types:")
print(df.dtypes)


# ==========================================
# STEP 7: CHECK YEAR RANGE
# ==========================================

if "year" in df.columns:

    years = sorted(df["year"].dropna().unique())

    print("\nYears found:")
    print(years)

    expected_years = list(range(2017, 2026))

    missing_years = set(expected_years) - set(years)

    print("Missing years:", missing_years)


# ==========================================
# STEP 8: CHECK CATEGORIES
# ==========================================

if "category" in df.columns:

    categories = sorted(df["category"].dropna().unique())

    print("\nCategories found:")
    print(categories)

    print("Total categories:", len(categories))


# ==========================================
# STEP 9: CHECK INVALID RANKS
# ==========================================

if "rank" in df.columns:

    invalid_ranks = df[
        df["rank"].notna() &
        (df["rank"] <= 0)
    ]

    print("\nInvalid ranks:", len(invalid_ranks))


# ==========================================
# STEP 10: CHECK INVALID SCORES
# ==========================================

score_columns = [
    "overall_score",
    "tlr",
    "rpc",
    "go",
    "oi",
    "pr"
]

for col in score_columns:

    if col in df.columns:

        invalid_scores = df[
            df[col].notna() &
            (
                (df[col] < 0) |
                (df[col] > 100)
            )
        ]

        print(f"Invalid values in {col}:", len(invalid_scores))


# ==========================================
# STEP 11: CHECK INSTITUTION NAMES
# ==========================================

if "institution_name" in df.columns:

    missing_names = df["institution_name"].isnull().sum()

    empty_names = (
        df["institution_name"]
        .astype("string")
        .str.strip()
        .eq("")
        .sum()
    )

    print("\nMissing institution names:", missing_names)
    print("Empty institution names:", empty_names)


# ==========================================
# STEP 12: FINAL SUMMARY
# ==========================================

print("\n" + "=" * 50)
print("VALIDATION SUMMARY")
print("=" * 50)

print("Rows:", len(df))
print("Columns:", len(df.columns))
print("Missing values:", df.isnull().sum().sum())
print("Duplicate rows:", duplicate_count)

print("\nValidation completed.")
print("Original clean dataset was not modified.")
