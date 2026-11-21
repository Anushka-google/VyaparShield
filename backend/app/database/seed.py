import asyncio
import os
import sys
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.session import AsyncSessionLocal, engine, Base
from app.models.entities import (
    Organization,
    User,
    Membership,
    Customer,
    EntityAlias,
    Invoice,
    InvoiceLine,
    Payment,
    LedgerEvent,
    AuditEvent,
)
from app.core.security import get_password_hash


async def seed_data():
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        chk = await session.execute(select(Organization).where(Organization.name == "Acme Textiles MSME"))
        if chk.scalar_one_or_none():
            print("Database already contains seed data. Skipping.")
            return

        print("Seeding Tenant 1: Acme Textiles MSME...")
        org1 = Organization(
            name="Acme Textiles MSME",
            gstin="27AAAAA0000A1Z5",
            pan="AAAAA0000A",
            currency="INR",
        )
        session.add(org1)
        await session.flush()

        user1 = User(
            email="owner@acmetextiles.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Rajesh Sharma",
            is_active=True,
        )
        session.add(user1)
        await session.flush()

        mem1 = Membership(
            tenant_id=org1.id,
            user_id=user1.id,
            role="owner",
        )
        session.add(mem1)

        print("Seeding Tenant 2 (For Cross-Tenant Isolation Tests): Bhavani Crafts MSME...")
        org2 = Organization(
            name="Bhavani Crafts MSME",
            gstin="24BBBBB9999B1Z8",
            pan="BBBBB9999B",
            currency="INR",
        )
        session.add(org2)
        await session.flush()

        user2 = User(
            email="owner@bhavanicrafts.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Bhavani Patel",
            is_active=True,
        )
        session.add(user2)
        await session.flush()

        mem2 = Membership(
            tenant_id=org2.id,
            user_id=user2.id,
            role="owner",
        )
        session.add(mem2)

        # Seed Customers for Tenant 1
        c1 = Customer(
            tenant_id=org1.id,
            name="Bharat Garments Ltd",
            gstin="27BBBBB1111B1Z2",
            email="billing@bharatgarments.in",
            phone="+919820012345",
            credit_period_days=30,
        )
        session.add(c1)
        await session.flush()

        # Seed Alias for Customer 1
        alias1 = EntityAlias(
            tenant_id=org1.id,
            entity_type="customer",
            entity_id=c1.id,
            alias_name="BHARAT GARMENTS MUMBAI",
            confidence=Decimal("1.0000"),
        )
        session.add(alias1)

        # Seed Invoices for Tenant 1
        inv1 = Invoice(
            tenant_id=org1.id,
            customer_id=c1.id,
            invoice_number="INV-2026-001",
            invoice_date=date(2026, 10, 1),
            due_date=date(2026, 10, 31),
            subtotal=Decimal("25000.0000"),
            cgst_amount=Decimal("625.0000"),
            sgst_amount=Decimal("625.0000"),
            igst_amount=Decimal("0.0000"),
            total_amount=Decimal("26250.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("26250.0000"),
            status="unpaid",
            lines=[
                InvoiceLine(
                    description="Combed Cotton Yarns 100kg",
                    hsn_sac_code="5205",
                    quantity=Decimal("100.0000"),
                    unit_price=Decimal("250.0000"),
                    tax_rate=Decimal("5.00"),
                    line_total=Decimal("26250.0000"),
                )
            ],
        )
        session.add(inv1)

        # Seed Invoices for Tenant 2 (Isolation Verification)
        c2 = Customer(
            tenant_id=org2.id,
            name="Kutch Handicrafts",
            gstin="24KKKKK8888K1Z1",
            credit_period_days=30,
        )
        session.add(c2)
        await session.flush()

        inv2 = Invoice(
            tenant_id=org2.id,
            customer_id=c2.id,
            invoice_number="BHAVANI-INV-001",
            invoice_date=date(2026, 10, 5),
            due_date=date(2026, 11, 5),
            subtotal=Decimal("50000.0000"),
            cgst_amount=Decimal("1250.0000"),
            sgst_amount=Decimal("1250.0000"),
            igst_amount=Decimal("0.0000"),
            total_amount=Decimal("52500.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("52500.0000"),
            status="unpaid",
            lines=[
                InvoiceLine(
                    description="Handmade Kutch Embroidery 50pcs",
                    quantity=Decimal("50.0000"),
                    unit_price=Decimal("1000.0000"),
                    tax_rate=Decimal("5.00"),
                    line_total=Decimal("52500.0000"),
                )
            ],
        )
        session.add(inv2)

        await session.commit()
        print("Database successfully seeded with realistic Indian MSME multi-tenant data!")


if __name__ == "__main__":
    asyncio.run(seed_data())
