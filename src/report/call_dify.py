import json, os
from pathlib import Path
import requests
from dotenv import load_dotenv
from src.report.extract_pdf_text import get_current_and_previous_pdf_text

def main():
    load_dotenv()
    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        raise SystemExit("Falta DIFY_API_KEY no .env")

    # 1) Texto dos PDFs locais
    current_text, prev_text = get_current_and_previous_pdf_text()

    # 2) KPIs/figures do payload (para satisfazer campos do Start)
    payload_path = Path("reports/weekly/payload.json")
    payload = json.loads(payload_path.read_text(encoding="utf-8")) if payload_path.exists() else {}
    kpis = json.dumps(payload.get("kpis", {}), ensure_ascii=False)
    figures = json.dumps(payload.get("figures", {}), ensure_ascii=False)

    # 3) Monta inputs iguais aos campos do Start no Dify
    inputs = {
        "kpis": kpis,
        "figures": figures,
        "current_text": current_text,
        "previous_text": prev_text or "",
        # não usamos upload de arquivo:
        "current_pdf": [],
        "previous_pdf": [],
    }

    url = "https://api.dify.ai/v1/workflows/run"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"inputs": inputs, "response_mode": "blocking", "user": "cli"}

    resp = requests.post(url, headers=headers, json=body)
    r = resp.json()
    print("[HTTP]", resp.status_code)
    Path("reports/weekly/response.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    if resp.status_code != 200:
        raise SystemExit(json.dumps(r, ensure_ascii=False, indent=2))

    data = r.get("data", {}) or {}
    outputs = data.get("outputs") or {}
    md = outputs.get("report_markdown") or next((v for v in outputs.values() if isinstance(v, str) and v.strip()), "")
    if not md:
        raise SystemExit("Não achei report_markdown na resposta do Dify.")

    # nome do arquivo por semana (se existir parquet) senão 'latest'
    week_str = "latest"
    try:
        import pandas as pd
        week = pd.read_parquet("data/processed/dengue_weekly.parquet")["week"].max()
        week_str = str(getattr(week, "date", lambda: week)())
    except Exception:
        pass

    out_md = Path("reports/weekly") / f"{week_str}.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")

if __name__ == "__main__":
    main()
