import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import User, Membership
from app.schemas.finance import UserResponse, UserInviteRequest
from app.core.security import get_current_context, AuthenticatedContext, require_roles, get_password_hash
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/users", tags=["Users & Access"])


@router.get("", response_model=List[UserResponse])
async def list_tenant_users(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """List all users/members belonging to the authenticated tenant."""
    query = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == ctx.tenant_id)
        .order_by(User.created_at.asc())
    )
    result = await db.execute(query)
    users_with_roles = []
    for user, role in result.all():
        users_with_roles.append(
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=role,
                is_active=user.is_active,
                created_at=user.created_at,
            )
        )
    return users_with_roles


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: UserInviteRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin"])),
):
    """Invite or add a user to the organization (Owner/Admin only)."""
    # Check if user already exists
    user_res = await db.execute(select(User).where(User.email == data.email))
    user = user_res.scalar_one_or_none()

    if not user:
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            is_active=True,
        )
        db.add(user)
        await db.flush()

    # Check if user is already a member of this tenant
    mem_res = await db.execute(
        select(Membership).where(Membership.tenant_id == ctx.tenant_id, Membership.user_id == user.id)
    )
    if mem_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        )

    membership = Membership(
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        role=data.role,
    )
    db.add(membership)

    await FinanceService.log_audit_event(
        db=db,
        event_name="USER_INVITED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        details={"invited_user_id": str(user.id), "email": user.email, "role": data.role},
    )
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=data.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
