import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Organization
from app.schemas.finance import TenantResponse, TenantUpdateRequest
from app.core.security import get_current_context, AuthenticatedContext, require_roles
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/tenants", tags=["Tenancy"])


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Retrieve the current authenticated tenant organization details."""
    res = await db.execute(select(Organization).where(Organization.id == ctx.tenant_id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant organization not found.")
    return org


@router.patch("/current", response_model=TenantResponse)
async def update_current_tenant(
    data: TenantUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin"])),
):
    """Update organization profile (Owner/Admin only)."""
    res = await db.execute(select(Organization).where(Organization.id == ctx.tenant_id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant organization not found.")

    if data.name is not None:
        org.name = data.name
    if data.gstin is not None:
        org.gstin = data.gstin
    if data.pan is not None:
        org.pan = data.pan

    await FinanceService.log_audit_event(
        db=db,
        event_name="TENANT_UPDATED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        details={"updated_fields": data.model_dump(exclude_unset=True)},
    )
    await db.commit()
    await db.refresh(org)
    return org
