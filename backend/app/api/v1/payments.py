import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Payment
from app.schemas.finance import (
    PaymentCreate,
    PaymentResponse,
    PaymentAllocationRequest,
    PaymentAllocationResponse,
)
from app.services.finance_service import FinanceService
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(prefix="/payments", tags=["Payments & Allocations"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """Records a bank payment / transaction entry."""
    return await FinanceService.record_payment(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        data=data,
    )


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Lists payments scoped strictly to caller's tenant."""
    res = await db.execute(
        select(Payment).where(Payment.tenant_id == ctx.tenant_id).order_by(Payment.payment_date.desc())
    )
    return res.scalars().all()


@router.post("/{payment_id}/allocate", response_model=PaymentAllocationResponse)
async def allocate_payment(
    payment_id: uuid.UUID,
    data: PaymentAllocationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """
    Applies payment funds to an invoice.
    Enforces conservation of funds (allocated <= unallocated) and checks idempotency.
    """
    return await FinanceService.allocate_payment(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        payment_id=payment_id,
        data=data,
    )
