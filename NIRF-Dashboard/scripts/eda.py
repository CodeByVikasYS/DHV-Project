
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# STEP 1: PROJECT PATHS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

CLEAN_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "nirf_clean.csv"
)

CHART_DIR = PROJECT_DIR / "data" / "processed" / "eda_charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# STEP 2: LOAD DATASET
# ==========================================

df = pd.read_csv(CLEAN_FILE)

print("=" * 60)
print("NIRF EXPLORATORY DATA ANALYSIS")
print("=" * 60)

print("\nDataset shape:", df.shape)

print("\nFirst 5 records:")
print(df.head())


# ==========================================
# STEP 3: BASIC DATASET INFORMATION
# ==========================================

print("\nDataset information:")
print(df.info())

print("\nStatistical summary:")
print(df.describe(include="all"))


# ==========================================
# STEP 4: CHECK YEARS
# ==========================================

if "year" in df.columns:

    print("\nYears available:")
    print(sorted(df["year"].dropna().unique()))

    print("\nRecords per year:")
    print(df["year"].value_counts().sort_index())


# ==========================================
# STEP 5: CHECK CATEGORIES
# ==========================================

if "category" in df.columns:

    print("\nCategories available:")
    print(sorted(df["category"].dropna().unique()))

    print("\nRecords per category:")
    print(df["category"].value_counts().sort_values(ascending=False))


# ==========================================
# STEP 6: MISSING VALUES
# ==========================================

print("\nMissing values per column:")
print(df.isnull().sum())


# ==========================================
# STEP 7: INSPECT PARAMETER SCORE RANGES
# ==========================================

score_columns = [
    "overall_score",
    "tlr",
    "rpc",
    "go",
    "oi",
    "pr"
]

available_scores = [
    col for col in score_columns
    if col in df.columns
]

print("\nParameter score ranges:")

for col in available_scores:

    print(f"\n{col.upper()}")

    print("Minimum:", df[col].min())
    print("Maximum:", df[col].max())
    print("Mean:", df[col].mean())
    print("Median:", df[col].median())

    print("Values below 0:", (df[col] < 0).sum())
    print("Values above 100:", (df[col] > 100).sum())


# ==========================================
# STEP 8: TOP RANKED INSTITUTIONS
# ==========================================

if "rank" in df.columns:

    latest_year = int(df["year"].max())

    latest_data = df[df["year"] == latest_year]

    print(f"\nTop 10 institutions in {latest_year}:")

    top_10 = (
        latest_data
        .sort_values("rank")
        .head(10)
    )

    display_columns = [
        col for col in [
            "category",
            "rank",
            "institution_name",
            "overall_score"
        ]
        if col in df.columns
    ]

    print(top_10[display_columns].to_string(index=False))


# ==========================================
# STEP 9: RECORDS PER YEAR CHART
# ==========================================

if "year" in df.columns:

    records_per_year = (
        df["year"]
        .value_counts()
        .sort_index()
    )

    plt.figure(figsize=(10, 5))

    records_per_year.plot(kind="bar")

    plt.title("Number of NIRF Records per Year")
    plt.xlabel("Year")
    plt.ylabel("Number of Records")
    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig(
        CHART_DIR / "records_per_year.png",
        dpi=300
    )

    plt.show()
    plt.close()


# ==========================================
# STEP 10: RECORDS PER CATEGORY CHART
# ==========================================

if "category" in df.columns:

    records_per_category = (
        df["category"]
        .value_counts()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(12, 6))

    records_per_category.plot(kind="bar")

    plt.title("Number of Records per NIRF Category")
    plt.xlabel("Category")
    plt.ylabel("Number of Records")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    plt.savefig(
        CHART_DIR / "records_per_category.png",
        dpi=300
    )

    plt.show()
    plt.close()


# ==========================================
# STEP 11: OVERALL SCORE TREND
# ==========================================

if "year" in df.columns and "overall_score" in df.columns:

    yearly_score = (
        df.groupby("year")["overall_score"]
        .mean()
    )

    print("\nAverage overall score per year:")
    print(yearly_score)

    plt.figure(figsize=(10, 5))

    yearly_score.plot(kind="line", marker="o")

    plt.title("Average Overall Score by Year")
    plt.xlabel("Year")
    plt.ylabel("Average Overall Score")
    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        CHART_DIR / "overall_score_trend.png",
        dpi=300
    )

    plt.show()
    plt.close()


# ==========================================
# STEP 12: PARAMETER SCORE TRENDS
# ==========================================

parameters = ["tlr", "rpc", "go", "oi", "pr"]

available_parameters = [
    col for col in parameters
    if col in df.columns
]

if "year" in df.columns and available_parameters:

    yearly_parameters = (
        df.groupby("year")[available_parameters]
        .mean()
    )

    print("\nAverage parameter scores by year:")
    print(yearly_parameters)

    plt.figure(figsize=(12, 6))

    for col in available_parameters:
        plt.plot(
            yearly_parameters.index,
            yearly_parameters[col],
            marker="o",
            label=col.upper()
        )

    plt.title("Average NIRF Parameter Scores by Year")
    plt.xlabel("Year")
    plt.ylabel("Average Score")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        CHART_DIR / "parameter_score_trends.png",
        dpi=300
    )

    plt.show()
    plt.close()


# ==========================================
# STEP 13: RANKING DISTRIBUTION
# ==========================================

if "rank" in df.columns:

    plt.figure(figsize=(10, 5))

    df["rank"].dropna().plot(
        kind="hist",
        bins=30
    )

    plt.title("Distribution of NIRF Ranks")
    plt.xlabel("Rank")
    plt.ylabel("Frequency")

    plt.tight_layout()

    plt.savefig(
        CHART_DIR / "rank_distribution.png",
        dpi=300
    )

    plt.show()
    plt.close()


# ==========================================
# STEP 14: FINAL SUMMARY
# ==========================================

print("\n" + "=" * 60)
print("EDA COMPLETED")
print("=" * 60)

print("Total records:", len(df))
print("Total columns:", len(df.columns))

if "year" in df.columns:
    print("Total years:", df["year"].nunique())

if "category" in df.columns:
    print("Total categories:", df["category"].nunique())

print("\nCharts saved at:")
print(CHART_DIR)
