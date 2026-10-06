from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings, read from environment variables or the .env file."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Any provider with an OpenAI-compatible chat API works (Gemini, OpenAI, Groq, ...)
    llm_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # 127.0.0.1 rather than localhost: on Windows localhost adds ~2s per request
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "documents"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    embedding_cache_dir: Path = BASE_DIR / ".cache" / "fastembed"

    # The embedding model only reads the first 128 tokens (~480 chars) of a chunk
    chunk_size: int = 450
    chunk_overlap: int = 60

    max_upload_mb: int = 10

    docs_dir: Path = BASE_DIR / "data" / "docs"
    metadata_path: Path = BASE_DIR / "data" / "metadata.json"


settings = Settings()
