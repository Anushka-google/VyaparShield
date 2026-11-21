import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import AuditEvent
from app.schemas.finance import AuditEventResponse
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(prefix="/audit", tags=["Audit & Security Logs"])


@router.get("", response_model=List[AuditEventResponse])
async def list_audit_events(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "reviewer", "admin"])),
):
    """Retrieves immutable audit trail for the organization."""
    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == ctx.tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    return res.scalars().all()
