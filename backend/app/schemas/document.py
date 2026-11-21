import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExtractedField(BaseModel):
    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[List[float]] = None  # [x0, y0, x1, y1]
    page_number: int = 1


class ExtractedLineItem(BaseModel):
    description: str
    hsn_sac_code: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal
    confidence: float = 1.0


class ExtractedInvoiceData(BaseModel):
    invoice_number: Optional[ExtractedField] = None
    invoice_date: Optional[ExtractedField] = None
    due_date: Optional[ExtractedField] = None
    vendor_name: Optional[ExtractedField] = None
    customer_name: Optional[ExtractedField] = None
    seller_gstin: Optional[ExtractedField] = None
    buyer_gstin: Optional[ExtractedField] = None
    subtotal: Optional[ExtractedField] = None
    cgst_amount: Optional[ExtractedField] = None
    sgst_amount: Optional[ExtractedField] = None
    igst_amount: Optional[ExtractedField] = None
    total_amount: Optional[ExtractedField] = None
    lines: List[ExtractedLineItem] = []
    overall_confidence: float = 1.0


class DocumentValidationResult(BaseModel):
    is_valid: bool
    arithmetic_valid: bool
    gstin_valid: bool
    duplicate_detected: bool
    errors: List[str] = []
    warnings: List[str] = []


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    file_name: str
    file_type: str
    storage_uri: str
    file_hash: str
    document_type: str
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    is_reviewed: bool
    reviewer_id: Optional[uuid.UUID] = None
    corrections: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReviewRequest(BaseModel):
    customer_id: uuid.UUID
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    due_date: date
    subtotal: Decimal
    cgst_amount: Decimal = Decimal("0.0000")
    sgst_amount: Decimal = Decimal("0.0000")
    igst_amount: Decimal = Decimal("0.0000")
    total_amount: Decimal
    lines: List[Dict[str, Any]] = Field(..., min_length=1)
    is_interstate: bool = False
    reviewer_notes: Optional[str] = None
