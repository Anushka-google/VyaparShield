import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Customer,
    Vendor,
    EntityAlias,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    LedgerEvent,
    AuditEvent,
)
from app.schemas.finance import (
    InvoiceCreate,
    PaymentCreate,
    PaymentAllocationRequest,
    AgingBucketReport,
)
from app.database.session import round_currency, to_decimal


class FinanceService:
    @staticmethod
    async def log_audit_event(
        db: AsyncSession,
        event_name: str,
        tenant_id: Optional[uuid.UUID],
        user_id: Optional[uuid.UUID],
        details: dict,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_name=event_name,
            ip_address=ip_address,
            details=details,
        )
        db.add(event)
        return event

    @classmethod
    async def create_invoice(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: InvoiceCreate,
    ) -> Invoice:
        # Verify customer belongs to this tenant
        res = await db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == data.customer_id)
        )
        customer = res.scalar_one_or_none()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer {data.customer_id} does not exist in this organization.",
            )

        # Check for duplicate invoice number in tenant
        dup = await db.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.invoice_number == data.invoice_number)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice number '{data.invoice_number}' already exists.",
            )

        # Calculate line totals and tax deterministically
        calculated_subtotal = Decimal("0.0000")
        total_tax_amount = Decimal("0.0000")
        invoice_lines: List[InvoiceLine] = []

        for line_data in data.lines:
            taxable = round_currency(line_data.quantity * line_data.unit_price)
            tax_rate_frac = line_data.tax_rate / Decimal("100.00")
            tax = round_currency(taxable * tax_rate_frac)
            line_tot = taxable + tax

            calculated_subtotal += taxable
            total_tax_amount += tax

            line = InvoiceLine(
                description=line_data.description,
                hsn_sac_code=line_data.hsn_sac_code,
                quantity=line_data.quantity,
                unit_price=round_currency(line_data.unit_price),
                tax_rate=line_data.tax_rate,
                line_total=line_tot,
            )
            invoice_lines.append(line)

        # Apply GST Jurisdictional Splitting
        if data.is_interstate:
            cgst = Decimal("0.0000")
            sgst = Decimal("0.0000")
            igst = total_tax_amount
        else:
            cgst = round_currency(total_tax_amount / Decimal("2.0"))
            sgst = total_tax_amount - cgst
            igst = Decimal("0.0000")

        total_amount = calculated_subtotal + cgst + sgst + igst
        outstanding_balance = total_amount

        invoice = Invoice(
            tenant_id=tenant_id,
            customer_id=data.customer_id,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            subtotal=calculated_subtotal,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            total_amount=total_amount,
            paid_amount=Decimal("0.0000"),
            outstanding_balance=outstanding_balance,
            status="unpaid" if outstanding_balance > 0 else "paid",
            lines=invoice_lines,
        )
        db.add(invoice)
        await db.flush()

        # Emit immutable ledger event
        ledger_event = LedgerEvent(
            tenant_id=tenant_id,
            event_type="INVOICE_CREATED",
            source_entity="invoices",
            source_id=invoice.id,
            amount_delta=total_amount,
            running_balance=outstanding_balance,
        )
        db.add(ledger_event)

        # Log audit trail
        await cls.log_audit_event(
            db=db,
            event_name="INVOICE_CREATED",
            tenant_id=tenant_id,
            user_id=user_id,
            details={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "total_amount": str(total_amount),
            },
        )
        await db.commit()
        await db.refresh(invoice)
        return invoice

    @classmethod
    async def record_payment(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PaymentCreate,
    ) -> Payment:
        total = round_currency(data.total_amount)
        if total <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment amount must be strictly greater than zero.",
            )

        payment = Payment(
            tenant_id=tenant_id,
            payment_reference=data.payment_reference,
            payment_date=data.payment_date,
            total_amount=total,
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=total,
            payment_mode=data.payment_mode,
            raw_narration=data.raw_narration,
            status="unmatched",
        )
        db.add(payment)
        await db.flush()

        ledger_event = LedgerEvent(
            tenant_id=tenant_id,
            event_type="PAYMENT_RECEIVED",
            source_entity="payments",
            source_id=payment.id,
            amount_delta=total,
            running_balance=total,
        )
        db.add(ledger_event)

        await cls.log_audit_event(
            db=db,
            event_name="PAYMENT_RECEIVED",
            tenant_id=tenant_id,
            user_id=user_id,
            details={
                "payment_id": str(payment.id),
                "total_amount": str(total),
                "reference": payment.payment_reference,
            },
        )
        await db.commit()
        await db.refresh(payment)
        return payment

    @classmethod
    async def allocate_payment(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
        data: PaymentAllocationRequest,
    ) -> PaymentAllocation:
        # Atomic lock on Payment within tenant
        p_res = await db.execute(
            select(Payment).where(Payment.tenant_id == tenant_id, Payment.id == payment_id).with_for_update()
        )
        payment = p_res.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

        # Atomic lock on Invoice within tenant
        i_res = await db.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == data.invoice_id).with_for_update()
        )
        invoice = i_res.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice record not found.")

        alloc_amount = round_currency(data.allocated_amount)
        tds = round_currency(data.tds_deducted)
        discount = round_currency(data.discount_allowed)
        round_off = round_currency(data.round_off_difference)

        # Invariant 1: Payment Conservation (Cannot allocate more than available unallocated funds)
        if alloc_amount > payment.unallocated_amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Allocation amount {alloc_amount} exceeds payment unallocated balance {payment.unallocated_amount}.",
            )

        # Invariant 2: Total Effective Settlement cannot exceed Invoice Outstanding Balance
        effective_settlement = alloc_amount + tds + discount + round_off
        if effective_settlement > invoice.outstanding_balance:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Effective settlement {effective_settlement} exceeds invoice outstanding balance {invoice.outstanding_balance}.",
            )

        # Apply state updates
        payment.allocated_amount += alloc_amount
        payment.unallocated_amount -= alloc_amount
        if payment.unallocated_amount == Decimal("0.0000"):
            payment.status = "fully_matched"
        else:
            payment.status = "partially_matched"

        invoice.paid_amount += effective_settlement
        invoice.outstanding_balance -= effective_settlement
        if invoice.outstanding_balance == Decimal("0.0000"):
            invoice.status = "paid"
        else:
            invoice.status = "partially_paid"

        allocation = PaymentAllocation(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=alloc_amount,
            tds_deducted=tds,
            discount_allowed=discount,
            bank_charges=round_currency(data.bank_charges),
            round_off_difference=round_off,
            match_type="deterministic_allocation",
            confidence_score=Decimal("1.0000"),
            status="confirmed",
            reviewer_id=user_id,
        )
        db.add(allocation)
        await db.flush()

        # Emit Ledger Event
        ledger_event = LedgerEvent(
            tenant_id=tenant_id,
            event_type="PAYMENT_ALLOCATED",
            source_entity="payment_allocations",
            source_id=allocation.id,
            amount_delta=-effective_settlement,
            running_balance=invoice.outstanding_balance,
        )
        db.add(ledger_event)

        # Log Audit Trail
        await cls.log_audit_event(
            db=db,
            event_name="PAYMENT_ALLOCATED",
            tenant_id=tenant_id,
            user_id=user_id,
            details={
                "allocation_id": str(allocation.id),
                "payment_id": str(payment.id),
                "invoice_id": str(invoice.id),
                "allocated_amount": str(alloc_amount),
                "tds_deducted": str(tds),
                "invoice_new_balance": str(invoice.outstanding_balance),
            },
        )

        await db.commit()
        await db.refresh(allocation)
        return allocation

    @classmethod
    async def get_receivables_aging(cls, db: AsyncSession, tenant_id: uuid.UUID) -> AgingBucketReport:
        today = date.today()
        res = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.outstanding_balance > Decimal("0.0000"),
            )
        )
        unpaid_invoices = res.scalars().all()

        total_outstanding = Decimal("0.0000")
        current_0_30 = Decimal("0.0000")
        overdue_31_60 = Decimal("0.0000")
        overdue_61_90 = Decimal("0.0000")
        overdue_90_plus = Decimal("0.0000")

        for inv in unpaid_invoices:
            bal = inv.outstanding_balance
            total_outstanding += bal
            overdue_days = (today - inv.due_date).days

            if overdue_days <= 30:
                current_0_30 += bal
            elif 31 <= overdue_days <= 60:
                overdue_31_60 += bal
            elif 61 <= overdue_days <= 90:
                overdue_61_90 += bal
            else:
                overdue_90_plus += bal

        return AgingBucketReport(
            total_outstanding=total_outstanding,
            current_0_30=current_0_30,
            overdue_31_60=overdue_31_60,
            overdue_61_90=overdue_61_90,
            overdue_90_plus=overdue_90_plus,
        )
