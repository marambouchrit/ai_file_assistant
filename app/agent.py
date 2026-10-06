import json

from openai import AsyncOpenAI

from app.config import settings
from app.mcp_client import MCPClient

MAX_ITERATIONS = 5

SYSTEM_PROMPT = """You are a document assistant. You answer questions about the files the user has uploaded.

Rules:
- Use the tools to look up information. Never answer from your own general knowledge.
- Base every statement on the tool results, and cite the filename of each document you used.
- If the tools do not return the information, say that it was not found in the documents. Do not guess.
- Answer in the language of the user's question."""


def _collect_sources(tool_name: str, result: str, sources: list[dict]) -> None:
    """Add the passages or documents a tool returned to `sources`, without duplicates."""
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict) or "error" in data:
        return

    if tool_name == "search_documents":
        found = [
            {
                "doc_id": r["doc_id"],
                "filename": r["filename"],
                "chunk_index": r["chunk_index"],
                "score": r["score"],
                "text": r["text"],
            }
            for r in data.get("results", [])
        ]
    elif tool_name == "read_document":
        found = [
            {
                "doc_id": data["doc_id"],
                "filename": data["filename"],
                "chunk_index": None,
                "score": None,
                "text": data["text"][:300],
            }
        ]
    else:
        return

    seen = {(s["doc_id"], s["chunk_index"]) for s in sources}
    for source in found:
        if (source["doc_id"], source["chunk_index"]) not in seen:
            seen.add((source["doc_id"], source["chunk_index"]))
            sources.append(source)


async def run_agent(
    message: str,
    history: list[dict],
    llm: AsyncOpenAI,
    mcp: MCPClient,
    tools: list[dict],
) -> dict:
    """Answer `message` by letting the model call MCP tools until it has an answer.

    Returns {"answer", "tool_calls", "sources"}.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]
    tool_calls: list[dict] = []
    sources: list[dict] = []

    for iteration in range(MAX_ITERATIONS + 1):
        # after MAX_ITERATIONS rounds of tools, force a final answer without tools
        last_round = iteration == MAX_ITERATIONS
        response = await llm.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="none" if last_round else "auto",
        )
        reply = response.choices[0].message
        if not reply.tool_calls:
            return {"answer": reply.content or "", "tool_calls": tool_calls, "sources": sources}

        messages.append(reply.model_dump(exclude_none=True))
        for call in reply.tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = await mcp.call_tool(name, arguments)
            except json.JSONDecodeError:
                arguments = {}
                result = json.dumps({"error": "The tool arguments were not valid JSON."})
            tool_calls.append({"name": name, "arguments": arguments})
            _collect_sources(name, result, sources)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return {"answer": reply.content or "", "tool_calls": tool_calls, "sources": sources}
