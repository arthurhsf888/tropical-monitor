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

    # 1) texto dos boletins
    pdf_dir = Path("data/raw/mg")
    current_text, prev_text = get_current_and_previous_pdf_text(pdf_dir)

    # 2) carrega payload para satisfazer campos obrigatórios do Start
    payload_path = Path("reports/weekly/payload.json")
    payload = {}
    if payload_path.exists():
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    kpis = json.dumps(payload.get("kpis", {}), ensure_ascii=False)
    figures = json.dumps(payload.get("figures", {}), ensure_ascii=False)

    # 3) monta inputs exatamente com os nomes do seu fluxo
    inputs = {
        "kpis": kpis,                    # <-- agora enviado
        "figures": figures,              # <-- agora enviado
        "current_pdf": [],               # não usamos upload de arquivo
        "previous_pdf": [],
        "current_text": current_text,    # usados no LLM como contexto
        "previous_text": prev_text or "",
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

    # nome do arquivo da semana
    import pandas as pd
    week = pd.read_parquet("data/processed/dengue_weekly.parquet")["week"].max()
    week_str = str(getattr(week, "date", lambda: week)())

    out_md = Path("reports/weekly") / f"{week_str}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")

if __name__ == "__main__":
    main()
