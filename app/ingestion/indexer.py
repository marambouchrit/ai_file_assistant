import json
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from app.config import settings
from app.ingestion.chunker import chunk_text
from app.ingestion.parsers import parse_file


class EmptyDocumentError(ValueError):
    """Raised when no text could be extracted from a file."""


@lru_cache
def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


@lru_cache
def get_embedder() -> TextEmbedding:
    return TextEmbedding(settings.embedding_model, cache_dir=str(settings.embedding_cache_dir))


def embed(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in get_embedder().embed(texts)]


def ensure_collection() -> None:
    """Create the Qdrant collection (and the doc_id index) if it does not exist yet."""
    client = get_client()
    if client.collection_exists(settings.qdrant_collection):
        return
    client.create_collection(
        settings.qdrant_collection,
        vectors_config=models.VectorParams(
            size=settings.embedding_dim, distance=models.Distance.COSINE
        ),
    )
    client.create_payload_index(
        settings.qdrant_collection, "doc_id", models.PayloadSchemaType.KEYWORD
    )


def load_metadata() -> dict[str, dict]:
    """Return all document entries, keyed by doc_id."""
    if not settings.metadata_path.exists():
        return {}
    return json.loads(settings.metadata_path.read_text(encoding="utf-8"))


def save_metadata(metadata: dict[str, dict]) -> None:
    settings.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    # write to a temp file first so a reader never sees a half-written file
    tmp = settings.metadata_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, settings.metadata_path)


def _doc_filter(doc_id: str) -> models.Filter:
    return models.Filter(
        must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
    )


def index_document(path: str | Path) -> dict:
    """Parse, chunk, embed and store one file. Returns its metadata entry.

    Indexing a filename that already exists replaces the old version and
    keeps the same doc_id.
    """
    path = Path(path)
    parsed = parse_file(path)
    chunks = chunk_text(parsed.text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise EmptyDocumentError(
            f"No text could be extracted from '{path.name}'. "
            "Empty files and scanned PDFs (images without text) are not supported."
        )

    ensure_collection()
    client = get_client()
    metadata = load_metadata()

    existing = next((d for d in metadata.values() if d["filename"] == path.name), None)
    if existing:
        doc_id = existing["doc_id"]
        client.delete(
            settings.qdrant_collection,
            points_selector=models.FilterSelector(filter=_doc_filter(doc_id)),
            wait=True,
        )
    else:
        doc_id = str(uuid.uuid4())

    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.UUID(doc_id), str(i))),
            vector=vector,
            payload={
                "doc_id": doc_id,
                "filename": path.name,
                "chunk_index": i,
                "text": chunk,
            },
        )
        for i, (chunk, vector) in enumerate(zip(chunks, embed(chunks)))
    ]
    client.upsert(settings.qdrant_collection, points=points, wait=True)

    entry = {
        "doc_id": doc_id,
        "filename": path.name,
        "type": parsed.file_type,
        "size_bytes": path.stat().st_size,
        "pages": parsed.pages,
        "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunk_count": len(chunks),
    }
    metadata[doc_id] = entry
    save_metadata(metadata)
    return entry


def search(query: str, top_k: int = 5, doc_id: str | None = None) -> list[dict]:
    """Return the `top_k` chunks most similar to `query`, optionally within one document."""
    client = get_client()
    if not client.collection_exists(settings.qdrant_collection):
        return []
    result = client.query_points(
        settings.qdrant_collection,
        query=embed([query])[0],
        query_filter=_doc_filter(doc_id) if doc_id else None,
        limit=top_k,
        with_payload=True,
    )
    return [{**point.payload, "score": round(point.score, 4)} for point in result.points]
