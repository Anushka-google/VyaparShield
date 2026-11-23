from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BACKEND_DIR / "vyaparshield.db"
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{DB_FILE.as_posix()}"
DEFAULT_SYNC_SQLITE_URL = f"sqlite:///{DB_FILE.as_posix()}"


class Settings(BaseSettings):
    # Core Application
    APP_NAME: str = "NexusOps AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Security & Tokens
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production-min32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Server Binding
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # Database (defaults to local SQLite with absolute path for zero-friction local execution)
    DATABASE_URL: str = DEFAULT_SQLITE_URL
    DATABASE_SYNC_URL: str = DEFAULT_SYNC_SQLITE_URL

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    # Redis & Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Object Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = str(BACKEND_DIR / "storage_data")
    
    # LLM & AI Providers
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    EMBEDDING_MODEL_NAME: str = "text-embedding-004"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # AgentGuard Security Policies
    AGENT_POLICY_DENY_BY_DEFAULT: bool = True
    ENABLE_HUMAN_APPROVAL_GATE: bool = True
    MAX_AUTONOMOUS_TOOL_BUDGET: int = 5
    REDACT_SENSITIVE_LOGS: bool = True
    
    # Observability
    ENABLE_OPENTELEMETRY: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    PROMETHEUS_METRICS_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR.parent / ".env"), str(BACKEND_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
