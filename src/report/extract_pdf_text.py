from pathlib import Path
import pdfplumber
from typing import Optional, Tuple, List

def _read_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

def get_current_and_previous_pdf_text(pdf_dir: Path) -> Tuple[str, Optional[str]]:
    """Pega o texto do PDF mais recente e (se houver) do anterior."""
    pdfs: List[Path] = sorted(pdf_dir.glob("boletim_mg_*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Nenhum PDF em {pdf_dir}")
    current = pdfs[-1]
    prev = pdfs[-2] if len(pdfs) >= 2 else None
    current_text = _read_pdf_text(current)
    prev_text = _read_pdf_text(prev) if prev else None
    return current_text, prev_text
