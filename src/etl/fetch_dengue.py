from pathlib import Path

RAW_DIR = Path("data/raw")
SRC = RAW_DIR / "mock_dengue.csv"
DEST = RAW_DIR / "ingest.csv"

MOCK_CSV = """date,state,city,cases,deaths
2025-09-28,MG,Belo Horizonte,120,0
2025-09-28,RJ,Rio de Janeiro,85,0
2025-10-05,MG,Belo Horizonte,140,1
2025-10-05,RJ,Rio de Janeiro,110,0
2025-10-12,MG,Belo Horizonte,90,0
2025-10-12,RJ,Rio de Janeiro,160,2
2025-10-19,MG,Belo Horizonte,130,0
2025-10-19,RJ,Rio de Janeiro,150,1
"""

def fetch_dengue():
    """Garante dados de exemplo no CI e copia para ingest.csv."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        SRC.write_text(MOCK_CSV, encoding="utf-8")
        print(f"[fetch] created mock {SRC}")
    DEST.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[fetch] {SRC} -> {DEST}")
