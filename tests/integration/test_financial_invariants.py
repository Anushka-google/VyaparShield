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
from app.models.entities import Organization, User, Membership, Customer, Invoice, Payment, AuditEvent
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_nonexistent_customer_rejected():
    """Acceptance Test: An invoice cannot reference a nonexistent customer."""
    async with TestingSessionLocal() as db:
        org = Organization(name="Test Org", gstin="27AAAAA1111A1Z1")
        db.add(org)
        await db.flush()

        user = User(email="user@test.com", hashed_password=get_password_hash("pass"), full_name="User")
        db.add(user)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=user.id, role="owner"))
        await db.commit()

        token = create_access_token({"sub": str(user.id), "tenant_id": str(org.id), "role": "owner", "email": user.email})

    random_customer_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "customer_id": random_customer_id,
            "invoice_number": "INV-FAIL-001",
            "invoice_date": "2026-10-01",
            "due_date": "2026-10-31",
            "lines": [
                {
                    "description": "Item 1",
                    "quantity": "2.0000",
                    "unit_price": "100.0000",
                    "tax_rate": "18.00"
                }
            ]
        }
        resp = await client.post("/api/v1/invoices", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404
        assert "does not exist in this organization" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_decimal_safe_invoice_and_double_payment_prevention():
    """
    Acceptance Test:
    1. Financial calculations use decimal-safe arithmetic.
    2. A repeated request cannot apply the same payment twice.
    3. Important financial changes leave an auditable trail.
    """
    async with TestingSessionLocal() as db:
        org = Organization(name="Acme MSME", gstin="27AAAAA1111A1Z1")
        db.add(org)
        await db.flush()

        user = User(email="owner@acme.com", hashed_password=get_password_hash("pass"), full_name="Owner")
        db.add(user)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=user.id, role="owner"))

        cust = Customer(tenant_id=org.id, name="Loyal Client")
        db.add(cust)
        await db.commit()

        token = create_access_token({"sub": str(user.id), "tenant_id": str(org.id), "role": "owner", "email": user.email})
        cust_id = str(cust.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Invoice with ₹10,000 subtotal and 5% GST (Intra-state: 2.5% CGST + 2.5% SGST)
        inv_payload = {
            "customer_id": cust_id,
            "invoice_number": "INV-2026-0099",
            "invoice_date": "2026-10-01",
            "due_date": "2026-10-31",
            "lines": [
                {
                    "description": "Textile Bales",
                    "quantity": "10.0000",
                    "unit_price": "1000.0000",
                    "tax_rate": "5.00"
                }
            ],
            "is_interstate": False
        }
        inv_resp = await client.post("/api/v1/invoices", json=inv_payload, headers=headers)
        assert inv_resp.status_code == 201
        inv_data = inv_resp.json()

        # Decimal safety assertion: 10 * 1000 = 10000; Tax = 500; CGST = 250, SGST = 250, Total = 10500
        assert Decimal(str(inv_data["subtotal"])) == Decimal("10000.0000")
        assert Decimal(str(inv_data["cgst_amount"])) == Decimal("250.0000")
        assert Decimal(str(inv_data["sgst_amount"])) == Decimal("250.0000")
        assert Decimal(str(inv_data["total_amount"])) == Decimal("10500.0000")
        assert Decimal(str(inv_data["outstanding_balance"])) == Decimal("10500.0000")

        invoice_id = inv_data["id"]

        # 2. Record Payment of ₹10,500
        pay_payload = {
            "payment_reference": "UPI998877665544",
            "payment_date": "2026-10-15",
            "total_amount": "10500.0000",
            "payment_mode": "UPI",
            "raw_narration": "UPI/998877665544/PAYMENT FOR INV-2026-0099"
        }
        pay_resp = await client.post("/api/v1/payments", json=pay_payload, headers=headers)
        assert pay_resp.status_code == 201
        pay_data = pay_resp.json()
        payment_id = pay_data["id"]

        # 3. First Allocation: Settle the invoice
        alloc_payload = {
            "invoice_id": invoice_id,
            "allocated_amount": "10500.0000",
            "tds_deducted": "0.0000",
            "discount_allowed": "0.0000",
            "round_off_difference": "0.0000"
        }
        alloc_resp = await client.post(f"/api/v1/payments/{payment_id}/allocate", json=alloc_payload, headers=headers)
        assert alloc_resp.status_code == 200
        alloc_data = alloc_resp.json()
        assert alloc_data["status"] == "confirmed"

        # Verify invoice is now paid
        invoices_list = (await client.get("/api/v1/invoices", headers=headers)).json()
        assert invoices_list[0]["outstanding_balance"] == "0.0000"
        assert invoices_list[0]["status"] == "paid"

        # 4. Invariant Assertion: Repeated request cannot apply the same payment twice!
        repeat_resp = await client.post(f"/api/v1/payments/{payment_id}/allocate", json=alloc_payload, headers=headers)
        assert repeat_resp.status_code == 422
        assert "exceeds payment unallocated balance" in repeat_resp.json()["detail"]

        # 5. Audit Trail Assertion: Verify audit events recorded
        audit_resp = await client.get("/api/v1/audit", headers=headers)
        assert audit_resp.status_code == 200
        events = audit_resp.json()
        event_names = [e["event_name"] for e in events]
        assert "INVOICE_CREATED" in event_names
        assert "PAYMENT_RECEIVED" in event_names
        assert "PAYMENT_ALLOCATED" in event_names
