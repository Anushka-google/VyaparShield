import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.reconciliation import (
    ReconciliationRunResponse,
    ReconciliationExceptionItem,
    AllocationConfirmRequest,
    NormalizedNarration,
)
from app.schemas.finance import PaymentAllocationResponse
from app.services.reconciliation_service import ReconciliationService
from app.services.narration_service import NarrationService
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(prefix="/reconciliation", tags=["Payment Reconciliation Engine"])


@router.post("/run", response_model=ReconciliationRunResponse)
async def run_reconciliation(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """
    Executes automated reconciliation between unallocated payments and unpaid invoices.
    Applies high-confidence deterministic matches directly, and puts all ambiguous or
    residual candidate matches into the human exception queue (never silently cleared).
    """
    return await ReconciliationService.run_reconciliation(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
    )


@router.get("/exceptions", response_model=List[ReconciliationExceptionItem])
async def list_reconciliation_exceptions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """
    Retrieves all payments currently in the human exception queue with candidate
    invoices, match confidence scores, and residual explanations (TDS, discounts).
    """
    return await ReconciliationService.get_exceptions(
        db=db,
        tenant_id=ctx.tenant_id,
    )


@router.post("/allocations/{payment_id}/{invoice_id}/confirm", response_model=PaymentAllocationResponse)
async def confirm_exception_allocation(
    payment_id: uuid.UUID,
    invoice_id: uuid.UUID,
    req: AllocationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """
    Human Review Action: Confirm an allocation candidate from the exception queue,
    specifying or accepting suggested TDS, cash discounts, or round-off differences.
    """
    return await ReconciliationService.confirm_allocation(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        payment_id=payment_id,
        invoice_id=invoice_id,
        req=req,
    )


@router.post("/normalize-narration", response_model=NormalizedNarration)
async def normalize_narration(
    narration: str = Query(..., description="Raw bank narration string"),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Inspect and test Indian bank narration normalization (UPI, NEFT, IMPS, RTGS)."""
    return NarrationService.normalize(narration)
