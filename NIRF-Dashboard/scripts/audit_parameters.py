from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
FILE = PROJECT_DIR / "data" / "processed" / "nirf_clean.csv"

df = pd.read_csv(FILE)

parameters = ["overall_score", "tlr", "rpc", "go", "oi", "pr"]

for col in parameters:
    if col not in df.columns:
        print(f"\n{col}: COLUMN NOT FOUND")
        continue

    values = pd.to_numeric(df[col], errors="coerce")

    print(f"\n--- {col.upper()} ---")
    print("Missing:", values.isna().sum())
    print("Minimum:", values.min())
    print("Maximum:", values.max())
    print("Mean:", values.mean())
    print("Values above 100:", (values > 100).sum())
    print("Sample values:")
    print(values.dropna().head(10).tolist())