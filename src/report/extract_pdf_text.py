from pathlib import Path
from typing import Optional, Tuple
import pdfplumber

CURRENT = Path("inputs/mg/current.pdf")
PREVIOUS = Path("inputs/mg/previous.pdf")  # opcional

def _read_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

def get_current_and_previous_pdf_text() -> Tuple[str, Optional[str]]:
    if not CURRENT.exists():
        raise FileNotFoundError(f"PDF atual não encontrado: {CURRENT.resolve()}")
    current_text = _read_pdf_text(CURRENT)
    prev_text = _read_pdf_text(PREVIOUS) if PREVIOUS.exists() else None
    return current_text, prev_text
