import uuid
import re
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Payment, Invoice, PaymentAllocation, Customer, EntityAlias, LedgerEvent
from app.schemas.reconciliation import (
    CandidateMatch,
    ReconciliationExceptionItem,
    ReconciliationRunResponse,
    AllocationConfirmRequest,
)
from app.schemas.finance import PaymentAllocationRequest
from app.services.narration_service import NarrationService
from app.services.finance_service import FinanceService
from app.database.session import round_currency


class ReconciliationService:
    """
    Automated Multi-Tier Payment Reconciliation Engine for Indian MSMEs.
    Enforces deterministic matching first, TDS detection, counterparty alias normalization,
    and reasoned human exception queues with NO silent clearing.
    """

    TDS_RATES = [Decimal("0.0100"), Decimal("0.0200"), Decimal("0.0500"), Decimal("0.1000")]
    ROUND_OFF_TOLERANCE = Decimal("5.0000")

    @classmethod
    async def run_reconciliation(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ReconciliationRunResponse:
        # 1. Fetch all unmatched/partially_matched payments
        pay_res = await db.execute(
            select(Payment).where(
                Payment.tenant_id == tenant_id,
                Payment.status.in_(["unmatched", "partially_matched"]),
                Payment.unallocated_amount > Decimal("0.0000"),
            ).order_by(Payment.payment_date.asc())
        )
        unmatched_payments = pay_res.scalars().all()

        # 2. Fetch all unpaid/partially_paid invoices
        inv_res = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(["unpaid", "partially_paid"]),
                Invoice.outstanding_balance > Decimal("0.0000"),
            ).order_by(Invoice.invoice_date.asc())
        )
        unpaid_invoices = inv_res.scalars().all()

        auto_matches: List[CandidateMatch] = []
        exceptions: List[ReconciliationExceptionItem] = []

        # Track invoice remaining balances in-memory during this run
        invoice_pool = {inv.id: inv for inv in unpaid_invoices}

        for payment in unmatched_payments:
            norm = NarrationService.normalize(payment.raw_narration)
            candidates = await cls._find_candidates(
                db=db,
                tenant_id=tenant_id,
                payment=payment,
                norm=norm,
                invoices=list(invoice_pool.values()),
            )

            if len(candidates) == 1 and candidates[0].confidence_score >= 0.95:
                top_match = candidates[0]
                top_match.auto_matched = True

                # Apply allocation immediately
                alloc_req = PaymentAllocationRequest(
                    invoice_id=top_match.invoice_id,
                    allocated_amount=top_match.allocated_amount,
                    tds_deducted=top_match.tds_deducted,
                    discount_allowed=top_match.discount_allowed,
                    bank_charges=top_match.bank_charges,
                    round_off_difference=top_match.round_off_difference,
                )
                await FinanceService.allocate_payment(
                    db=db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payment_id=payment.id,
                    data=alloc_req,
                )
                auto_matches.append(top_match)

                # Update invoice in-memory pool
                inv = invoice_pool.get(top_match.invoice_id)
                if inv and inv.outstanding_balance <= Decimal("0.0000"):
                    del invoice_pool[top_match.invoice_id]
            else:
                reason = "ambiguous_candidates" if len(candidates) > 1 else (
                    "unmatched_residual" if len(candidates) == 1 else "unknown_counterparty"
                )
                exceptions.append(
                    ReconciliationExceptionItem(
                        payment_id=payment.id,
                        payment_reference=payment.payment_reference,
                        payment_date=payment.payment_date,
                        payment_total=payment.total_amount,
                        payment_unallocated=payment.unallocated_amount,
                        raw_narration=payment.raw_narration,
                        candidates=candidates,
                        reason=reason,
                    )
                )

        return ReconciliationRunResponse(
            unmatched_payments_count=len(unmatched_payments),
            unpaid_invoices_count=len(unpaid_invoices),
            auto_matched_count=len(auto_matches),
            exceptions_count=len(exceptions),
            auto_matches=auto_matches,
            exceptions=exceptions,
        )

    @classmethod
    async def _find_candidates(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        payment: Payment,
        norm: Any,
        invoices: List[Invoice],
    ) -> List[CandidateMatch]:
        candidates: List[CandidateMatch] = []
        payment_amt = payment.unallocated_amount

        # Load aliases for counterparty fuzzy lookup
        alias_query = await db.execute(
            select(EntityAlias).where(EntityAlias.tenant_id == tenant_id)
        )
        aliases = alias_query.scalars().all()

        for inv in invoices:
            if inv.outstanding_balance <= Decimal("0.0000"):
                continue

            inv_balance = inv.outstanding_balance
            inv_num_clean = inv.invoice_number.upper().strip()

            # Rule 1: Exact reference match in narration/ref
            has_ref_match = (
                (norm.reference_number and norm.reference_number.upper() == inv_num_clean) or
                any(ref.upper() == inv_num_clean for ref in norm.invoice_references) or
                (inv_num_clean in payment.raw_narration.upper())
            )

            # Case 1A: Exact reference + Exact amount
            if has_ref_match and payment_amt == inv_balance:
                candidates.append(
                    CandidateMatch(
                        payment_id=payment.id,
                        invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        payment_reference=payment.payment_reference,
                        payment_date=payment.payment_date,
                        invoice_date=inv.invoice_date,
                        invoice_total=inv.total_amount,
                        invoice_outstanding=inv.outstanding_balance,
                        payment_total=payment.total_amount,
                        payment_unallocated=payment.unallocated_amount,
                        allocated_amount=payment_amt,
                        confidence_score=1.0,
                        match_type="exact_reference_and_amount",
                        explanation=f"Exact invoice reference '{inv.invoice_number}' found in bank narration with identical amount.",
                    )
                )
                continue

            # Case 1B: Exact reference + TDS deduction math
            if has_ref_match and payment_amt < inv_balance:
                for rate in cls.TDS_RATES:
                    expected_net = round_currency(inv_balance * (Decimal("1.0000") - rate))
                    if abs(payment_amt - expected_net) <= Decimal("0.5000"):
                        tds_amt = round_currency(inv_balance * rate)
                        candidates.append(
                            CandidateMatch(
                                payment_id=payment.id,
                                invoice_id=inv.id,
                                invoice_number=inv.invoice_number,
                                payment_reference=payment.payment_reference,
                                payment_date=payment.payment_date,
                                invoice_date=inv.invoice_date,
                                invoice_total=inv.total_amount,
                                invoice_outstanding=inv.outstanding_balance,
                                payment_total=payment.total_amount,
                                payment_unallocated=payment.unallocated_amount,
                                allocated_amount=payment_amt,
                                tds_deducted=tds_amt,
                                confidence_score=0.98,
                                match_type="exact_ref_with_tds",
                                explanation=f"Exact reference '{inv.invoice_number}' matched with statutory {int(rate*100)}% TDS deduction (Rs.{tds_amt}).",
                            )
                        )
                        break

            # Case 1C: Exact reference + Partial Payment
            if has_ref_match and payment_amt < inv_balance:
                candidates.append(
                    CandidateMatch(
                        payment_id=payment.id,
                        invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        payment_reference=payment.payment_reference,
                        payment_date=payment.payment_date,
                        invoice_date=inv.invoice_date,
                        invoice_total=inv.total_amount,
                        invoice_outstanding=inv.outstanding_balance,
                        payment_total=payment.total_amount,
                        payment_unallocated=payment.unallocated_amount,
                        allocated_amount=payment_amt,
                        residual_amount=inv_balance - payment_amt,
                        residual_reason="partial_settlement",
                        confidence_score=0.96,
                        match_type="exact_ref_partial_payment",
                        explanation=f"Exact reference '{inv.invoice_number}' matched. Partial settlement leaves Rs.{inv_balance - payment_amt} balance.",
                    )
                )

            # Rule 2: Counterparty Alias Match + Amount Match
            if not has_ref_match and norm.counterparty_name:
                matched_party = False
                for a in aliases:
                    if a.alias_name.upper() in norm.counterparty_name.upper() and a.entity_id == inv.customer_id:
                        matched_party = True
                        break

                if matched_party and payment_amt == inv_balance:
                    candidates.append(
                        CandidateMatch(
                            payment_id=payment.id,
                            invoice_id=inv.id,
                            invoice_number=inv.invoice_number,
                            payment_reference=payment.payment_reference,
                            payment_date=payment.payment_date,
                            invoice_date=inv.invoice_date,
                            invoice_total=inv.total_amount,
                            invoice_outstanding=inv.outstanding_balance,
                            payment_total=payment.total_amount,
                            payment_unallocated=payment.unallocated_amount,
                            allocated_amount=payment_amt,
                            confidence_score=0.88,
                            match_type="alias_and_amount_match",
                            explanation=f"Counterparty alias matched customer with exact balance match.",
                        )
                    )

            # Rule 3: Small Round-Off Tolerance (<= Rs. 5 difference)
            if has_ref_match and abs(payment_amt - inv_balance) <= cls.ROUND_OFF_TOLERANCE:
                diff = inv_balance - payment_amt
                candidates.append(
                    CandidateMatch(
                        payment_id=payment.id,
                        invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        payment_reference=payment.payment_reference,
                        payment_date=payment.payment_date,
                        invoice_date=inv.invoice_date,
                        invoice_total=inv.total_amount,
                        invoice_outstanding=inv.outstanding_balance,
                        payment_total=payment.total_amount,
                        payment_unallocated=payment.unallocated_amount,
                        allocated_amount=payment_amt,
                        round_off_difference=diff,
                        confidence_score=0.95,
                        match_type="exact_ref_with_roundoff",
                        explanation=f"Matched with rounding difference of Rs.{diff}.",
                    )
                )

        return candidates

    @classmethod
    async def get_exceptions(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> List[ReconciliationExceptionItem]:
        # Perform dry-run candidate retrieval on unmatched payments
        pay_res = await db.execute(
            select(Payment).where(
                Payment.tenant_id == tenant_id,
                Payment.status.in_(["unmatched", "partially_matched"]),
                Payment.unallocated_amount > Decimal("0.0000"),
            ).order_by(Payment.payment_date.asc())
        )
        unmatched_payments = pay_res.scalars().all()

        inv_res = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(["unpaid", "partially_paid"]),
                Invoice.outstanding_balance > Decimal("0.0000"),
            ).order_by(Invoice.invoice_date.asc())
        )
        unpaid_invoices = inv_res.scalars().all()

        items: List[ReconciliationExceptionItem] = []
        for payment in unmatched_payments:
            norm = NarrationService.normalize(payment.raw_narration)
            candidates = await cls._find_candidates(
                db=db,
                tenant_id=tenant_id,
                payment=payment,
                norm=norm,
                invoices=unpaid_invoices,
            )
            reason = "ambiguous_candidates" if len(candidates) > 1 else (
                "unmatched_residual" if len(candidates) == 1 else "unknown_counterparty"
            )
            items.append(
                ReconciliationExceptionItem(
                    payment_id=payment.id,
                    payment_reference=payment.payment_reference,
                    payment_date=payment.payment_date,
                    payment_total=payment.total_amount,
                    payment_unallocated=payment.unallocated_amount,
                    raw_narration=payment.raw_narration,
                    candidates=candidates,
                    reason=reason,
                )
            )
        return items

    @classmethod
    async def confirm_allocation(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
        req: AllocationConfirmRequest,
    ) -> PaymentAllocation:
        # Determine allocated amount
        pay_res = await db.execute(select(Payment).where(Payment.tenant_id == tenant_id, Payment.id == payment_id))
        payment = pay_res.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

        inv_res = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id))
        invoice = inv_res.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice record not found.")

        alloc_amount = req.allocated_amount or min(payment.unallocated_amount, invoice.outstanding_balance)
        tds = req.tds_deducted or Decimal("0.0000")
        discount = req.discount_allowed or Decimal("0.0000")
        round_off = req.round_off_difference or Decimal("0.0000")
        bank_charges = req.bank_charges or Decimal("0.0000")

        alloc_payload = PaymentAllocationRequest(
            invoice_id=invoice_id,
            allocated_amount=alloc_amount,
            tds_deducted=tds,
            discount_allowed=discount,
            bank_charges=bank_charges,
            round_off_difference=round_off,
        )

        return await FinanceService.allocate_payment(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            payment_id=payment_id,
            data=alloc_payload,
        )
