"""Centralized application configuration, loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Project metadata ---
    PROJECT_NAME: str = "Nexus"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # --- CORS ---
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- Database (PostgreSQL) ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://nexus:nexus@localhost:5432/nexus"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://nexus:nexus@localhost:5432/nexus"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # --- JWT Authentication ---
    SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION_ENV_FILE")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Vector store (Qdrant) ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_PREFIX: str = "nexus_repo_"
    VECTOR_SIZE: int = 1536

    # --- LLM provider (swappable) ---
    LLM_PROVIDER: Literal["openai", "claude"] = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str | None = None
    CLAUDE_CHAT_MODEL: str = "claude-sonnet-4-20250514"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 2048

    # --- Embeddings (swappable) ---
    EMBEDDING_PROVIDER: Literal["openai", "bge"] = "openai"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    BGE_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"

    # --- Retrieval (RAG) ---
    RETRIEVAL_TOP_K: int = 8
    RETRIEVAL_SCORE_THRESHOLD: float | None = None

    # --- Repository processing / uploads ---
    STORAGE_PATH: str = str(BACKEND_ROOT / "storage")
    UPLOAD_DIR: str = str(BACKEND_ROOT / "storage" / "uploads")
    REPOS_DIR: str = str(BACKEND_ROOT / "storage" / "repos")
    MAX_UPLOAD_SIZE_MB: int = 200
    ALLOWED_UPLOAD_EXTENSIONS: Annotated[List[str], NoDecode] = [".zip"]
    MAX_REPO_SIZE_MB: int = 500
    MAX_FILE_SIZE_MB: int = 5
    MAX_CHUNK_SIZE_TOKENS: int = 800
    CHUNK_OVERLAP_TOKENS: int = 100
    IGNORED_DIRECTORIES: Annotated[List[str], NoDecode] = [
        "node_modules",
        ".git",
        "dist",
        "build",
        "vendor",
        "coverage",
        "__pycache__",
        ".next",
        ".venv",
        "venv",
        ".pytest_cache",
        "target",
    ]

    @field_validator("ALLOWED_UPLOAD_EXTENSIONS", "IGNORED_DIRECTORIES", mode="before")
    @classmethod
    def assemble_comma_separated_list(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_JSON: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
