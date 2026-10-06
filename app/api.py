from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import openai
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client.http.exceptions import ResponseHandlingException

from app.agent import run_agent
from app.config import settings
from app.ingestion.indexer import EmptyDocumentError, index_document, load_metadata
from app.ingestion.parsers import SUPPORTED_EXTENSIONS, DocumentParseError
from app.mcp_client import MCPClient, to_openai_tools


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    type: str
    size_bytes: int
    pages: int | None
    uploaded_at: str
    chunk_count: int


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


class ToolCall(BaseModel):
    name: str
    arguments: dict


class Source(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int | None
    score: float | None
    text: str


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCall]
    sources: list[Source]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # the MCP server subprocess lives for the whole life of the API
    async with MCPClient() as mcp:
        app.state.mcp = mcp
        app.state.tools = to_openai_tools(await mcp.list_tools())
        # the openai library is only the HTTP client; base_url decides which provider answers
        app.state.llm = openai.AsyncOpenAI(
            api_key=settings.llm_api_key or "missing", base_url=settings.llm_base_url
        )
        yield


app = FastAPI(title="AI File Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload", response_model=DocumentInfo)
async def upload(file: UploadFile):
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, f"Unsupported file type. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, "The file is empty.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"The file is too large (limit: {settings.max_upload_mb} MB).")

    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    path = settings.docs_dir / filename
    previous = path.read_bytes() if path.exists() else None
    path.write_bytes(content)
    try:
        # parsing and embedding are blocking, so keep them off the event loop
        return await run_in_threadpool(index_document, path)
    except Exception as exc:
        # indexing failed: put data/docs back the way it was
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(previous)
        if isinstance(exc, (EmptyDocumentError, DocumentParseError)):
            raise HTTPException(400, str(exc))
        if isinstance(exc, ResponseHandlingException):
            raise HTTPException(503, "Cannot reach the vector database. Is Qdrant running?")
        raise


@app.get("/documents", response_model=list[DocumentInfo])
def documents():
    return list(load_metadata().values())


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(400, "The message is empty.")
    if not settings.llm_api_key:
        raise HTTPException(503, "LLM_API_KEY is not set in the .env file.")
    try:
        return await run_agent(
            request.message,
            [m.model_dump() for m in request.history],
            app.state.llm,
            app.state.mcp,
            app.state.tools,
        )
    except openai.RateLimitError:
        raise HTTPException(
            429, "The LLM rate limit was reached. Wait a few seconds and try again."
        )
    except openai.OpenAIError as exc:
        raise HTTPException(502, f"LLM request failed: {exc}")
