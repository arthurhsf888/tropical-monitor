from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def _load_payload() -> tuple[str, str]:
    """
    Lê reports/weekly/payload.json (se existir) e devolve (kpis_json, figures_json)
    como strings JSON. Isso satisfaz os campos do nó Iniciar no Dify.
    """
    payload_path = Path("reports/weekly/payload.json")
    if payload_path.exists():
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    else:
        payload = {}

    kpis = json.dumps(payload.get("kpis", {}), ensure_ascii=False)
    figures = json.dumps(payload.get("figures", {}), ensure_ascii=False)
    return kpis, figures


def _read_week_label() -> str:
    """
    Tenta pegar a semana mais recente do parquet local; se não existir,
    usa a data de hoje como rótulo.
    """
    try:
        import pandas as pd  # import local para evitar custo se não usado
        parquet = Path("data/processed/dengue_weekly.parquet")
        if parquet.exists():
            df = pd.read_parquet(parquet)
            wk = df["week"].max()
            # Se 'week' já for date/datetime:
            try:
                return str(wk.date())
            except Exception:
                return str(wk)
    except Exception:
        pass

    from datetime import date
    return date.today().isoformat()


def main() -> None:
    load_dotenv()

    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        raise SystemExit("Falta DIFY_API_KEY no .env ou no ambiente.")

    # Lê texto dos PDFs locais
    from src.report.extract_pdf_text import get_current_and_previous_pdf_text

    current_text, prev_text = get_current_and_previous_pdf_text()

    # Lê kpis/figures do payload (ou envia {} se não existir)
    kpis_json_str, figures_json_str = _load_payload()

    # Monta os inputs com os MESMOS nomes dos campos do nó Iniciar no Dify
    inputs = {
        # Campos do seu Start (mantidos para compatibilidade)
        "kpis": kpis_json_str,
        "figures": figures_json_str,

        # Texto dos PDFs (o LLM deve ter essas variáveis no Contexto)
        "current_text": current_text,
        "previous_text": prev_text or "",

        # Se o seu fluxo ainda tiver esses campos como não obrigatórios,
        # mandamos lista vazia para evitar erro de tipagem.
        "current_pdf": [],
        "previous_pdf": [],
    }

    url = "https://api.dify.ai/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {"inputs": inputs, "response_mode": "blocking", "user": "cli"}

    print("[call_dify] POST", url)
    resp = requests.post(url, headers=headers, json=body, timeout=90)
    print("[HTTP]", resp.status_code)

    # Sempre salva a resposta crua para depuração
    out_dir = Path("reports/weekly")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "response.json"
    raw_path.write_text(json.dumps(resp.json(), ensure_ascii=False, indent=2), encoding="utf-8")

    if resp.status_code != 200:
        raise SystemExit(raw_path.read_text(encoding="utf-8"))

    data = resp.json().get("data", {}) or {}
    outputs = data.get("outputs") or {}

    # Esperamos 'report_markdown' no nó FIM
    md = outputs.get("report_markdown")
    if not isinstance(md, str) or not md.strip():
        # Fallback: tenta pegar qualquer string não vazia das saídas
        md = next((v for v in outputs.values() if isinstance(v, str) and v.strip()), "")

    if not md:
        raise SystemExit("Não achei 'report_markdown' (ou outra string) na resposta do Dify.")

    week_label = _read_week_label()
    out_md = out_dir / f"{week_label}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")


if __name__ == "__main__":
    main()
