import json
import logging
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.logging import SensitiveDataRedactor, JSONLogFormatter, correlation_id_ctx


def test_sensitive_data_redactor_text():
    text = "User with password='Secret123!' and token='Bearer eyJhbGciOiJIUzI1NiJ9.abc' and PAN ABCDE1234F"
    redacted = SensitiveDataRedactor.redact_text(text)
    assert "Secret123!" not in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted or "[REDACTED]" in redacted
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_PAN]" in redacted


def test_sensitive_data_redactor_dict():
    payload = {
        "email": "user@example.com",
        "password": "plain_password_123",
        "nested": {
            "secret_key": "confidential_api_token",
            "pan": "ABCDE1234F",
            "public_id": 12345,
        },
    }
    redacted = SensitiveDataRedactor.redact_dict(payload)
    assert redacted["email"] == "user@example.com"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["secret_key"] == "[REDACTED]"
    assert redacted["nested"]["pan"] == "[REDACTED]"
    assert redacted["nested"]["public_id"] == 12345


def test_json_log_formatter():
    formatter = JSONLogFormatter()
    token = correlation_id_ctx.set("test-corr-id-999")
    try:
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Connected to postgresql+asyncpg://user:secretpass@localhost:5432/db",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["correlation_id"] == "test-corr-id-999"
        assert "secretpass" not in data["message"]
        assert "[REDACTED_PASSWORD]" in data["message"]
    finally:
        correlation_id_ctx.reset(token)


@pytest.mark.asyncio
async def test_correlation_id_header_middleware():
    transport = ASGITransport(app=app)
    custom_cid = "client-trace-id-abc12345"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request with client-supplied correlation ID
        resp = await client.get("/healthz", headers={"X-Request-ID": custom_cid})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == custom_cid

        # Request without header gets auto-generated ID
        resp_auto = await client.get("/healthz")
        assert resp_auto.status_code == 200
        assert "X-Request-ID" in resp_auto.headers
        assert len(resp_auto.headers["X-Request-ID"]) >= 16
