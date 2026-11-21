import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from app.database.session import round_currency


# --- Auth & Tenancy ---

class TenantRegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    pan: Optional[str] = Field(None, min_length=10, max_length=10)
    currency: str = Field("INR", max_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    pan: Optional[str] = Field(None, min_length=10, max_length=10)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=8)
    role: str = Field("accountant", pattern="^(owner|accountant|reviewer|admin)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    email: str


# --- Master Parties & Aliases ---

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    credit_period_days: int = Field(30, ge=0)


class CustomerResponse(CustomerCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    bank_account_no: Optional[str] = None
    ifsc_code: Optional[str] = None


class VendorResponse(VendorCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityAliasCreate(BaseModel):
    entity_type: str = Field(..., pattern="^(customer|vendor)$")
    entity_id: uuid.UUID
    alias_name: str = Field(..., min_length=2, max_length=255)
    confidence: Decimal = Field(Decimal("1.0000"), ge=0, le=1)


class EntityAliasResponse(EntityAliasCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Invoices ---

class InvoiceLineCreate(BaseModel):
    description: str
    hsn_sac_code: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(..., ge=0)  # e.g. 5.00, 12.00, 18.00


class InvoiceLineResponse(InvoiceLineCreate):
    id: uuid.UUID
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    due_date: date
    lines: List[InvoiceLineCreate] = Field(..., min_length=1)
    # Optional explicit tax overrides; if omitted, backend calculates them deterministically
    is_interstate: bool = False


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    subtotal: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    status: str
    created_at: datetime
    lines: List[InvoiceLineResponse]

    model_config = ConfigDict(from_attributes=True)


class AgingBucketReport(BaseModel):
    total_outstanding: Decimal
    current_0_30: Decimal
    overdue_31_60: Decimal
    overdue_61_90: Decimal
    overdue_90_plus: Decimal
    currency: str = "INR"


# --- Payments & Allocation ---

class PaymentCreate(BaseModel):
    payment_reference: Optional[str] = None
    payment_date: date
    total_amount: Decimal = Field(..., gt=0)
    payment_mode: str = Field("UPI")
    raw_narration: str = Field(..., min_length=2)


class PaymentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_reference: Optional[str]
    payment_date: date
    total_amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    payment_mode: str
    raw_narration: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentAllocationRequest(BaseModel):
    invoice_id: uuid.UUID
    allocated_amount: Decimal = Field(..., gt=0)
    tds_deducted: Decimal = Field(Decimal("0.0000"), ge=0)
    discount_allowed: Decimal = Field(Decimal("0.0000"), ge=0)
    bank_charges: Decimal = Field(Decimal("0.0000"), ge=0)
    round_off_difference: Decimal = Field(Decimal("0.0000"))


class PaymentAllocationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    allocated_amount: Decimal
    tds_deducted: Decimal
    discount_allowed: Decimal
    round_off_difference: Decimal
    match_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Audit Events ---

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    event_name: str
    ip_address: Optional[str]
    details: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
