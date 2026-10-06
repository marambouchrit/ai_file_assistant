import pytest

from app.ingestion.chunker import chunk_text

# 600 distinct words, so every word can be traced back to its position
WORDS = [f"word{i}" for i in range(600)]
TEXT = " ".join(WORDS)


def test_short_text_is_one_chunk():
    assert chunk_text("hello world", chunk_size=450, overlap=60) == ["hello world"]


def test_empty_text_gives_no_chunks():
    assert chunk_text("   \n  ", chunk_size=450, overlap=60) == []


def test_chunks_respect_max_size():
    chunks = chunk_text(TEXT, chunk_size=450, overlap=60)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 450 for chunk in chunks)


def test_words_are_never_split_and_none_is_lost():
    chunks = chunk_text(TEXT, chunk_size=450, overlap=60)
    seen = [word for chunk in chunks for word in chunk.split()]
    assert set(seen) == set(WORDS)


def test_consecutive_chunks_overlap():
    chunks = chunk_text(TEXT, chunk_size=450, overlap=60)
    for current, following in zip(chunks, chunks[1:]):
        shared = set(current.split()) & set(following.split())
        assert shared, "consecutive chunks share no words"
        # the shared part is the end of one chunk and the start of the next
        assert following.startswith(" ".join(current.split()[-len(shared):]))
        assert len(" ".join(shared)) <= 60


def test_no_overlap_when_overlap_is_zero():
    chunks = chunk_text(TEXT, chunk_size=450, overlap=0)
    seen = [word for chunk in chunks for word in chunk.split()]
    assert seen == WORDS


@pytest.mark.parametrize("chunk_size, overlap", [(0, 0), (100, 100), (100, -1)])
def test_invalid_settings_are_rejected(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size, overlap=overlap)
