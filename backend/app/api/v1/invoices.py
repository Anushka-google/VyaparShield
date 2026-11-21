import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Invoice
from app.schemas.finance import InvoiceCreate, InvoiceResponse, AgingBucketReport
from app.services.finance_service import FinanceService
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(prefix="/invoices", tags=["Invoices & Receivables"])


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """Creates an invoice with deterministic GST calculations and balanced ledger events."""
    invoice = await FinanceService.create_invoice(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        data=data,
    )
    # Ensure lines are loaded
    res = await db.execute(
        select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.id == invoice.id)
    )
    return res.scalar_one()


@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Lists invoices strictly scoped to caller's tenant."""
    query = select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.tenant_id == ctx.tenant_id)
    if status_filter:
        query = query.where(Invoice.status == status_filter)
    res = await db.execute(query.order_by(Invoice.invoice_date.desc()))
    return res.scalars().all()


@router.get("/aging", response_model=AgingBucketReport)
async def get_receivables_aging(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Returns deterministic accounts receivable aging breakdown across 4 statutory buckets."""
    return await FinanceService.get_receivables_aging(db=db, tenant_id=ctx.tenant_id)
