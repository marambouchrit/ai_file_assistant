"""Tests of the MCP tools against a real Qdrant instance.

They use a separate collection and a temporary data folder, so the real
documents are never touched. Skipped when Qdrant is not running.
"""

import json

import pytest

from app.config import settings
from app.ingestion.indexer import get_client, index_document
from app.mcp_server import get_document_metadata, list_documents, read_document, search_documents

TEXT = (
    "The warranty for the Orion X2 drone lasts 24 months. "
    "It covers motor failures but not water damage. "
    "Returns are accepted within 30 days of purchase."
)


@pytest.fixture
def indexed_doc(tmp_path, monkeypatch):
    try:
        get_client().get_collections()
    except Exception:
        pytest.skip("Qdrant is not running")

    monkeypatch.setattr(settings, "qdrant_collection", "test_documents")
    monkeypatch.setattr(settings, "docs_dir", tmp_path / "docs")
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "metadata.json")
    settings.docs_dir.mkdir()

    path = settings.docs_dir / "warranty.txt"
    path.write_text(TEXT, encoding="utf-8")
    yield index_document(path)
    get_client().delete_collection("test_documents")


def test_search_returns_results_for_indexed_document(indexed_doc):
    data = json.loads(search_documents("How long is the drone warranty?"))

    assert data["results"], "no results returned"
    top = data["results"][0]
    assert top["filename"] == "warranty.txt"
    assert top["doc_id"] == indexed_doc["doc_id"]
    assert "24 months" in top["text"]
    assert 0 < top["score"] <= 1


def test_search_can_be_restricted_to_one_document(indexed_doc):
    data = json.loads(search_documents("warranty", doc_id=indexed_doc["doc_id"]))
    assert all(r["doc_id"] == indexed_doc["doc_id"] for r in data["results"])


@pytest.mark.parametrize(
    "call",
    [
        lambda: search_documents("warranty", doc_id="unknown-id"),
        lambda: read_document("unknown-id"),
        lambda: get_document_metadata("unknown-id"),
    ],
)
def test_unknown_doc_id_gives_a_clean_error(indexed_doc, call):
    data = json.loads(call())
    assert "unknown-id" in data["error"]
    assert "list_documents" in data["error"]


def test_list_metadata_and_read(indexed_doc):
    doc_id = indexed_doc["doc_id"]

    listed = json.loads(list_documents())["documents"]
    assert listed == [{"doc_id": doc_id, "filename": "warranty.txt", "type": "txt"}]

    metadata = json.loads(get_document_metadata(doc_id))
    assert metadata["chunk_count"] == 1 and metadata["pages"] is None

    read = json.loads(read_document(doc_id, max_chars=20))
    assert read["text"] == TEXT[:20] and read["truncated"] is True


def test_no_documents_gives_a_message_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "metadata.json")

    assert json.loads(list_documents())["documents"] == []
    data = json.loads(search_documents("anything"))
    assert data["results"] == [] and "No documents" in data["message"]
