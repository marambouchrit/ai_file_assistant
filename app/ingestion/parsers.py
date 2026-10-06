import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.table import Table
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class UnsupportedFormatError(ValueError):
    """Raised when a file extension is not one of SUPPORTED_EXTENSIONS."""


@dataclass
class ParsedDocument:
    text: str
    file_type: str
    pages: int | None = None  # only known for PDFs


def clean_text(text: str) -> str:
    """Normalise whitespace: single spaces, at most one blank line in a row."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf(path: Path) -> ParsedDocument:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return ParsedDocument(
        text=clean_text("\n\n".join(pages)),
        file_type="pdf",
        pages=len(reader.pages),
    )


def parse_docx(path: Path) -> ParsedDocument:
    doc = Document(str(path))
    blocks: list[str] = []
    # iter_inner_content yields paragraphs and tables in document order
    for block in doc.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                blocks.append(" | ".join(cell.text.strip() for cell in row.cells))
        else:
            blocks.append(block.text)
    return ParsedDocument(text=clean_text("\n".join(blocks)), file_type="docx")


def parse_txt(path: Path) -> ParsedDocument:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Windows-saved files are often cp1252; it decodes any byte sequence
        text = raw.decode("cp1252", errors="replace")
    return ParsedDocument(text=clean_text(text), file_type="txt")


_PARSERS = {".pdf": parse_pdf, ".docx": parse_docx, ".txt": parse_txt}


def parse_file(path: str | Path) -> ParsedDocument:
    """Extract clean text from a PDF, DOCX or TXT file, chosen by extension."""
    path = Path(path)
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(
            f"Unsupported file type '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return parser(path)
