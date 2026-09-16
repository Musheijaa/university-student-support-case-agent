"""Application configuration.

Loads settings from environment variables (and a local .env file in
development). No secret values are hardcoded anywhere in this module.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "student-support-case-agent"
    log_level: str = "INFO"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    # Prompt version currently served by the API. Switching this constant
    # is how we move between Prompt V1, V2, and the Week 3 RAG prompt
    # without code changes elsewhere in the application.
    active_prompt_version: str = "rag-v1.0"

    # Week 3: RAG configuration.
    embedding_model: str = "chroma-default"
    chroma_persist_directory: str = "data/chroma"
    rag_top_k: int = 4
    rag_min_score: float = 0.35
    rag_corpus_dir: str = "../docs/makerereUniversityPolicyDocs"
    rag_collection_name: str = "makerere_policy_docs"

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so environment variables are read once per process; tests that
    need different configuration should clear the cache explicitly
    (see tests/test_main.py).
    """
    return Settings()
