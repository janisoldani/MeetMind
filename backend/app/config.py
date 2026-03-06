from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Datenbank
    database_url: str = "postgresql+asyncpg://meetmind:meetmind_dev@localhost:5432/meetmind"

    # KI-Provider
    llm_provider: str = "local"
    transcription_mode: str = "local"
    embedding_mode: str = "local"

    # OpenAI (Production)
    openai_api_key: str = ""

    # Ollama (MVP)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Whisper (MVP)
    whisper_model: str = "base"
    whisper_language: str = "de"

    # Embeddings (MVP)
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Auth — Clerk
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # Monitoring
    sentry_dsn: str = ""

    # File Storage
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 500

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
