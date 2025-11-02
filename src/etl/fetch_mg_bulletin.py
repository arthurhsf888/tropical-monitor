from __future__ import annotations
from pathlib import Path
import re, json, datetime as dt
import requests, pdfplumber
import pandas as pd

RAW_DIR = Path("data/raw/mg")
INTERIM_DIR = Path("data/interim/mg")
PROCESSED_DIR = Path("data/processed")

# URL do último boletim informado por você.
MG_BULLETIN_URL = (
    "https://www.saude.mg.gov.br/documentos/boletim-epidemiologico-dengue-chikungunya-e-zika/boletim-epidemiologico-de-monitoramento-dos-casos-de-dengue-chikungunya-e-zika-06-10/"
)

def _to_int(s: str) -> int:
    # remove separador de milhar tipo "156.219" -> 156219
    return int(re.sub(r"[^\d]", "", s))

def _extract_numbers(text: str) -> dict:
    """
    Extrai os principais indicadores descritos no boletim (ex.: seu print):
    - Dengue: prováveis, confirmados, óbitos confirmados
    - Chikungunya: prováveis, confirmados, óbitos (confirmados ou em investigação)
    - Zika: prováveis, confirmados, óbitos
    Obs: o boletim costuma trazer números acumulados "até DD/MM".
    """
    # normaliza espaços
    t = " ".join(text.split())

    def find(pattern: str, group: int = 1, default: int = 0) -> int:
        m = re.search(pattern, t, flags=re.IGNORECASE)
        return _to_int(m.group(group)) if m else default

    # Padrões tolerantes (varia um pouco entre versões)
    dengue_prob  = find(r"(\d[\d\.\,]*) casos prov[aá]veis .*? dengue")
    dengue_conf  = find(r"(\d[\d\.\,]*) foram confirmados .*? dengue|(\d[\d\.\,]*) casos .*? confirmados .*? dengue", group=1) or \
                   find(r"dengue[, ]+(\d[\d\.\,]*) casos confirmados")
    dengue_obitos_conf = find(r"(\d[\d\.\,]*) [oó]bitos confirmados .*? dengue")

    chik_prob   = find(r"(\d[\d\.\,]*) casos prov[aá]veis .*? Chikungunya")
    chik_conf   = find(r"(\d[\d\.\,]*) (?:foram )?confirmados .*? Chikungunya")
    chik_obitos = find(r"(\d[\d\.\,]*) [oó]bitos .*? Chikungunya")

    zika_prob   = find(r"Quanto ao v[ií]rus Zika.*?h[aá] (\d[\d\.\,]*) casos prov[aá]veis")
    zika_conf   = find(r"Zika.*?(\d[\d\.\,]*) casos confirmados")
    zika_obitos = find(r"Zika.*?(?:n[aã]o h[aá]|0) [oó]bitos") and 0

    return {
        "dengue": {"provaveis": dengue_prob, "confirmados": dengue_conf, "obitos_conf": dengue_obitos_conf},
        "chikungunya": {"provaveis": chik_prob, "confirmados": chik_conf, "obitos": chik_obitos},
        "zika": {"provaveis": zika_prob, "confirmados": zika_conf, "obitos": zika_obitos if isinstance(zika_obitos, int) else 0},
    }

def fetch_mg_bulletin(url: str = MG_BULLETIN_URL) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    # Baixa a página HTML e tenta pegar o primeiro PDF
    html = requests.get(url, timeout=30).text
    # procura links .pdf
    m = re.search(r'href="([^"]+\.pdf)"', html, flags=re.IGNORECASE)
    if not m:
        raise RuntimeError("Não encontrei link PDF na página da SES-MG.")
    pdf_url = m.group(1)
    # nomeia por data atual
    stamp = dt.date.today().strftime("%Y%m%d")
    pdf_path = RAW_DIR / f"boletim_mg_{stamp}.pdf"
    r = requests.get(pdf_url, timeout=60)
    r.raise_for_status()
    pdf_path.write_bytes(r.content)
    print(f"[mg] downloaded -> {pdf_path}")
    return pdf_path

def parse_mg_pdf(pdf_path: Path) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    metrics = _extract_numbers(text)
    # tenta extrair a data "Até DD/MM" para referenciar a semana
    m = re.search(r"At[eé]\s+(\d{2})/(\d{2})", text)
    if m:
        day, month = map(int, m.groups())
        year = dt.date.today().year
        ref_date = dt.date(year, month, day)
    else:
        ref_date = dt.date.today()
    out = {
        "ref_date": ref_date.isoformat(),
        "state": "MG",
        **metrics,
    }
    return out

def save_mg_timeseries(parsed: dict) -> Path:
    """
    Salva um registro cumulativo por data (CSV), e também um parquet semanal
    somando casos confirmados de dengue (diferença dos acumulados).
    """
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cumulative_csv = INTERIM_DIR / "mg_bulletin_cumulative.csv"
    row = {
        "date": parsed["ref_date"],
        "state": parsed["state"],
        "dengue_prob": parsed["dengue"]["provaveis"] or 0,
        "dengue_conf": parsed["dengue"]["confirmados"] or 0,
        "dengue_obitos_conf": parsed["dengue"]["obitos_conf"] or 0,
        "chik_prob": parsed["chikungunya"]["provaveis"] or 0,
        "chik_conf": parsed["chikungunya"]["confirmados"] or 0,
        "chik_obitos": parsed["chikungunya"]["obitos"] or 0,
        "zika_prob": parsed["zika"]["provaveis"] or 0,
        "zika_conf": parsed["zika"]["confirmados"] or 0,
        "zika_obitos": parsed["zika"]["obitos"] or 0,
    }

    if cumulative_csv.exists():
        df_old = pd.read_csv(cumulative_csv)
        df = pd.concat([df_old, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    # 🔧 Normaliza tipo da data e ordena SEMPRE
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=False)
    df = df.dropna(subset=["date"]).drop_duplicates(["date"], keep="last")
    df = df.sort_values("date")
    df.to_csv(cumulative_csv, index=False)
    print(f"[mg] wrote cumulative -> {cumulative_csv}")

    # ⚙️ Agora é seguro resamplear (DatetimeIndex garantido)
    df_idx = df.set_index("date").asfreq("D").ffill()

    weekly = (
        df_idx[["dengue_conf"]]
        .diff()                       # novos na semana
        .resample("W-SUN")
        .sum(min_count=1)
        .rename(columns={"dengue_conf": "cases"})
        .reset_index()
        .rename(columns={"date": "week"})
    )
    weekly["state"] = "MG"
    weekly["deaths"] = 0

    out_path = PROCESSED_DIR / "dengue_weekly_mg.parquet"
    weekly.to_parquet(out_path, index=False)
    print(f"[mg] wrote weekly parquet -> {out_path}")
    return out_path

def run():
    pdf = fetch_mg_bulletin()
    parsed = parse_mg_pdf(pdf)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    (INTERIM_DIR / "mg_bulletin_last.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[mg] parsed -> {INTERIM_DIR/'mg_bulletin_last.json'}")
    save_mg_timeseries(parsed)

if __name__ == "__main__":
    run()
