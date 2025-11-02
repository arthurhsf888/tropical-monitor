import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

def main():
    print("[call_dify] start")

    load_dotenv()
    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        raise SystemExit("Falta DIFY_API_KEY no .env")

    payload_path = Path("reports/weekly/payload.json")
    if not payload_path.exists():
        raise SystemExit("Não encontrei reports/weekly/payload.json. Rode antes: python -m src.cli report")

    data = json.loads(payload_path.read_text(encoding="utf-8"))
    print("[call_dify] payload loaded:", json.dumps(data, ensure_ascii=False))

    inputs = {
        "kpis": json.dumps(data["kpis"], ensure_ascii=False),
        "figures": json.dumps(data["figures"], ensure_ascii=False),
    }

    url = "https://api.dify.ai/v1/workflows/run"  # sem workflow_id
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"inputs": inputs, "response_mode": "blocking", "user": "cli"}

    print("[call_dify] POST", url)
    resp = requests.post(url, headers=headers, json=body)
    print("[call_dify] status:", resp.status_code)

    # Tenta sempre decodificar JSON
    try:
        r = resp.json()
    except Exception:
        print("[call_dify] non-JSON response:", resp.text[:500])
        raise SystemExit("Resposta não-JSON do Dify.")

    # Salva a resposta completa para inspeção
    logs_dir = Path("reports/weekly")
    logs_dir.mkdir(parents=True, exist_ok=True)
    raw_path = logs_dir / "response.json"
    raw_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[call_dify] saved raw response -> {raw_path}")

    if resp.status_code != 200:
        print("[DIFY ERROR]", json.dumps(r, ensure_ascii=False, indent=2))
        raise SystemExit("Falha ao chamar o workflow do Dify.")

    # Extrai o markdown (compatível com formatos novos/antigos)
    data_obj = r.get("data", {}) or {}
    outputs = data_obj.get("outputs") or r.get("outputs") or {}
    md = None
    if isinstance(outputs, dict):
        md = outputs.get("report_markdown")
        if md is None:
            # fallback: primeira string encontrada
            for v in outputs.values():
                if isinstance(v, str) and v.strip():
                    md = v
                    break
    if not md:
        md = data_obj.get("report_markdown") or r.get("report_markdown")

    if not md:
        print("[DEBUG] full response:", json.dumps(r, ensure_ascii=False, indent=2))
        raise SystemExit("Não achei 'report_markdown' em data.outputs / data / outputs.")

    week = data["kpis"]["week"]
    out_md = logs_dir / f"{week}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"[dify] boletim salvo -> {out_md.resolve()}")

if __name__ == "__main__":
    main()
