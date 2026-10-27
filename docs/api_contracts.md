# VyaparShield — REST API Contracts & Endpoint Specifications

**Phase:** Phase 0 — API Design & Interface Contracts  
**Protocol:** RESTful HTTPS / JSON  
**Base URL:** `/api/v1`  
**Authentication:** Bearer JWT Header (`Authorization: Bearer <token>`)  

---

## 1. Global Standards & Error Format

All error responses adhere to the RFC 7807 problem details specification:

```json
{
  "error": {
    "code": "INVALID_INVOICE_STATE",
    "message": "Payment allocation exceeds outstanding invoice balance.",
    "details": {
      "invoice_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "outstanding_balance": "15000.00",
      "attempted_allocation": "20000.00"
    },
    "timestamp": "2026-10-27T10:00:00Z"
  }
}
```

---

## 2. Authentication & Tenancy

### `POST /auth/register`
- **Description:** Registers a new organization and admin user account.
- **Request:**
  ```json
  {
    "organization_name": "Acme Textiles MSME",
    "gstin": "27AAAAA0000A1Z5",
    "email": "owner@acmetextiles.com",
    "password": "StrongPassword123!",
    "full_name": "Rajesh Sharma"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "user_id": "018f3a21-...",
    "tenant_id": "018f3a20-...",
    "role": "owner",
    "token": "eyJhbGciOi..."
  }
  ```

### `POST /auth/login`
- **Description:** Authenticates user and returns tenant-scoped JWT token.
- **Request:** `{"email": "...", "password": "..."}`
- **Response `200 OK`:** `{"access_token": "...", "token_type": "bearer", "tenant_id": "..."}`

---

## 3. Master Parties & Aliases

### `POST /customers`
- **Request:**
  ```json
  {
    "name": "Bharat Garments Ltd",
    "gstin": "27BBBBB1111B1Z2",
    "email": "accounts@bharatgarments.in",
    "phone": "+919876543210",
    "credit_period_days": 30
  }
  ```
- **Response `201 Created`**

### `POST /customers/{id}/aliases`
- **Description:** Maps alternate names found in bank narrations (e.g. UPI/NEFT text) to customer record.
- **Request:** `{"alias_name": "BHARAT GARMENTS MUMBAI", "confidence": 1.0}`
- **Response `201 Created`**

---

## 4. Invoices & Aging

### `POST /invoices`
- **Request:**
  ```json
  {
    "customer_id": "018f3a25-...",
    "invoice_number": "INV-2026-0042",
    "invoice_date": "2026-10-01",
    "due_date": "2026-10-31",
    "lines": [
      {
        "description": "Premium Cotton Fabric 100m",
        "hsn_sac_code": "5208",
        "quantity": "100.00",
        "unit_price": "250.00",
        "tax_rate": "5.00"
      }
    ]
  }
  ```
- **Response `201 Created`:** Calculated `subtotal`, `cgst`, `sgst`, `igst`, `total_amount`, `outstanding_balance`.

### `GET /invoices/aging`
- **Description:** Returns deterministic accounts receivable aging breakdown.
- **Response `200 OK`:**
  ```json
  {
    "total_outstanding": "1482500.00",
    "buckets": {
      "current_0_30": "842500.00",
      "overdue_31_60": "340000.00",
      "overdue_61_90": "200000.00",
      "overdue_90_plus": "100000.00"
    },
    "currency": "INR"
  }
  ```

---

## 5. Payments & Allocation Engine

### `POST /payments`
- **Request:**
  ```json
  {
    "payment_reference": "UPI/412345678901/PAY",
    "payment_date": "2026-10-15",
    "total_amount": "25725.00",
    "payment_mode": "UPI",
    "raw_narration": "UPI/412345678901/PAYMENT FROM BHARAT GARMENTS/BARB0..."
  }
  ```
- **Response `201 Created`**

### `POST /payments/{id}/allocate`
- **Headers:** `Idempotency-Key: <UUID>` (Guarantees no duplicate execution)
- **Request:**
  ```json
  {
    "invoice_id": "018f3a26-...",
    "allocated_amount": "25000.00",
    "tds_deducted": "500.00",
    "discount_allowed": "200.00",
    "round_off_difference": "25.00"
  }
  ```
- **Response `200 OK`:** Updated invoice balance, payment unallocated balance, and created ledger event.

---

## 6. Document Ingestion & Review Queue

### `POST /documents/upload`
- **Request:** Multipart form-data (`file: [PDF/Image/CSV]`, `document_type: "invoice" | "bank_statement"`)
- **Response `202 Accepted`:** `{"document_id": "...", "status": "queued", "job_id": "..."}`

### `GET /documents/review-queue`
- **Description:** Returns extracted fields requiring human review due to low OCR confidence or validation warnings.
- **Response `200 OK`:**
  ```json
  [
    {
      "document_id": "018f3a30-...",
      "field_name": "gstin",
      "extracted_value": "27AAAAA0OOOA1Z5",
      "confidence": 0.64,
      "validation_error": "Character 'O' invalid in PAN numeric block; suggested '0'."
    }
  ]
  ```

---

## 7. AI Finance Assistant & Human Approvals

### `POST /finance/assistant/query`
- **Request:**
  ```json
  {
    "question": "Why is cash flow projected to dip next month?",
    "include_citations": true
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "answer": "Projected cash flow dips by ₹3,40,000 due to 3 high-value invoices from Sharma Enterprises and Bharat Garments that are past 45 days overdue...",
    "calculation_proof": {
      "expected_inflow": "500000.00",
      "expected_outflow": "840000.00",
      "net_deficit": "-340000.00"
    },
    "citations": [
      {"entity": "invoice", "id": "018f3a26-...", "reference": "INV-2026-0042", "amount": "26250.00"}
    ]
  }
  ```

### `POST /approvals/{id}/decide`
- **Request:** `{"decision": "approved", "reason": "Verified with vendor over phone."}`
- **Response `200 OK`:** `{"status": "executed", "timestamp": "2026-10-27T10:05:00Z"}`
