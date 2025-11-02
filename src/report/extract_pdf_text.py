from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pdfplumber

# Ajuste os caminhos aqui se desejar outra pasta
CURRENT = Path("inputs/mg/current.pdf")
PREVIOUS = Path("inputs/mg/previous.pdf")  # opcional


def _read_pdf_text(path: Path) -> str:
    """
    Lê todo o texto de um PDF concatenando as páginas.
    Retorna string vazia se uma página não tiver texto extraível.
    """
    with pdfplumber.open(path) as pdf:
        parts = []
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()


def get_current_and_previous_pdf_text() -> Tuple[str, Optional[str]]:
    """
    Retorna (texto_atual, texto_anterior_ou_None).
    Levanta FileNotFoundError se o PDF 'current.pdf' não existir.
    """
    if not CURRENT.exists():
        raise FileNotFoundError(
            f"PDF atual não encontrado: {CURRENT.resolve()}. "
            "Crie inputs/mg/current.pdf antes de rodar."
        )

    current_text = _read_pdf_text(CURRENT)
    prev_text = _read_pdf_text(PREVIOUS) if PREVIOUS.exists() else None
    return current_text, prev_text
