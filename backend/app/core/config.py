from functools import lru_cache
from typing import Optional, Set
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BACKEND_DIR / "vyaparshield.db"
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{DB_FILE.as_posix()}"
DEFAULT_SYNC_SQLITE_URL = f"sqlite:///{DB_FILE.as_posix()}"

INSECURE_SECRET_PLACEHOLDERS: Set[str] = {
    "default-insecure-secret-key-change-in-production-min32",
    "change-this-to-a-secure-random-secret-key-in-production-min-32-chars",
    "secret",
    "secretkey",
    "changeme",
    "password",
    "12345678901234567890123456789012",
}


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
    
    # Redis & Readiness
    REDIS_URL: str = "redis://localhost:6379/0"
    REQUIRE_REDIS_READY: bool = False
    REDIS_TIMEOUT_SECONDS: float = 2.0
    DB_TIMEOUT_SECONDS: float = 2.0

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

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        env_normalized = self.APP_ENV.strip().lower()
        is_production = env_normalized in ("production", "prod", "staging")

        if is_production:
            secret = (self.SECRET_KEY or "").strip()
            if not secret or secret in INSECURE_SECRET_PLACEHOLDERS or len(secret) < 32 or "change-in-production" in secret:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: When APP_ENV='production', a secure, "
                    "non-placeholder SECRET_KEY with at least 32 characters must be provided via the "
                    "environment."
                )
            if self.DEBUG:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: DEBUG mode cannot be enabled (DEBUG=True) "
                    "when running in production (APP_ENV='production')."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR.parent / ".env"), str(BACKEND_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
