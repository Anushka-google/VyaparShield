import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import (
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    Boolean,
    Integer,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base, money_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    """Tenant / Business Entity."""
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), unique=True, nullable=True, index=True)
    pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    customers: Mapped[List["Customer"]] = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    vendors: Mapped[List["Vendor"]] = relationship("Vendor", back_populates="organization", cascade="all, delete-orphan")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    """User account identity."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    """User-to-Organization association and RBAC Role."""
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="accountant")  # owner, accountant, reviewer, admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )


class Customer(Base):
    """Customer master record for Accounts Receivable (AR)."""
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    credit_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="customers")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="customer")
    aliases: Mapped[List["EntityAlias"]] = relationship(
        "EntityAlias",
        primaryjoin="and_(Customer.id==foreign(EntityAlias.entity_id), EntityAlias.entity_type=='customer')",
        cascade="all, delete-orphan",
        overlaps="aliases",
    )


class Vendor(Base):
    """Vendor master record for Accounts Payable (AP)."""
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    bank_account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="vendors")
    aliases: Mapped[List["EntityAlias"]] = relationship(
        "EntityAlias",
        primaryjoin="and_(Vendor.id==foreign(EntityAlias.entity_id), EntityAlias.entity_type=='vendor')",
        cascade="all, delete-orphan",
        overlaps="aliases",
    )


class EntityAlias(Base):
    """Counterparty alias for resolving noisy bank statement narrations (UPI/NEFT/IMPS)."""
    __tablename__ = "entity_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'customer' or 'vendor'
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "alias_name", name="uq_tenant_entity_alias"),
    )


class Document(Base):
    """Original document metadata & provenance."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # invoice, bank_statement, receipt
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)  # uploaded, extracted, review_needed, approved, rejected
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    validation_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    corrections: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "file_hash", name="uq_tenant_document_file_hash"),
    )


class Invoice(Base):
    """Invoice authoritative record with decimal-safe money and GST fields."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    subtotal: Mapped[Decimal] = money_column(nullable=False)
    cgst_amount: Mapped[Decimal] = money_column(nullable=False)
    sgst_amount: Mapped[Decimal] = money_column(nullable=False)
    igst_amount: Mapped[Decimal] = money_column(nullable=False)
    total_amount: Mapped[Decimal] = money_column(nullable=False)
    paid_amount: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))
    outstanding_balance: Mapped[Decimal] = money_column(nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="unpaid", nullable=False)  # unpaid, partially_paid, paid, overdue
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invoices")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    lines: Mapped[List["InvoiceLine"]] = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    allocations: Mapped[List["PaymentAllocation"]] = relationship("PaymentAllocation", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_tenant_invoice_number"),
        CheckConstraint("total_amount >= 0", name="chk_invoice_total_positive"),
        CheckConstraint("paid_amount >= 0", name="chk_invoice_paid_positive"),
        CheckConstraint("outstanding_balance >= 0", name="chk_invoice_balance_non_negative"),
    )


class InvoiceLine(Base):
    """Individual line items within an invoice."""
    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hsn_sac_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price: Mapped[Decimal] = money_column(nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # e.g., 5.00, 12.00, 18.00
    line_total: Mapped[Decimal] = money_column(nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")


class Payment(Base):
    """Payment record received or issued."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_amount: Mapped[Decimal] = money_column(nullable=False)
    allocated_amount: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))
    unallocated_amount: Mapped[Decimal] = money_column(nullable=False)

    payment_mode: Mapped[str] = mapped_column(String(50), default="UPI", nullable=False)  # UPI, NEFT, RTGS, IMPS, CHEQUE
    raw_narration: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="unmatched", nullable=False)  # unmatched, partially_matched, fully_matched
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="payments")
    allocations: Mapped[List["PaymentAllocation"]] = relationship("PaymentAllocation", back_populates="payment")

    __table_args__ = (
        CheckConstraint("total_amount > 0", name="chk_payment_total_positive"),
        CheckConstraint("allocated_amount >= 0", name="chk_payment_allocated_non_negative"),
        CheckConstraint("unallocated_amount >= 0", name="chk_payment_unallocated_non_negative"),
        CheckConstraint("allocated_amount <= total_amount", name="chk_payment_allocated_lte_total"),
    )


class PaymentAllocation(Base):
    """Reconciliation match connecting a payment to an invoice."""
    __tablename__ = "payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)

    allocated_amount: Mapped[Decimal] = money_column(nullable=False)
    tds_deducted: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))
    discount_allowed: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))
    bank_charges: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))
    round_off_difference: Mapped[Decimal] = money_column(nullable=False, default=Decimal("0.0000"))

    match_type: Mapped[str] = mapped_column(String(50), default="exact_deterministic", nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="confirmed", nullable=False)  # suggested, confirmed, rejected, reversed
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="allocations")
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="allocations")


class LedgerEvent(Base):
    """Immutable audit & event-sourcing log for financial balance changes."""
    __tablename__ = "ledger_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # INVOICE_CREATED, PAYMENT_RECEIVED, PAYMENT_ALLOCATED, REVERSAL
    source_entity: Mapped[str] = mapped_column(String(50), nullable=False)  # invoices, payments, payment_allocations
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount_delta: Mapped[Decimal] = money_column(nullable=False)
    running_balance: Mapped[Decimal] = money_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    """Immutable security and operations audit log."""
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AnomalyAlert(Base):
    """Financial & Operational Anomaly Alert with human-in-the-loop triage."""
    __tablename__ = "anomaly_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # invoice, payment, vendor, customer
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # duplicate_invoice, unusual_amount, velocity_spike, round_number_surge, ml_outlier
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    anomaly_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.5000"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open, expected, suspicious, investigating, dismissed
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
