""" parse and chunk the given files and print a summary.

Usage: python -m scripts.check_ingestion data/samples/*
"""

import sys
from pathlib import Path

from app.config import settings
from app.ingestion.chunker import chunk_text
from app.ingestion.parsers import parse_file


def check(path: Path) -> None:
    doc = parse_file(path)
    chunks = chunk_text(doc.text, settings.chunk_size, settings.chunk_overlap)
    sizes = [len(c) for c in chunks]

    print(f"=== {path.name} ===")
    print(f"type={doc.file_type}  pages={doc.pages}  chars={len(doc.text)}  chunks={len(chunks)}")
    if not chunks:
        print("(no text extracted)\n")
        return
    print(f"chunk sizes: min={min(sizes)} max={max(sizes)} avg={sum(sizes) // len(sizes)}")
    print(f"--- chunk 0 ---\n{chunks[0]}")
    if len(chunks) > 1:
        print(f"--- chunk 1 (first 200 chars) ---\n{chunks[1][:200]}")
    print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        sys.exit(__doc__)
    for p in paths:
        check(p)
