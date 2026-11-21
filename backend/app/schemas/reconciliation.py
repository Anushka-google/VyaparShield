import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class NormalizedNarration(BaseModel):
    raw_narration: str
    payment_mode: str  # UPI, NEFT, IMPS, RTGS, CHEQUE
    reference_number: Optional[str] = None
    utr_number: Optional[str] = None
    counterparty_name: Optional[str] = None
    invoice_references: List[str] = []


class CandidateMatch(BaseModel):
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    payment_reference: Optional[str] = None
    payment_date: date
    invoice_date: date
    invoice_total: Decimal
    invoice_outstanding: Decimal
    payment_total: Decimal
    payment_unallocated: Decimal
    allocated_amount: Decimal
    tds_deducted: Decimal = Decimal("0.0000")
    discount_allowed: Decimal = Decimal("0.0000")
    bank_charges: Decimal = Decimal("0.0000")
    round_off_difference: Decimal = Decimal("0.0000")
    residual_amount: Decimal = Decimal("0.0000")
    residual_reason: Optional[str] = None
    match_type: str  # exact_reference, tds_aware_match, alias_match, amount_only, partial_payment
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    auto_matched: bool = False


class ReconciliationExceptionItem(BaseModel):
    payment_id: uuid.UUID
    payment_reference: Optional[str] = None
    payment_date: date
    payment_total: Decimal
    payment_unallocated: Decimal
    raw_narration: str
    candidates: List[CandidateMatch] = []
    reason: str  # ambiguous_candidates, unmatched_residual, unknown_counterparty, duplicate_candidate


class ReconciliationRunResponse(BaseModel):
    unmatched_payments_count: int
    unpaid_invoices_count: int
    auto_matched_count: int
    exceptions_count: int
    auto_matches: List[CandidateMatch] = []
    exceptions: List[ReconciliationExceptionItem] = []


class AllocationConfirmRequest(BaseModel):
    allocated_amount: Optional[Decimal] = None
    tds_deducted: Optional[Decimal] = None
    discount_allowed: Optional[Decimal] = None
    bank_charges: Optional[Decimal] = None
    round_off_difference: Optional[Decimal] = None
    reviewer_notes: Optional[str] = None


class StatementTransactionItem(BaseModel):
    transaction_date: date
    narration: str
    amount: Decimal
    payment_mode: Optional[str] = "UPI"
    reference_number: Optional[str] = None
