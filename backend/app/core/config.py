from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://nexusops:nexusops_secure_password@localhost:5432/nexusops_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://nexusops:nexusops_secure_password@localhost:5432/nexusops_db"
    
    # Redis & Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Object Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./storage_data"
    
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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
