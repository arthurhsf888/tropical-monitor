from pathlib import Path
import pandas as pd

RAW = Path("data/raw/ingest.csv")
INTERIM = Path("data/interim")
OUT = INTERIM / "dengue_clean.parquet"

def clean():
    INTERIM.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW)
    # Normalização mínima
    df["date"] = pd.to_datetime(df["date"])
    df["state"] = df["state"].str.upper().str.strip()
    df["city"] = df["city"].str.title().str.strip()
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce").fillna(0).astype(int)
    df["deaths"] = pd.to_numeric(df["deaths"], errors="coerce").fillna(0).astype(int)
    df.to_parquet(OUT, index=False)
    print(f"[clean] wrote {OUT}")
