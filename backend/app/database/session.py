import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()

# SQLAlchemy 2.0 Async Engine with robust connection pooling
engine_kwargs = {"echo": settings.DEBUG, "future": True}
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class Base(DeclarativeBase):
    """Base model class with standard audit mixin fields."""
    pass


# -----------------------------------------------------------------------------
# Financial Money Utilities (Indian Rupee / Decimal Invariants)
# -----------------------------------------------------------------------------

PAISE_EXPONENT = Decimal("0.01")
PRECISION_EXPONENT = Decimal("0.0001")


def to_decimal(value: float | int | str | Decimal) -> Decimal:
    """Converts any numeric value to a strict Decimal, preventing float precision errors."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_currency(value: Decimal) -> Decimal:
    """Rounds currency to standard Indian paise (2 decimal places) using ROUND_HALF_UP."""
    return value.quantize(PAISE_EXPONENT, rounding=ROUND_HALF_UP)


def money_column(nullable: bool = False, default: Decimal = Decimal("0.0000")):
    """Standardized SQLAlchemy column definition for monetary amounts: NUMERIC(18, 4)."""
    return mapped_column(Numeric(18, 4), nullable=nullable, default=default)
