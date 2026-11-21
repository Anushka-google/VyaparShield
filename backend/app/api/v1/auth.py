import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Organization, User, Membership
from app.schemas.finance import TenantRegisterRequest, LoginRequest, TokenResponse
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_context,
    AuthenticatedContext,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/auth", tags=["Authentication & Tenancy"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    data: TenantRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check if user email already exists
    user_chk = await db.execute(select(User).where(User.email == data.email))
    if user_chk.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    # Create Organization (Tenant)
    org = Organization(
        name=data.organization_name,
        gstin=data.gstin,
        pan=data.pan,
        currency=data.currency,
    )
    db.add(org)
    await db.flush()

    # Create User
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Assign 'owner' role membership
    membership = Membership(
        tenant_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)

    await FinanceService.log_audit_event(
        db=db,
        event_name="TENANT_REGISTERED",
        tenant_id=org.id,
        user_id=user.id,
        details={"org_name": org.name, "email": user.email, "role": "owner"},
    )
    await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(org.id),
        "role": "owner",
        "email": user.email,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        tenant_id=org.id,
        role="owner",
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_res = await db.execute(select(User).where(User.email == data.email))
    user = user_res.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    # Get primary membership
    mem_res = await db.execute(select(Membership).where(Membership.user_id == user.id))
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any active organization.",
        )

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(membership.tenant_id),
        "role": membership.role,
        "email": user.email,
    })

    await FinanceService.log_audit_event(
        db=db,
        event_name="USER_LOGGED_IN",
        tenant_id=membership.tenant_id,
        user_id=user.id,
        details={"email": user.email},
    )
    await db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        email=user.email,
    )


@router.get("/me")
async def get_current_profile(ctx: AuthenticatedContext = Depends(get_current_context)):
    return {
        "user_id": ctx.user_id,
        "tenant_id": ctx.tenant_id,
        "role": ctx.role,
        "email": ctx.email,
    }
