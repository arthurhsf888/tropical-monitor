# src/report/render_weekly.py
from pathlib import Path
import pandas as pd
import json

PROCESSED = Path("data/processed/dengue_weekly.parquet")
OUT = Path("reports/weekly/payload.json")

def render_weekly():
    df = pd.read_parquet(PROCESSED)

    # garante tipos
    df["week"] = pd.to_datetime(df["week"])
    for col in ("cases", "deaths"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # pega a semana mais recente com pelo menos 1 caso/death ou simplesmente a última
    last_week = df["week"].max()
    ref = df[df["week"] == last_week].copy()

    # métricas globais da semana
    cases_total = int(ref["cases"].sum())
    deaths_total = int(ref["deaths"].sum())

    # top UFs por casos (até 3)
    uf_top = (
        ref.groupby("state")["cases"]
           .sum()
           .sort_values(ascending=False)
           .head(3)
           .astype(int)
           .to_dict()
    )

    payload = {
    "kpis": { ... },
    "figures": {
        "choropleth": "reports/figures/incidencia_semana.html",
        "evidently": "reports/figures/evidently_weekly.html",
        "serotype_map": "reports/figures/serotype_map.png",  # <--- NOVO
    }
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[report] wrote {OUT}")
