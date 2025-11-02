from pathlib import Path
import shutil

RAW = Path("data/raw")
DEST = RAW / "ingest.csv"
SOURCE = RAW / "mock_dengue.csv"

def fetch_dengue():
    """Simula ingestão: copia o mock para 'ingest.csv'."""
    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, DEST)
    print(f"[fetch] {SOURCE} -> {DEST}")
