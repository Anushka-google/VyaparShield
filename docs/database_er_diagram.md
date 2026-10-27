# VyaparShield — Database Entity-Relationship (ER) Diagram

**Phase:** Phase 0 — Engineering Design & Database Architecture  
**Database:** PostgreSQL 16 with `pgvector`  

---

## 1. Visual Entity-Relationship Diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ MEMBERSHIPS : has
    ORGANIZATIONS ||--o{ CUSTOMERS : owns
    ORGANIZATIONS ||--o{ VENDORS : owns
    ORGANIZATIONS ||--o{ DOCUMENTS : stores
    ORGANIZATIONS ||--o{ INVOICES : issues_or_receives
    ORGANIZATIONS ||--o{ PAYMENTS : records
    ORGANIZATIONS ||--o{ PAYMENT_ALLOCATIONS : reconciles
    ORGANIZATIONS ||--o{ LEDGER_EVENTS : audits
    ORGANIZATIONS ||--o{ FORECASTS : projects
    ORGANIZATIONS ||--o{ APPROVALS : governs

    USERS ||--o{ MEMBERSHIPS : holds
    USERS ||--o{ APPROVALS : reviews
    USERS ||--o{ AUDIT_EVENTS : triggers

    CUSTOMERS ||--o{ INVOICES : billed_to
    CUSTOMERS ||--o{ ENTITY_ALIASES : has_alias
    VENDORS ||--o{ ENTITY_ALIASES : has_alias

    DOCUMENTS ||--o{ INVOICES : source_of

    INVOICES ||--|{ INVOICE_LINES : contains
    INVOICES ||--o{ PAYMENT_ALLOCATIONS : settled_by
    PAYMENTS ||--o{ PAYMENT_ALLOCATIONS : allocated_to

    ORGANIZATIONS {
        uuid id PK
        string name
        string gstin UK
        string pan
        string currency
        timestamp created_at
    }

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        timestamp created_at
    }

    MEMBERSHIPS {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        string role "owner | accountant | reviewer | admin"
        timestamp created_at
    }

    CUSTOMERS {
        uuid id PK
        uuid tenant_id FK
        string name
        string gstin
        string email
        string phone
        int credit_period_days
    }

    VENDORS {
        uuid id PK
        uuid tenant_id FK
        string name
        string gstin
        string bank_account_no
        string ifsc_code
    }

    ENTITY_ALIASES {
        uuid id PK
        uuid tenant_id FK
        string entity_type "customer | vendor"
        uuid entity_id
        string alias_name
        numeric confidence
    }

    DOCUMENTS {
        uuid id PK
        uuid tenant_id FK
        string file_name
        string file_type
        string storage_uri
        string file_hash UK
        string document_type "invoice | bank_statement"
        string status
        timestamp created_at
    }

    INVOICES {
        uuid id PK
        uuid tenant_id FK
        uuid customer_id FK
        uuid document_id FK
        string invoice_number
        date invoice_date
        date due_date
        numeric subtotal
        numeric cgst_amount
        numeric sgst_amount
        numeric igst_amount
        numeric total_amount
        numeric paid_amount
        numeric outstanding_balance
        string status "unpaid | partially_paid | paid | overdue"
        timestamp created_at
    }

    INVOICE_LINES {
        uuid id PK
        uuid invoice_id FK
        string description
        string hsn_sac_code
        numeric quantity
        numeric unit_price
        numeric tax_rate
        numeric line_total
    }

    PAYMENTS {
        uuid id PK
        uuid tenant_id FK
        string payment_reference
        date payment_date
        numeric total_amount
        numeric allocated_amount
        numeric unallocated_amount
        string payment_mode "UPI | NEFT | RTGS | IMPS | CHEQUE"
        string raw_narration
        string status "unmatched | partially_matched | fully_matched"
    }

    PAYMENT_ALLOCATIONS {
        uuid id PK
        uuid tenant_id FK
        uuid payment_id FK
        uuid invoice_id FK
        numeric allocated_amount
        numeric tds_deducted
        numeric discount_allowed
        numeric bank_charges
        numeric round_off_difference
        string match_type "exact | fuzzy | manual"
        numeric confidence_score
        string status "suggested | confirmed | rejected | reversed"
        uuid reviewer_id FK
        timestamp created_at
    }

    LEDGER_EVENTS {
        uuid id PK
        uuid tenant_id FK
        string event_type
        string source_entity
        uuid source_id
        numeric amount_delta
        numeric running_balance
        timestamp created_at
    }

    APPROVALS {
        uuid id PK
        uuid tenant_id FK
        string action_type
        jsonb payload
        string status "pending | approved | rejected"
        uuid reviewer_id FK
        text reason
        timestamp created_at
        timestamp decided_at
    }

    AUDIT_EVENTS {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        string event_name
        string ip_address
        jsonb details
        timestamp created_at
    }
```

---

## 2. Integrity and Relational Constraints

1. **Foreign Key Cascade Policy:**
   - Invoices reference `customers(id)` with `ON DELETE RESTRICT` (customers with active invoices cannot be deleted).
   - `invoice_lines` reference `invoices(id)` with `ON DELETE CASCADE`.
   - `payment_allocations` reference `payments(id)` and `invoices(id)` with `ON DELETE RESTRICT`.
2. **Unique Business Keys:**
   - Composite Unique: `(tenant_id, invoice_number)` ensures no duplicate invoice numbers within the same business tenant.
   - Unique: `(file_hash)` prevents uploading the exact same document twice.
3. **Check Constraints:**
   - `invoices.outstanding_balance >= 0`
   - `invoices.paid_amount >= 0`
   - `payments.allocated_amount <= payments.total_amount`
   - `payments.unallocated_amount >= 0`
