import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request correlation tracking across async tasks
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    cid = correlation_id_ctx.get()
    if not cid:
        cid = uuid.uuid4().hex
        correlation_id_ctx.set(cid)
    return cid


class SensitiveDataRedactor:
    """
    Sanitizes log messages, query parameters, and dictionaries to prevent
    leakage of credentials, bearer tokens, API keys, PANs, and PII.
    """

    PATTERNS = [
        # Bearer tokens
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
        # Key/value patterns like password="xyz" or secret: 'xyz'
        (re.compile(r'((?:password|secret|token|api_key|access_token|authorization|auth_token)\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE), r"\1[REDACTED]\3"),
        # Database connection strings with passwords
        (re.compile(r'(postgres(?:ql)?(?:\+[a-z]+)?://[^:]+:)([^@]+)(@)', re.IGNORECASE), r"\1[REDACTED_PASSWORD]\3"),
        # Indian PAN (5 letters, 4 digits, 1 letter)
        (re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b'), r"[REDACTED_PAN]"),
    ]

    SENSITIVE_KEYS = {
        "password",
        "hashed_password",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "authorization",
        "api_key",
        "gemini_api_key",
        "openai_api_key",
        "anthropic_api_key",
        "pan",
    }

    @classmethod
    def redact_text(cls, text: str) -> str:
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        redacted = {}
        for k, v in data.items():
            if str(k).lower() in cls.SENSITIVE_KEYS:
                redacted[k] = "[REDACTED]"
            elif isinstance(v, dict):
                redacted[k] = cls.redact_dict(v)
            elif isinstance(v, (list, tuple)):
                redacted[k] = [cls.redact_dict(item) if isinstance(item, dict) else (cls.redact_text(str(item)) if isinstance(item, str) else item) for item in v]
            elif isinstance(v, str):
                redacted[k] = cls.redact_text(v)
            else:
                redacted[k] = v
        return redacted


class JSONLogFormatter(logging.Formatter):
    """
    Formats standard library log records into structured JSON objects
    with correlation IDs and PII redaction.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": SensitiveDataRedactor.redact_text(record.getMessage()),
            "correlation_id": correlation_id_ctx.get() or getattr(record, "correlation_id", None),
        }

        if record.exc_info:
            log_payload["exception"] = SensitiveDataRedactor.redact_text(self.formatException(record.exc_info))

        # Include custom extra fields if present
        for k, v in record.__dict__.items():
            if k not in {"msg", "args", "levelname", "levelno", "pathname", "filename", "module",
                         "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
                         "msecs", "relativeCreated", "thread", "threadName", "processName",
                         "process", "name", "correlation_id"}:
                if isinstance(v, dict):
                    log_payload[k] = SensitiveDataRedactor.redact_dict(v)
                elif isinstance(v, str):
                    log_payload[k] = SensitiveDataRedactor.redact_text(v)
                else:
                    log_payload[k] = v

        return json.dumps(log_payload)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Extracts or injects X-Request-ID / X-Correlation-ID headers and sets
    the request-scoped correlation ID context for logs and responses.
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or uuid.uuid4().hex
        )
        token = correlation_id_ctx.set(correlation_id)

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = correlation_id
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)


def setup_structured_logging(log_level: str = "INFO"):
    """Configures root and application loggers to emit structured JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    # Replace existing handlers with JSON handler
    root_logger.handlers = [handler]
