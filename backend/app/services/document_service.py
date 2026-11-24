import os
import io
import re
import uuid
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
import pymupdf
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document, Invoice, InvoiceLine, Customer
from app.schemas.document import (
    ExtractedField,
    ExtractedLineItem,
    ExtractedInvoiceData,
    DocumentValidationResult,
    DocumentReviewRequest,
)
from app.database.session import round_currency
from app.services.finance_service import FinanceService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentService:
    """
    Document Intelligence Service for Indian MSME Invoices and Financial Documents.
    Performs PDF layout extraction, GST & arithmetic validation, and review promotion.
    """

    GSTIN_REGEX = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b")
    INVOICE_NUM_REGEX = re.compile(r"\b(?:invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*|inv\s*[:#\-]\s*)([A-Za-z0-9\-_/]+)", re.IGNORECASE)
    DATE_REGEX = re.compile(r"\b([0-3]?[0-9][/\-.][0-1]?[0-9][/\-.](?:20)?[0-9]{2})\b")
    GRAND_TOTAL_REGEX = re.compile(r"(?:grand\s*total|invoice\s*total|total\s*payable|net\s*payable)[:\s]*(?:\u20b9|rs\.?|inr)?\s*([0-9,]+\.?[0-9]{0,4})", re.IGNORECASE)
    TOTAL_AMOUNT_REGEX = re.compile(r"(?<!sub)\b(?:total|amount)[:\s]*(?:\u20b9|rs\.?|inr)?\s*([0-9,]+\.?[0-9]{0,4})", re.IGNORECASE)
    SUBTOTAL_REGEX = re.compile(r"(?:sub\s*total|taxable\s*(?:subtotal|amount|value)?)[:\s]*(?:\u20b9|rs\.?|inr)?\s*([0-9,]+\.?[0-9]{0,4})", re.IGNORECASE)

    @classmethod
    async def upload_document(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        file: UploadFile,
        document_type: str = "invoice",
        storage_base_dir: str = "./storage_data",
    ) -> Document:
        contents = await file.read()
        if not contents or len(contents) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        # Compute SHA-256 for cryptographic deduplication
        file_hash = hashlib.sha256(contents).hexdigest()

        # Check deduplication within tenant
        chk = await db.execute(
            select(Document).where(Document.tenant_id == tenant_id, Document.file_hash == file_hash)
        )
        if chk.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A duplicate document with the identical file hash has already been uploaded for this organization.",
            )

        # Save to local storage
        tenant_dir = os.path.join(storage_base_dir, str(tenant_id))
        os.makedirs(tenant_dir, exist_ok=True)
        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        storage_uri = os.path.join(tenant_dir, safe_filename)

        with open(storage_uri, "wb") as f:
            f.write(contents)

        # Create Document record
        doc = Document(
            tenant_id=tenant_id,
            file_name=file.filename or "unknown.pdf",
            file_type=file.content_type or "application/pdf",
            storage_uri=storage_uri,
            file_hash=file_hash,
            document_type=document_type,
            status="uploaded",
        )
        db.add(doc)
        await db.flush()

        # Perform extraction if PDF
        if doc.file_name.lower().endswith(".pdf") or "pdf" in doc.file_type.lower():
            extracted, validation = await cls.extract_and_validate_pdf(
                db=db,
                tenant_id=tenant_id,
                file_bytes=contents,
            )
            doc.extracted_data = extracted.model_dump(mode="json")
            doc.validation_results = validation.model_dump(mode="json")
            doc.status = "extracted" if validation.is_valid else "review_needed"

        await FinanceService.log_audit_event(
            db=db,
            event_name="DOCUMENT_UPLOADED",
            tenant_id=tenant_id,
            user_id=user_id,
            details={
                "document_id": str(doc.id),
                "file_name": doc.file_name,
                "file_hash": doc.file_hash,
                "status": doc.status,
            },
        )
        await db.commit()
        await db.refresh(doc)
        return doc

    @classmethod
    async def extract_and_validate_pdf(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_bytes: bytes,
    ) -> Tuple[ExtractedInvoiceData, DocumentValidationResult]:
        doc_pdf = pymupdf.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        extracted = ExtractedInvoiceData()
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Text and Block Extraction
        for page_idx in range(len(doc_pdf)):
            page = doc_pdf[page_idx]
            full_text += page.get_text() + "\n"

            # Search invoice number
            if not extracted.invoice_number:
                m_inv = cls.INVOICE_NUM_REGEX.search(page.get_text())
                if m_inv:
                    val = m_inv.group(1).strip()
                    rects = page.search_for(val)
                    bbox = [rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1] if rects else None
                    extracted.invoice_number = ExtractedField(value=val, confidence=0.95, bounding_box=bbox, page_number=page_idx+1)

            # Search GSTIN
            gstins = cls.GSTIN_REGEX.findall(page.get_text())
            if gstins and not extracted.seller_gstin:
                val = gstins[0]
                rects = page.search_for(val)
                bbox = [rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1] if rects else None
                extracted.seller_gstin = ExtractedField(value=val, confidence=0.98, bounding_box=bbox, page_number=page_idx+1)
            if len(gstins) > 1 and not extracted.buyer_gstin:
                val = gstins[1]
                rects = page.search_for(val)
                bbox = [rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1] if rects else None
                extracted.buyer_gstin = ExtractedField(value=val, confidence=0.98, bounding_box=bbox, page_number=page_idx+1)

            # Search Total Amount (prioritizing Grand Total)
            if not extracted.total_amount:
                m_grand = cls.GRAND_TOTAL_REGEX.search(page.get_text())
                m_total = m_grand or cls.TOTAL_AMOUNT_REGEX.search(page.get_text())
                if m_total:
                    try:
                        amt_str = m_total.group(1).replace(",", "").strip()
                        val = Decimal(amt_str)
                        rects = page.search_for(m_total.group(0).strip())
                        bbox = [rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1] if rects else None
                        conf = 0.98 if m_grand else 0.90
                        extracted.total_amount = ExtractedField(value=str(round_currency(val)), confidence=conf, bounding_box=bbox, page_number=page_idx+1)
                    except (InvalidOperation, ValueError):
                        pass

            # Search Subtotal
            if not extracted.subtotal:
                m_sub = cls.SUBTOTAL_REGEX.search(page.get_text())
                if m_sub:
                    try:
                        sub_val = Decimal(m_sub.group(1).replace(",", "").strip())
                        extracted.subtotal = ExtractedField(value=str(round_currency(sub_val)), confidence=0.92, page_number=page_idx+1)
                    except (InvalidOperation, ValueError):
                        pass

        # Fallback regex search on full_text if fields not found
        if not extracted.invoice_number:
            inv_fallback = re.search(r"(?:INV[-_][A-Za-z0-9\-]+)", full_text, re.IGNORECASE)
            if inv_fallback:
                extracted.invoice_number = ExtractedField(value=inv_fallback.group(0), confidence=0.85)

        # Dates extraction
        dates = cls.DATE_REGEX.findall(full_text)
        if dates:
            extracted.invoice_date = ExtractedField(value=cls._parse_date(dates[0]), confidence=0.90)
        if len(dates) > 1:
            extracted.due_date = ExtractedField(value=cls._parse_date(dates[1]), confidence=0.85)
        else:
            extracted.due_date = ExtractedField(value=extracted.invoice_date.value if extracted.invoice_date else str(date.today()), confidence=0.70)

        # 2. Validation & Business Rules
        arithmetic_valid = True
        gstin_valid = True
        duplicate_detected = False

        if extracted.invoice_number:
            # Check duplicate invoice in organization
            dup_chk = await db.execute(
                select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.invoice_number == extracted.invoice_number.value)
            )
            if dup_chk.scalar_one_or_none():
                duplicate_detected = True
                errors.append(f"Invoice number '{extracted.invoice_number.value}' already exists in this organization.")

        if extracted.seller_gstin and not cls.validate_gstin_checksum(extracted.seller_gstin.value):
            gstin_valid = False
            warnings.append(f"Seller GSTIN '{extracted.seller_gstin.value}' failed checksum format validation.")

        if not extracted.total_amount:
            arithmetic_valid = False
            errors.append("Could not reliably extract total amount from invoice.")

        is_valid = (len(errors) == 0 and not duplicate_detected)

        validation = DocumentValidationResult(
            is_valid=is_valid,
            arithmetic_valid=arithmetic_valid,
            gstin_valid=gstin_valid,
            duplicate_detected=duplicate_detected,
            errors=errors,
            warnings=warnings,
        )

        return extracted, validation

    @classmethod
    async def review_and_approve(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        review: DocumentReviewRequest,
    ) -> Invoice:
        # Fetch document
        doc_res = await db.execute(
            select(Document).where(Document.tenant_id == tenant_id, Document.id == document_id)
        )
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        # Check customer exists
        cust_res = await db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == review.customer_id)
        )
        customer = cust_res.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced customer does not exist.")

        # Check duplicate invoice number
        dup = await db.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.invoice_number == review.invoice_number)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An invoice with number '{review.invoice_number}' already exists.",
            )

        # Calculate authoritative line items
        invoice_lines: List[InvoiceLine] = []
        calc_subtotal = Decimal("0.0000")
        calc_tax = Decimal("0.0000")

        for l_data in review.lines:
            qty = Decimal(str(l_data["quantity"]))
            rate = Decimal(str(l_data["unit_price"]))
            tax_rate = Decimal(str(l_data["tax_rate"]))
            line_sub = round_currency(qty * rate)
            line_tax = round_currency(line_sub * (tax_rate / Decimal("100.00")))
            line_total = line_sub + line_tax

            calc_subtotal += line_sub
            calc_tax += line_tax

            invoice_lines.append(
                InvoiceLine(
                    description=l_data.get("description", "Item"),
                    hsn_sac_code=l_data.get("hsn_sac_code"),
                    quantity=qty,
                    unit_price=rate,
                    tax_rate=tax_rate,
                    line_total=line_total,
                )
            )

        if review.is_interstate:
            igst = calc_tax
            cgst = Decimal("0.0000")
            sgst = Decimal("0.0000")
        else:
            igst = Decimal("0.0000")
            cgst = round_currency(calc_tax / Decimal("2.0000"))
            sgst = round_currency(calc_tax / Decimal("2.0000"))

        total_amount = calc_subtotal + cgst + sgst + igst

        # Create authoritative Invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            customer_id=review.customer_id,
            document_id=doc.id,
            invoice_number=review.invoice_number,
            invoice_date=review.invoice_date,
            due_date=review.due_date,
            subtotal=calc_subtotal,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            total_amount=total_amount,
            paid_amount=Decimal("0.0000"),
            outstanding_balance=total_amount,
            status="unpaid",
            lines=invoice_lines,
        )
        db.add(invoice)

        # Update Document state
        doc.is_reviewed = True
        doc.reviewer_id = user_id
        doc.status = "approved"
        doc.corrections = {
            "approved_by": str(user_id),
            "approved_at": utc_now().isoformat(),
            "notes": review.reviewer_notes,
            "final_invoice_number": review.invoice_number,
            "final_total": str(total_amount),
        }

        await FinanceService.log_audit_event(
            db=db,
            event_name="DOCUMENT_APPROVED",
            tenant_id=tenant_id,
            user_id=user_id,
            details={
                "document_id": str(doc.id),
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "total_amount": str(total_amount),
            },
        )
        await db.commit()
        res = await db.execute(
            select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.id == invoice.id)
        )
        return res.scalar_one()

    @staticmethod
    def _parse_date(raw_date: str) -> str:
        clean = re.sub(r"[/\-.]", "-", raw_date).strip()
        parts = clean.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            elif len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return str(date.today())

    @staticmethod
    def validate_gstin_checksum(gstin: str) -> bool:
        if not gstin or len(gstin) != 15:
            return False
        return bool(re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gstin))
