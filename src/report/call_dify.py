import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
from src.report.extract_pdf_text import get_current_and_previous_pdf_text

def main():
    load_dotenv()
    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        raise SystemExit("Falta DIFY_API_KEY no .env")

    # 1) pega texto dos boletins baixados no fetch_mg()
    pdf_dir = Path("data/raw/mg")
    current_text, prev_text = get_current_and_previous_pdf_text(pdf_dir)

    # 2) monta inputs exatamente como seu fluxo do Dify espera
    inputs = {
        "current_pdf": [],           # não vamos enviar arquivo, só texto
        "previous_pdf": [],          # idem
        "current_text": current_text,
        "previous_text": prev_text or "",
    }

    url = "https://api.dify.ai/v1/workflows/run"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"inputs": inputs, "response_mode": "blocking", "user": "cli"}

    resp = requests.post(url, headers=headers, json=body)
    r = resp.json()
    print("[HTTP]", resp.status_code)

    # salva resposta crua p/ debug
    out_dir = Path("reports/weekly"); out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "response.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    if resp.status_code != 200:
        raise SystemExit(json.dumps(r, ensure_ascii=False, indent=2))

    # pega o markdown
    data = r.get("data", {}) or {}
    outputs = data.get("outputs") or {}
    md = outputs.get("report_markdown") or ""
    if not md:
        # fallback genérico
        md = next((v for v in outputs.values() if isinstance(v, str) and v.strip()), "")

    if not md:
        raise SystemExit("Não achei report_markdown na resposta do Dify.")

    # nomeia pelo dia do PDF atual (assumindo fetch_mg roda na semana)
    week = (Path("data/processed/dengue_weekly.parquet").exists() and
            __import__("pandas").read_parquet("data/processed/dengue_weekly.parquet")["week"].max())
    week_str = str(getattr(week, "date", lambda: week)()) if week is not None else "latest"

    out_md = out_dir / f"{week_str}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")

if __name__ == "__main__":
    main()
