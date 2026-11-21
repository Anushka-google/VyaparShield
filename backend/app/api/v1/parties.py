import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Customer, Vendor, EntityAlias
from app.schemas.finance import (
    CustomerCreate,
    CustomerResponse,
    VendorCreate,
    VendorResponse,
    EntityAliasCreate,
    EntityAliasResponse,
)
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(tags=["Master Parties & Aliases"])


# --- Customers ---

@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    customer = Customer(
        tenant_id=ctx.tenant_id,
        name=data.name,
        gstin=data.gstin,
        email=data.email,
        phone=data.phone,
        credit_period_days=data.credit_period_days,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    res = await db.execute(select(Customer).where(Customer.tenant_id == ctx.tenant_id))
    return res.scalars().all()


# --- Vendors ---

@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    data: VendorCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    vendor = Vendor(
        tenant_id=ctx.tenant_id,
        name=data.name,
        gstin=data.gstin,
        bank_account_no=data.bank_account_no,
        ifsc_code=data.ifsc_code,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    res = await db.execute(select(Vendor).where(Vendor.tenant_id == ctx.tenant_id))
    return res.scalars().all()


# --- Counterparty Aliases ---

@router.post("/aliases", response_model=EntityAliasResponse, status_code=status.HTTP_201_CREATED)
async def create_alias(
    data: EntityAliasCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    alias = EntityAlias(
        tenant_id=ctx.tenant_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        alias_name=data.alias_name.strip().upper(),
        confidence=data.confidence,
    )
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    return alias
