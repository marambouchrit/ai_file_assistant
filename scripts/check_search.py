"""Index the sample documents, then run a search and print the best chunks.

Usage: python -m scripts.check_search "your question" [filename-to-filter-on]
"""

import shutil
import sys
from pathlib import Path

from app.config import settings
from app.ingestion.indexer import index_document, load_metadata, search

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def index_samples() -> None:
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    indexed = {d["filename"] for d in load_metadata().values()}
    for sample in sorted(SAMPLES.iterdir()):
        if sample.name in indexed:
            continue
        # same steps /upload will do: save the file in data/docs, then index it
        target = settings.docs_dir / sample.name
        shutil.copy(sample, target)
        entry = index_document(target)
        print(f"indexed {entry['filename']}: {entry['chunk_count']} chunks, doc_id={entry['doc_id']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    index_samples()

    doc_id = None
    if len(sys.argv) > 2:
        doc_id = next(d["doc_id"] for d in load_metadata().values() if d["filename"] == sys.argv[2])

    print(f"\nQuery: {sys.argv[1]}" + (f"  (only in {sys.argv[2]})" if doc_id else ""))
    for hit in search(sys.argv[1], top_k=3, doc_id=doc_id):
        print(f"\n[{hit['score']}] {hit['filename']} #{hit['chunk_index']}\n{hit['text'][:300]}")
