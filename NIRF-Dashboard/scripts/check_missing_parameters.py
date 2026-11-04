import pandas as pd
from pathlib import Path

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
FILE = PROJECT_DIR / "data" / "processed" / "nirf_clean.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

# Load dataset
df = pd.read_csv(FILE)

parameters = ["overall_score", "tlr", "rpc", "go", "oi", "pr"]

# Convert parameter columns to numeric
for col in parameters:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Check missing values by year and category
summary = (
    df.groupby(["year", "category"])[parameters]
    .apply(lambda group: group.isna().sum())
    .reset_index()
)

# Keep only groups where at least one parameter is missing
missing_summary = summary[
    summary[parameters].sum(axis=1) > 0
]

print("\nMISSING VALUES BY YEAR AND CATEGORY")
print("=" * 60)

if missing_summary.empty:
    print("No missing parameter values found.")
else:
    print(missing_summary.to_string(index=False))

# Total missing values per parameter
print("\nTOTAL MISSING VALUES")
print("=" * 60)

for col in parameters:
    print(f"{col}: {df[col].isna().sum()}")

# Save report
output_file = OUTPUT_DIR / "missing_parameters_report.csv"
missing_summary.to_csv(output_file, index=False)

print(f"\nReport saved to: {output_file}")