from pathlib import Path
import pandas as pd
import json

PROCESSED = Path("data/processed/dengue_weekly.parquet")
PAYLOAD = Path("reports/weekly/payload.json")

def render_weekly():
    df = pd.read_parquet(PROCESSED)
    last_week = df["week"].max()
    ref = df[df["week"] == last_week]
    kpis = {
        "week": pd.to_datetime(last_week).strftime("%Y-%m-%d"),
        "cases_total": int(ref["cases"].sum()),
        "deaths_total": int(ref["deaths"].sum()),
        "uf_top_cases": (
            ref.groupby("state")["cases"].sum().sort_values(ascending=False).head(3).to_dict()
        ),
    }
    payload = {
        "kpis": kpis,
        "figures": {
            "choropleth": "reports/figures/incidencia_semana.html",
            "evidently": "reports/figures/evidently_weekly.html",
        },
    }
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[report] wrote {PAYLOAD}")

if __name__ == "__main__":
    render_weekly()
