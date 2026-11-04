from pathlib import Path
import re
import pandas as pd

# ==========================================
# STEP 1: PROJECT PATHS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "nirf_2017_2025_raw.csv"
)

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "nirf_clean.csv"


# ==========================================
# STEP 2: LOAD MASTER DATASET
# ==========================================

df = pd.read_csv(RAW_FILE, low_memory=False)

print("Original dataset shape:", df.shape)


# ==========================================
# STEP 3: STANDARDIZE COLUMN NAMES
# ==========================================

df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

print("\nColumn names:")
print(df.columns.tolist())


# ==========================================
# STEP 4: CLEAN TEXT COLUMNS & STANDARDIZE
# ==========================================

def clean_display_name(name):
    if not name or pd.isna(name):
        return "Unknown"
    s = str(name).strip()
    # Normalize backticks and quotes
    s = s.replace("`", "'").replace("’", "'").replace("‘", "'")
    # Put space after dots if followed by multiple letters (e.g., I.C.College -> I. C. College)
    s = re.sub(r"([A-Za-z])\.([A-Za-z]{2,})", r"\1. \2", s)
    # Remove unnecessary commas between words (e.g., 'Technology, Dharwad' -> 'Technology Dharwad')
    s = s.replace(",", " ")
    # Collapse multiple whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # Standardize casing of minor connecting words
    words = s.split()
    fixed_words = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in {"of", "and", "the", "for", "in", "at", "to"}:
            fixed_words.append(lw)
        elif w.isupper() and len(w) <= 4:
            # Preserve acronyms like IIT, NIT, IIM, BITS, SRM, MAHE
            fixed_words.append(w)
        elif w.islower():
            fixed_words.append(w.capitalize())
        else:
            fixed_words.append(w)
    return " ".join(fixed_words)


def clean_state_str(s):
    if not s or pd.isna(s):
        return "Unknown"
    s = str(s).strip()
    if s.lower() in ["jammu and kashmir", "jammu & kashmir"]:
        return "Jammu and Kashmir"
    return s.title()


text_columns = [
    "institution_id",
    "institution_name",
    "name",
    "city",
    "state",
    "category",
    "source_file"
]

for col in text_columns:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype("string")
            .fillna("Unknown")
            .str.strip()
        )

if "institution_name" in df.columns:
    df["institution_name"] = df["institution_name"].map(clean_display_name).astype("string")

if "state" in df.columns:
    df["state"] = df["state"].map(clean_state_str).astype("string")

if "city" in df.columns:
    df["city"] = (
        df["city"]
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .astype("string")
    )


# ==========================================
# STEP 5: STANDARDIZE CATEGORY NAMES
# ==========================================

if "category" in df.columns:
    df["category"] = df["category"].str.title().astype("string")


# ==========================================
# STEP 6: CONVERT NUMERIC COLUMNS
# ==========================================

numeric_columns = [
    "year",
    "rank",
    "overall_score",
    "tlr",
    "rpc",
    "go",
    "oi",
    "pr"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

# Preserve rank_original as clean string without converting to NaN
if "rank_original" in df.columns:
    df["rank_original"] = (
        df["rank_original"]
        .astype("string")
        .fillna("")
        .str.strip()
    )


# ==========================================
# STEP 7: DEDUPLICATION WITH SCORE PRESERVATION
# ==========================================

# When duplicates exist, prefer records with valid parameter scores
param_cols = [c for c in ["tlr", "rpc", "go", "oi", "pr", "overall_score"] if c in df.columns]
if param_cols:
    df["_valid_score_count"] = df[param_cols].notna().sum(axis=1)
    df = df.sort_values(by=["year", "category", "_valid_score_count"], ascending=[True, True, False])
    df = df.drop(columns=["_valid_score_count"])

duplicate_count_exact = df.duplicated().sum()
print("\nExact duplicate rows:", duplicate_count_exact)
df = df.drop_duplicates()

# Deduplicate on [year, category, institution_id] keeping first (which has highest score count)
if "institution_id" in df.columns:
    dup_id_mask = df.duplicated(subset=["year", "category", "institution_id"], keep="first")
    print("Duplicate [year, category, institution_id] rows removed:", dup_id_mask.sum())
    df = df[~dup_id_mask]

# Sort cleanly
sort_cols = [c for c in ["year", "category", "rank"] if c in df.columns]
if sort_cols:
    df = df.sort_values(by=sort_cols).reset_index(drop=True)


# ==========================================
# STEP 8: CHECK MISSING VALUES
# ==========================================

print("\nMissing values:")
print(df.isnull().sum())


# ==========================================
# STEP 9: CHECK INVALID VALUES
# ==========================================

if "rank" in df.columns:
    invalid_ranks = df[
        df["rank"].notna() &
        (df["rank"] <= 0)
    ]
    print("\nInvalid ranks:", len(invalid_ranks))

if "overall_score" in df.columns:
    invalid_scores = df[
        df["overall_score"].notna() &
        (
            (df["overall_score"] < 0) |
            (df["overall_score"] > 100)
        )
    ]
    print("Invalid overall scores:", len(invalid_scores))


# ==========================================
# STEP 10: CHECK YEARS AND CATEGORIES
# ==========================================

if "year" in df.columns:
    print("\nYears in dataset:")
    print(sorted(df["year"].dropna().unique()))

if "category" in df.columns:
    print("\nCategories in dataset:")
    print(sorted(df["category"].dropna().unique()))


# ==========================================
# STEP 11: SAVE CLEAN DATASET
# ==========================================

df.to_csv(OUTPUT_FILE, index=False)

print("\nPreprocessing completed!")
print("Final dataset shape:", df.shape)
print("Clean dataset saved at:")
print(OUTPUT_FILE)
