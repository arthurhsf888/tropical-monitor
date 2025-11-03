from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def _load_payload() -> tuple[str, str, str]:
    """
    Lê reports/weekly/payload.json (se existir) e devolve (kpis_json, figures_json, map_path)
    como strings JSON + caminho da imagem do mapa (se houver).
    """
    payload_path = Path("reports/weekly/payload.json")
    if payload_path.exists():
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    else:
        payload = {}

    kpis = json.dumps(payload.get("kpis", {}), ensure_ascii=False)
    figures = json.dumps(payload.get("figures", {}), ensure_ascii=False)

    # extrai o caminho do mapa (se existir nas figures)
    figures_dict = payload.get("figures", {}) if isinstance(payload.get("figures", {}), dict) else {}
    map_path = figures_dict.get("serotype_map", "")

    return kpis, figures, map_path


def _read_week_label() -> str:
    """
    Tenta pegar a semana mais recente do parquet local; se não existir,
    usa a data de hoje como rótulo.
    """
    try:
        import pandas as pd  # import local
        parquet = Path("data/processed/dengue_weekly.parquet")
        if parquet.exists():
            df = pd.read_parquet(parquet)
            wk = df["week"].max()
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

    # Texto dos PDFs locais
    from src.report.extract_pdf_text import get_current_and_previous_pdf_text
    current_text, prev_text = get_current_and_previous_pdf_text()

    # DEBUG: verifique se veio texto
    print(f"[debug] current_text chars: {len(current_text)}")
    print("[debug] current_text sample:", current_text[:400].replace("\n", " "))
    if prev_text:
        print(f"[debug] previous_text chars: {len(prev_text)}")

    # Carrega figures e caminho do mapa (kpis não será usado no LLM)
    kpis_json_str, figures_json_str, map_path = _load_payload()

    # Monta os inputs usados no Start do Dify
    inputs = {
        # NÃO enviar 'kpis' para não poluir o LLM com zeros
        # "kpis": kpis_json_str,

        "figures": figures_json_str,    # ok manter (se usa a seção de figuras)
        "map_path": map_path,           # para embutir a imagem no markdown

        "current_text": current_text,   # texto do PDF
        "previous_text": prev_text or "",

        # campos de arquivo não usados
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

    out_dir = Path("reports/weekly")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "response.json"
    try:
        raw_path.write_text(json.dumps(resp.json(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        raw_path.write_text(str(resp.text), encoding="utf-8")

    if resp.status_code != 200:
        raise SystemExit(raw_path.read_text(encoding="utf-8"))

    data = resp.json().get("data", {}) or {}
    outputs = data.get("outputs") or {}

    md = outputs.get("report_markdown")
    if not isinstance(md, str) or not md.strip():
        md = next((v for v in outputs.values() if isinstance(v, str) and v.strip()), "")

    if not md:
        raise SystemExit("Não achei 'report_markdown' (ou outra string) na resposta do Dify.")

    week_label = _read_week_label()
    out_md = out_dir / f"{week_label}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")


if __name__ == "__main__":
    main()
