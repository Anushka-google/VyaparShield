import pytest
import io
import pymupdf
from decimal import Decimal
from datetime import date
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.entities import Organization, User, Membership, Customer, Invoice
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


def create_sample_gst_invoice_pdf(
    invoice_number: str = "INV-2026-901",
    invoice_date: str = "15/10/2026",
    seller_gstin: str = "27AAAAA1111A1Z1",
    buyer_gstin: str = "24BBBBB2222B1Z2",
    total_amount: str = "26250.00",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()

    text = f"""
    TAX INVOICE
    Seller GSTIN: {seller_gstin}
    Buyer GSTIN: {buyer_gstin}
    Invoice No: {invoice_number}
    Invoice Date: {invoice_date}
    Due Date: 15/11/2026

    Item Description: Premium Cotton Textiles
    HSN Code: 5208
    Quantity: 100.00
    Unit Rate: 250.00
    Taxable Subtotal: Rs. 25000.00
    CGST (2.5%): Rs. 625.00
    SGST (2.5%): Rs. 625.00
    Grand Total: Rs. {total_amount}
    """
    page.insert_text((50, 70), text, fontsize=12)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_document_upload_extraction_and_deduplication():
    """Acceptance Test: Upload PDF invoice, extract fields, validate GST, and prevent duplicate upload."""
    async with TestingSessionLocal() as db:
        org = Organization(name="Textile Mills Ltd", gstin="27AAAAA1111A1Z1")
        db.add(org)
        await db.flush()

        user = User(email="accountant@textiles.com", hashed_password=get_password_hash("pass"), full_name="Accountant")
        db.add(user)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=user.id, role="accountant"))

        cust = Customer(tenant_id=org.id, name="Retailer Shop", gstin="24BBBBB2222B1Z2")
        db.add(cust)
        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "accountant",
            "email": user.email,
        })
        cust_id = str(cust.id)

    pdf_bytes = create_sample_gst_invoice_pdf(invoice_number="INV-2026-901", total_amount="26250.00")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload Document
        files = {"file": ("invoice_901.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"document_type": "invoice"}
        resp = await client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
        assert resp.status_code == 201
        doc_data = resp.json()
        assert doc_data["file_name"] == "invoice_901.pdf"
        assert doc_data["status"] in ["extracted", "review_needed"]

        # Check extracted fields
        ext = doc_data["extracted_data"]
        assert ext["invoice_number"]["value"] == "INV-2026-901"
        assert ext["seller_gstin"]["value"] == "27AAAAA1111A1Z1"
        assert Decimal(ext["total_amount"]["value"]) == Decimal("26250.0000")

        doc_id = doc_data["id"]

        # 2. Cryptographic Deduplication Test: Uploading identical file must be rejected (409 Conflict)
        dup_files = {"file": ("invoice_901_duplicate.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        dup_resp = await client.post("/api/v1/documents/upload", files=dup_files, data=data, headers=headers)
        assert dup_resp.status_code == 409
        assert "identical file hash" in dup_resp.json()["detail"]

        # 3. Human Review & Promotion to Authoritative Invoice
        review_payload = {
            "customer_id": cust_id,
            "invoice_number": "INV-2026-901",
            "invoice_date": "2026-10-15",
            "due_date": "2026-11-15",
            "subtotal": "25000.0000",
            "total_amount": "26250.0000",
            "lines": [
                {
                    "description": "Premium Cotton Textiles",
                    "hsn_sac_code": "5208",
                    "quantity": "100.0000",
                    "unit_price": "250.0000",
                    "tax_rate": "5.00"
                }
            ],
            "is_interstate": False,
            "reviewer_notes": "Verified against physical PO."
        }
        review_resp = await client.post(f"/api/v1/documents/{doc_id}/review", json=review_payload, headers=headers)
        assert review_resp.status_code == 200
        inv_data = review_resp.json()
        assert inv_data["invoice_number"] == "INV-2026-901"
        assert inv_data["total_amount"] == "26250.0000"
        assert inv_data["outstanding_balance"] == "26250.0000"

        # 4. Verify Document status is now approved
        doc_get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert doc_get_resp.status_code == 200
        assert doc_get_resp.json()["status"] == "approved"
        assert doc_get_resp.json()["is_reviewed"] is True
