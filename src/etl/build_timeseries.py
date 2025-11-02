from pathlib import Path
import pandas as pd

INTERIM = Path("data/interim/dengue_clean.parquet")
PROCESSED_DIR = Path("data/processed")
OUT = PROCESSED_DIR / "dengue_weekly.parquet"

def build_ts():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(INTERIM)
    # Semana epidemiológica simples (domingo encerra a semana)
    df = df.set_index("date")
    weekly = (
        df.groupby([pd.Grouper(freq="W-SUN"), "state"])
          .agg(cases=("cases", "sum"), deaths=("deaths", "sum"))
          .reset_index()
          .rename(columns={"date": "week"})
    )
    weekly.to_parquet(OUT, index=False)
    print(f"[timeseries] wrote {OUT}")
