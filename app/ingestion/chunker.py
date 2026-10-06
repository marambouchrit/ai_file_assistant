def _cut_point(text: str, start: int, end: int) -> int:
    """Move `end` back to the nearest whitespace so a chunk never ends mid-word."""
    if text[end].isspace():
        return end
    for i in range(end - 1, start, -1):
        if text[i].isspace():
            return i
    return end  # one word longer than the chunk: hard cut


def _word_start(text: str, pos: int, limit: int) -> int:
    """Move `pos` forward to the start of the next word, without passing `limit`."""
    while pos < limit and not text[pos - 1].isspace():
        pos += 1
    while pos < limit and text[pos].isspace():
        pos += 1
    return pos


def chunk_text(text: str, chunk_size: int = 450, overlap: int = 60) -> list[str]:
    """Split text into chunks of at most `chunk_size` characters.

    Consecutive chunks share up to `overlap` characters, and both ends of a
    chunk fall on whitespace so words are never split.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    text = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            end = _cut_point(text, start, end)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break

        # start + 1 guarantees progress even if the chunk was shorter than the overlap
        start = _word_start(text, max(end - overlap, start + 1), end)
    return chunks
