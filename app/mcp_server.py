"""MCP server exposing the document tools over stdio.

Run: python -m app.mcp_server
"""

import json

from mcp.server.mcpserver import MCPServer

from app.config import settings
from app.ingestion.indexer import load_metadata, search
from app.ingestion.parsers import parse_file

mcp = MCPServer(
    "ai-file-assistant",
    instructions=(
        "Tools to explore the user's uploaded documents. Call list_documents first "
        "to get the doc_id values the other tools need."
    ),
)


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _error(message: str) -> str:
    return _json({"error": message})


def _unknown_doc(doc_id: str) -> str:
    return _error(f"No document with doc_id '{doc_id}'. Call list_documents to see the valid ids.")


@mcp.tool()
def list_documents() -> str:
    """List every uploaded document with its doc_id, filename and type.

    Use this first: the other tools identify a document by its doc_id.
    """
    documents = [
        {"doc_id": d["doc_id"], "filename": d["filename"], "type": d["type"]}
        for d in load_metadata().values()
    ]
    if not documents:
        return _json({"documents": [], "message": "No documents have been uploaded yet."})
    return _json({"documents": documents})


@mcp.tool()
def read_document(doc_id: str, max_chars: int = 4000) -> str:
    """Read the raw text of one document from its beginning.

    Use this to summarise a document or read its introduction. For a specific
    question, prefer search_documents, which finds the relevant passages.

    Args:
        doc_id: Id of the document, as returned by list_documents.
        max_chars: Maximum number of characters to return (default 4000).
    """
    doc = load_metadata().get(doc_id)
    if doc is None:
        return _unknown_doc(doc_id)
    path = settings.docs_dir / doc["filename"]
    if not path.exists():
        return _error(f"The file for '{doc['filename']}' is missing on the server.")

    text = parse_file(path).text
    max_chars = max(1, max_chars)
    return _json(
        {
            "doc_id": doc_id,
            "filename": doc["filename"],
            "total_chars": len(text),
            "truncated": len(text) > max_chars,
            "text": text[:max_chars],
        }
    )


@mcp.tool()
def get_document_metadata(doc_id: str) -> str:
    """Get facts about one document: file size, page count, upload date, chunk count.

    Use this for questions about the file itself rather than its content.
    The page count is only known for PDF files (null otherwise).

    Args:
        doc_id: Id of the document, as returned by list_documents.
    """
    doc = load_metadata().get(doc_id)
    if doc is None:
        return _unknown_doc(doc_id)
    return _json(doc)


@mcp.tool()
def search_documents(query: str, top_k: int = 5, doc_id: str | None = None) -> str:
    """Semantic search: find the passages most relevant to a question.

    Use this to answer questions about the content of the documents. Each
    result has the passage text, the source filename and a similarity score
    (higher is more relevant). Works across languages.

    Args:
        query: The question or topic to search for, in natural language.
        top_k: Number of passages to return (default 5, maximum 20).
        doc_id: Optional. Restrict the search to this one document.
    """
    if not query.strip():
        return _error("The query is empty.")
    metadata = load_metadata()
    if not metadata:
        return _json({"results": [], "message": "No documents have been uploaded yet."})
    if doc_id is not None and doc_id not in metadata:
        return _unknown_doc(doc_id)

    results = search(query, top_k=min(max(top_k, 1), 20), doc_id=doc_id)
    if not results:
        return _json({"results": [], "message": "No matching passages found."})
    return _json({"results": results})


if __name__ == "__main__":
    mcp.run(transport="stdio")
