import pytest
import sys
import os
import uuid
from decimal import Decimal
from datetime import date
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.entities import Organization, User, Membership, Customer, Invoice, InvoiceLine
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_cross_tenant_isolation_invoices():
    """Acceptance Test: Tenant A cannot read Tenant B's invoices or records."""
    async with TestingSessionLocal() as db:
        # Create Tenant A
        t_a = Organization(name="Tenant A Fabrics", gstin="27AAAAA1111A1Z1")
        db.add(t_a)
        await db.flush()

        u_a = User(email="owner@tenanta.com", hashed_password=get_password_hash("pass"), full_name="User A")
        db.add(u_a)
        await db.flush()
        db.add(Membership(tenant_id=t_a.id, user_id=u_a.id, role="owner"))

        # Create Tenant B
        t_b = Organization(name="Tenant B Garments", gstin="24BBBBB2222B1Z2")
        db.add(t_b)
        await db.flush()

        u_b = User(email="owner@tenantb.com", hashed_password=get_password_hash("pass"), full_name="User B")
        db.add(u_b)
        await db.flush()
        db.add(Membership(tenant_id=t_b.id, user_id=u_b.id, role="owner"))

        # Create customer & invoice under Tenant B
        cust_b = Customer(tenant_id=t_b.id, name="Customer of B")
        db.add(cust_b)
        await db.flush()

        inv_b = Invoice(
            tenant_id=t_b.id,
            customer_id=cust_b.id,
            invoice_number="INV-TENANT-B-001",
            invoice_date=date(2026, 10, 1),
            due_date=date(2026, 10, 31),
            subtotal=Decimal("10000.0000"),
            cgst_amount=Decimal("250.0000"),
            sgst_amount=Decimal("250.0000"),
            igst_amount=Decimal("0.0000"),
            total_amount=Decimal("10500.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("10500.0000"),
            status="unpaid",
        )
        db.add(inv_b)
        await db.commit()

        token_a = create_access_token({
            "sub": str(u_a.id),
            "tenant_id": str(t_a.id),
            "role": "owner",
            "email": u_a.email,
        })

    # User A requests invoices
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/invoices", headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 200
        invoices = resp.json()
        # Tenant A must NOT see Tenant B's invoice
        assert len(invoices) == 0
        assert not any(inv["invoice_number"] == "INV-TENANT-B-001" for inv in invoices)
