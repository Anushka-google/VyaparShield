import pytest
from pydantic import ValidationError
from app.core.config import Settings, INSECURE_SECRET_PLACEHOLDERS


def test_development_config_allows_defaults():
    """Development settings allow local zero-friction defaults."""
    cfg = Settings(APP_ENV="development", DEBUG=True)
    assert cfg.APP_ENV == "development"
    assert cfg.DEBUG is True
    assert cfg.SECRET_KEY is not None


def test_production_rejects_default_placeholder_secret():
    """Production mode must reject default placeholder secret key."""
    for placeholder in INSECURE_SECRET_PLACEHOLDERS:
        with pytest.raises(ValidationError) as exc:
            Settings(APP_ENV="production", DEBUG=False, SECRET_KEY=placeholder)
        assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc.value)


def test_production_rejects_short_secret():
    """Production mode must reject secrets shorter than 32 characters."""
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEBUG=False, SECRET_KEY="short-secret-under-32-chars")
    assert "at least 32 characters" in str(exc.value)


def test_production_rejects_debug_enabled():
    """Production mode must reject DEBUG=True."""
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            DEBUG=True,
            SECRET_KEY="a-very-secure-random-production-secret-key-32chars",
        )
    assert "DEBUG mode cannot be enabled" in str(exc.value)


def test_production_accepts_strong_secret_and_debug_false():
    """Production mode succeeds when provided strong secret and DEBUG=False."""
    strong_key = "prod-super-secure-cryptographic-key-value-99128374612345"
    cfg = Settings(APP_ENV="production", DEBUG=False, SECRET_KEY=strong_key)
    assert cfg.APP_ENV == "production"
    assert cfg.DEBUG is False
    assert cfg.SECRET_KEY == strong_key
