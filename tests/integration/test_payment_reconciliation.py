import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.entities import Organization, User, Membership, Customer, EntityAlias, Invoice, InvoiceLine, Payment
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_reconciliation_exact_match_and_tds_detection():
    """
    Acceptance Test:
    1. Exact reference & amount matching auto-clears.
    2. Statutory TDS deduction (e.g. 2%) is detected and explained.
    3. Partial payments properly adjust balances without silently clearing.
    """
    async with TestingSessionLocal() as db:
        org = Organization(name="Recon Test MSME", gstin="27AAAAA1111A1Z1")
        db.add(org)
        await db.flush()

        user = User(email="recon@msme.com", hashed_password=get_password_hash("pass"), full_name="Recon Officer")
        db.add(user)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=user.id, role="accountant"))

        cust = Customer(tenant_id=org.id, name="Royal Fabrics Ltd", gstin="27BBBBB1111B1Z2")
        db.add(cust)
        await db.flush()

        alias = EntityAlias(
            tenant_id=org.id,
            entity_type="customer",
            entity_id=cust.id,
            alias_name="ROYAL FABRICS PUNE",
            confidence=Decimal("1.0000"),
        )
        db.add(alias)

        # Invoice 1: Exact Match candidate (Rs. 10,000)
        inv1 = Invoice(
            tenant_id=org.id,
            customer_id=cust.id,
            invoice_number="INV-2026-0010",
            invoice_date=date(2026, 10, 1),
            due_date=date(2026, 10, 31),
            subtotal=Decimal("10000.0000"),
            total_amount=Decimal("10000.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("10000.0000"),
            status="unpaid",
            lines=[
                InvoiceLine(
                    description="Yarn Spools",
                    quantity=Decimal("10.0000"),
                    unit_price=Decimal("1000.0000"),
                    tax_rate=Decimal("0.00"),
                    line_total=Decimal("10000.0000"),
                )
            ],
        )
        db.add(inv1)

        # Invoice 2: TDS Candidate (Rs. 50,000 invoice with 2% TDS = Rs. 49,000 net)
        inv2 = Invoice(
            tenant_id=org.id,
            customer_id=cust.id,
            invoice_number="INV-2026-0020",
            invoice_date=date(2026, 10, 5),
            due_date=date(2026, 11, 5),
            subtotal=Decimal("50000.0000"),
            total_amount=Decimal("50000.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("50000.0000"),
            status="unpaid",
            lines=[
                InvoiceLine(
                    description="Cotton Rolls",
                    quantity=Decimal("50.0000"),
                    unit_price=Decimal("1000.0000"),
                    tax_rate=Decimal("0.00"),
                    line_total=Decimal("50000.0000"),
                )
            ],
        )
        db.add(inv2)

        # Payment 1: Exact match with invoice reference in narration
        p1 = Payment(
            tenant_id=org.id,
            payment_reference="UPI1122334455",
            payment_date=date(2026, 10, 10),
            total_amount=Decimal("10000.0000"),
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=Decimal("10000.0000"),
            payment_mode="UPI",
            raw_narration="UPI/1122334455/PAYMENT FOR INV-2026-0010/ROYAL",
            status="unmatched",
        )
        db.add(p1)

        # Payment 2: 2% TDS Net payment of Rs. 49,000 for INV-2026-0020
        p2 = Payment(
            tenant_id=org.id,
            payment_reference="NEFT99887766",
            payment_date=date(2026, 10, 12),
            total_amount=Decimal("49000.0000"),
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=Decimal("49000.0000"),
            payment_mode="NEFT",
            raw_narration="NEFT-AXIS99887766-ROYAL FABRICS-INV-2026-0020",
            status="unmatched",
        )
        db.add(p2)

        # Payment 3: Ambiguous payment without reference
        p3 = Payment(
            tenant_id=org.id,
            payment_reference="UPI77777777",
            payment_date=date(2026, 10, 15),
            total_amount=Decimal("15000.0000"),
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=Decimal("15000.0000"),
            payment_mode="UPI",
            raw_narration="UPI/77777777/MISC TRANSFER FROM UNKNOWN",
            status="unmatched",
        )
        db.add(p3)

        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "accountant",
            "email": user.email,
        })
        p2_id = str(p2.id)
        inv2_id = str(inv2.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Run Automated Reconciliation
        run_resp = await client.post("/api/v1/reconciliation/run", headers=headers)
        assert run_resp.status_code == 200
        run_data = run_resp.json()

        # Payment 1 must be auto-matched
        assert run_data["auto_matched_count"] >= 1
        auto_inv_nums = [m["invoice_number"] for m in run_data["auto_matches"]]
        assert "INV-2026-0010" in auto_inv_nums

        # 2. Check Exception Queue: Ambiguous Payment 3 must NEVER be silently cleared
        exc_resp = await client.get("/api/v1/reconciliation/exceptions", headers=headers)
        assert exc_resp.status_code == 200
        exceptions = exc_resp.json()
        assert len(exceptions) >= 1
        exc_refs = [e["payment_reference"] for e in exceptions]
        assert "UPI77777777" in exc_refs

        # 3. Confirming an exception match with TDS via reviewer action
        confirm_payload = {
            "allocated_amount": "49000.0000",
            "tds_deducted": "1000.0000",
            "reviewer_notes": "Confirmed 2% TDS deducted as per Form 16A."
        }
        conf_resp = await client.post(
            f"/api/v1/reconciliation/allocations/{p2_id}/{inv2_id}/confirm",
            json=confirm_payload,
            headers=headers,
        )
        assert conf_resp.status_code == 200
        conf_data = conf_resp.json()
        assert Decimal(str(conf_data["allocated_amount"])) == Decimal("49000.0000")
        assert Decimal(str(conf_data["tds_deducted"])) == Decimal("1000.0000")
        assert conf_data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_reconciliation_alias_matching_and_partial_payment():
    """Acceptance Test: Counterparty alias resolution and partial payment handling."""
    async with TestingSessionLocal() as db:
        org = Organization(name="Kutch Handlooms", gstin="24BBBBB0000B1Z1")
        db.add(org)
        await db.flush()

        user = User(email="owner@kutch.com", hashed_password=get_password_hash("pass"), full_name="Kutch Owner")
        db.add(user)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=user.id, role="owner"))

        cust = Customer(tenant_id=org.id, name="Western Retailers", gstin="24WWWWW1111W1Z5")
        db.add(cust)
        await db.flush()

        alias = EntityAlias(
            tenant_id=org.id,
            entity_type="customer",
            entity_id=cust.id,
            alias_name="WESTERN RETAILERS AHMEDABAD",
            confidence=Decimal("1.0000"),
        )
        db.add(alias)

        # Invoice of Rs. 20,000
        inv = Invoice(
            tenant_id=org.id,
            customer_id=cust.id,
            invoice_number="KUTCH-INV-101",
            invoice_date=date(2026, 10, 1),
            due_date=date(2026, 10, 31),
            subtotal=Decimal("20000.0000"),
            total_amount=Decimal("20000.0000"),
            paid_amount=Decimal("0.0000"),
            outstanding_balance=Decimal("20000.0000"),
            status="unpaid",
            lines=[
                InvoiceLine(
                    description="Embroidered Shawls",
                    quantity=Decimal("10.0000"),
                    unit_price=Decimal("2000.0000"),
                    tax_rate=Decimal("0.00"),
                    line_total=Decimal("20000.0000"),
                )
            ],
        )
        db.add(inv)

        # Payment of Rs. 8,000 referencing KUTCH-INV-101 (partial payment)
        p_partial = Payment(
            tenant_id=org.id,
            payment_reference="UPIPARTIAL123",
            payment_date=date(2026, 10, 15),
            total_amount=Decimal("8000.0000"),
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=Decimal("8000.0000"),
            payment_mode="UPI",
            raw_narration="UPI/UPIPARTIAL123/PARTIAL PAYMENT FOR KUTCH-INV-101",
            status="unmatched",
        )
        db.add(p_partial)
        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "owner",
            "email": user.email,
        })
        inv_id = str(inv.id)
        p_partial_id = str(p_partial.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Run reconciliation: Partial payment should auto-match with high confidence
        res = await client.post("/api/v1/reconciliation/run", headers=headers)
        assert res.status_code == 200
        run_data = res.json()
        assert run_data["auto_matched_count"] >= 1

        # 2. Verify invoice balance is reduced from 20,000 to 12,000 and status is partially_paid
        inv_res = await client.get("/api/v1/invoices", headers=headers)
        assert inv_res.status_code == 200
        invoices = inv_res.json()
        assert Decimal(invoices[0]["outstanding_balance"]) == Decimal("12000.0000")
        assert Decimal(invoices[0]["paid_amount"]) == Decimal("8000.0000")
        assert invoices[0]["status"] == "partially_paid"

