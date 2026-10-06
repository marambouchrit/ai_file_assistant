# AI File Assistant

Chat with your own documents. Upload PDF, DOCX or TXT files, ask questions in English or French, and get answers that cite the file they came from.

The assistant is built on the **Model Context Protocol (MCP)**: the LLM does not have the documents in its prompt. It discovers four tools exposed by an MCP server and decides by itself which ones to call to answer each question.

**Stack:** Python · MCP · FastAPI · Gemini (OpenAI-compatible API) · Qdrant · FastEmbed · React · TypeScript · Tailwind CSS

## How it works

```
React (Vite) ──HTTP──► FastAPI ──stdio──► MCP server (4 tools)
 upload, chat          │  ├─ /upload: parse → chunk → embed → Qdrant
                       │  └─ /chat:   LLM ⇄ tool-calling loop   │
                       └───────────── Qdrant (Docker) ◄─────────┘
                                      data/docs/ + metadata.json
```

**Uploading a file.** FastAPI saves the file, extracts its text, splits it into overlapping chunks of about 450 characters, turns each chunk into a 384-dimension vector with a local embedding model, and stores the vectors in Qdrant. No LLM is involved.

**Asking a question.** FastAPI sends the question and the list of tools to the LLM. The LLM replies with the tool it wants to call, FastAPI runs it through the MCP server and sends the result back. This repeats (five rounds at most) until the LLM writes its answer. The response includes the answer, the tools that were called and the passages that were retrieved.

The tools are discovered, not hardcoded: at startup FastAPI asks the MCP server for its tool list and converts it to the format the LLM expects. Adding a tool to the server makes it available to the LLM with no other change. The same server can also be plugged into any other MCP client, such as Claude Desktop.

### MCP tools

| Tool | Parameters | Returns |
|---|---|---|
| `list_documents` | none | id, filename and type of every document |
| `read_document` | `doc_id`, `max_chars=4000` | the beginning of the document's text |
| `get_document_metadata` | `doc_id` | size, page count, upload date, chunk count |
| `search_documents` | `query`, `top_k=5`, `doc_id=None` | the most relevant passages, with source and score |

### Data stores

| Store | Content |
|---|---|
| Qdrant | one point per chunk: the vector plus `doc_id`, `filename`, `chunk_index`, `text` |
| `data/metadata.json` | one entry per document: name, type, size, pages, upload date, chunk count |
| `data/docs/` | the original uploaded files |

## Setup

You need Python 3.12, Node.js 20.19 or newer, Docker, and an API key for an LLM. The default is Google Gemini, whose key is free to create at [aistudio.google.com](https://aistudio.google.com).

**1. Start Qdrant**

```bash
docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

**2. Install and configure the backend**

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS / Linux: cp .env.example .env
```

Open `.env` and set `LLM_API_KEY` to your key.

**3. Start the API**

```bash
uvicorn app.api:app --reload
```

The first start downloads the embedding model (about 220 MB). The API is then at http://127.0.0.1:8000 and its interactive documentation at http://127.0.0.1:8000/docs.

**4. Start the frontend**, in a second terminal

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, upload a document and ask a question. Three sample documents are provided in `data/samples/`.

If port 6333 or 8000 is already taken on your machine, change the port in the command and update `QDRANT_URL` in `.env` or `VITE_API_URL` in `frontend/.env`.

### Using another LLM

Any provider with an OpenAI-compatible chat API works. Set three values in `.env`:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| Gemini (default) | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.5-flash-lite` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

## Example questions

With the sample documents uploaded:

- Which documents do I have?
- How many days per week can employees work remotely?
- Quel est le budget total du projet Atlas et combien a déjà été dépensé ?
- How many pages does the remote work policy have?
- Summarise the meeting notes in two sentences.
- What is the company's policy on parental leave? *(not in the documents: the assistant says so instead of guessing)*

Questions and documents can be in different languages.

## Evaluation

The assistant was evaluated on 20 questions about the three sample documents ([eval/questions.json](eval/questions.json)), in English and French. Each question has an expected answer and an expected source written before the run.

| Category | Questions | Correct answer | Right source or tool |
|---|---|---|---|
| Factual, one document | 9 | 9 | 9 |
| Needs the right document | 4 | 4 | 4 |
| Metadata and listing | 4 | 4 | 4 |
| No answer in the documents | 3 | 3 (all said "not found") | n/a |
| **Total** | **20** | **20** | **17 / 17** |

- **Hallucinations: 0 of 20**, checked by reading every answer against the documents.
- **Speed:** 2.7 s per answer on average (7.3 s at most), with 1.6 tool calls per question.
- **Source precision:** the expected file was always among the displayed sources, but in 8 of the 13 content questions the list also included a passage from another file.

How to read these numbers: this is a single run with `gemini-3.5-flash-lite` on a small corpus of three short documents, and the questions were written by the author of the system. LLM answers vary between runs. The result shows that the pipeline works end to end, not how it would perform on a large or messy document set.

To reproduce, start the API with the three files of `data/samples/` uploaded, then:

```bash
python eval/run_eval.py
```

The script pauses between questions to stay under the free-tier rate limit, checks each answer for the expected key facts, and writes [eval/results.json](eval/results.json) with every answer, the tools called and the sources.

## Tests

```bash
pytest
```

`tests/test_chunker.py` checks chunk sizes and overlap. `tests/test_tools.py` runs the MCP tools against Qdrant in a separate collection, so your documents are not touched; these tests are skipped when Qdrant is not running.

To try the MCP server on its own, without an LLM, use the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python -m app.mcp_server
```

## Project structure

```
app/
├── ingestion/
│   ├── parsers.py      # PDF / DOCX / TXT → clean text
│   ├── chunker.py      # text → overlapping chunks
│   └── indexer.py      # embed, store in Qdrant, metadata.json, search
├── config.py           # settings from .env
├── mcp_server.py       # MCP server exposing the 4 tools
├── mcp_client.py       # starts the server over stdio, list_tools / call_tool
├── agent.py            # LLM tool-calling loop
└── api.py              # FastAPI: /upload, /documents, /chat
frontend/src/
├── types.ts            # interfaces mirroring the API models
├── api.ts              # fetch wrappers
├── App.tsx             # layout: sidebar + chat
└── components/         # UploadPanel, DocumentList, Chat, Message
data/samples/           # three sample documents
eval/                   # questions.json, run_eval.py, results.json
tests/
```

## Design notes

- **No RAG framework.** Parsing, chunking, embedding and search are written directly with `pypdf`, `python-docx`, FastEmbed and `qdrant-client`.
- **Chunk size follows the embedding model.** `paraphrase-multilingual-MiniLM-L12-v2` reads only the first 128 tokens of a text, so chunks are 450 characters with a 60-character overlap. Changing the embedding model means re-indexing every document.
- **Qdrant runs as a server**, because the API and the MCP server are two processes that both need it.
- **Re-uploading a file** with the same name replaces its chunks and keeps its `doc_id`.
- **Tool descriptions drive behaviour.** The LLM only sees each tool's name, parameters and docstring, so the docstrings say when to use each tool.

## Limitations

- Scanned PDFs (images without a text layer) are rejected: there is no OCR.
- Uploads are limited to 10 MB (`MAX_UPLOAD_MB`).
- Single user, no authentication, no streaming of answers.
- The free Gemini tier is rate limited; when the limit is reached the chat asks you to wait a few seconds.
