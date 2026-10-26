# NexusOps AI & VyaparShield — Data Dictionary & Entity Catalog

**Document Version:** 1.0.0  
**Phase:** A0.1 — Data Modeling & Schema Design  
**Authoritative Store:** PostgreSQL 16 + pgvector  

---

## 1. Schema Design Principles
1. **Multi-Tenant Isolation:** Every operational table contains a `tenant_id UUID` column with a mandatory foreign key referencing `organizations(id)` and composite indices `(tenant_id, id)`.
2. **Decimal-Safe Financial Arithmetic:** All monetary fields use `NUMERIC(18, 4)`. Floating-point types are strictly forbidden.
3. **Auditing & Event Immutability:** State changes generate immutable `ledger_events` and `audit_events`. Financial tables never hard-delete records; they use status flags and soft-deletes.
4. **Primary Keys:** All primary keys use `UUIDv7` (or `UUIDv4`) to avoid serial enumeration attacks.

---

## 2. Core Entities

### 2.1 Identity, Tenancy & Access Control

#### `organizations` (Tenants)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique organization / tenant identifier. |
| `name` | VARCHAR(255) | NOT NULL | Legal business name of the MSME. |
| `gstin` | VARCHAR(15) | UNIQUE, NULLABLE | 15-character Indian GST Identification Number. |
| `pan` | VARCHAR(10) | NULLABLE | 10-character Permanent Account Number. |
| `currency` | VARCHAR(3) | DEFAULT 'INR' | Base operational currency (INR, USD). |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation timestamp. |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last record update timestamp. |

#### `users`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique user identity. |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User email address (login identifier). |
| `hashed_password` | VARCHAR(255) | NOT NULL | Argon2 / bcrypt password hash. |
| `full_name` | VARCHAR(255) | NOT NULL | User's full name. |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account active status. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp of user registration. |

#### `memberships`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Membership association record. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant reference. |
| `user_id` | UUID | FK -> users(id) | User reference. |
| `role` | VARCHAR(50) | NOT NULL | RBAC Role (`owner`, `finance`, `reviewer`, `admin`). |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp when role was assigned. |

---

### 2.2 Master Parties & Alias Resolution

#### `customers`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Customer identifier. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `name` | VARCHAR(255) | NOT NULL | Customer legal business name. |
| `gstin` | VARCHAR(15) | NULLABLE | Customer GSTIN. |
| `email` | VARCHAR(255) | NULLABLE | Billing email. |
| `phone` | VARCHAR(20) | NULLABLE | Contact telephone. |
| `credit_period_days`| INTEGER | DEFAULT 30 | Agreed credit period for overdue calculation. |

#### `vendors`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Vendor identifier. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `name` | VARCHAR(255) | NOT NULL | Vendor commercial name. |
| `gstin` | VARCHAR(15) | NULLABLE | Vendor GSTIN. |
| `bank_account_no` | VARCHAR(50) | NULLABLE | Encrypted/Masked vendor bank account. |
| `ifsc_code` | VARCHAR(11) | NULLABLE | Bank branch IFSC code. |

#### `vendor_customer_aliases`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Alias identifier. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `entity_type` | VARCHAR(20) | NOT NULL | `'customer'` or `'vendor'`. |
| `entity_id` | UUID | NOT NULL | Foreign key to `customers(id)` or `vendors(id)`. |
| `alias_name` | VARCHAR(255) | NOT NULL | Known alternate name (e.g., from bank UPI/NEFT string). |
| `confidence` | NUMERIC(5, 4)| DEFAULT 1.0000 | Match confidence score. |

---

### 2.3 Financial Documents & Invoices

#### `documents`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique document identifier. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `file_name` | VARCHAR(255) | NOT NULL | Original uploaded filename. |
| `file_type` | VARCHAR(50) | NOT NULL | `application/pdf`, `text/csv`, `application/vnd.ms-excel`. |
| `storage_uri` | VARCHAR(512) | NOT NULL | Object storage path (`s3://...` or local path). |
| `file_hash` | VARCHAR(64) | NOT NULL | SHA-256 hash for deduplication. |
| `document_type` | VARCHAR(50) | NOT NULL | `invoice`, `bank_statement`, `receipt`. |
| `status` | VARCHAR(50) | NOT NULL | `queued`, `processing`, `extracted`, `review_required`, `failed`. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Upload timestamp. |

#### `invoices`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique invoice ID. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `document_id` | UUID | FK -> documents(id), NULL | Source document origin. |
| `customer_id` | UUID | FK -> customers(id) | Buyer / Debtor reference. |
| `invoice_number` | VARCHAR(100) | NOT NULL | Bill/Invoice number. |
| `invoice_date` | DATE | NOT NULL | Invoice issuance date. |
| `due_date` | DATE | NOT NULL | Payment deadline date. |
| `subtotal` | NUMERIC(18, 4)| NOT NULL | Pre-tax taxable value. |
| `cgst_amount` | NUMERIC(18, 4)| DEFAULT 0.0000 | Central GST amount. |
| `sgst_amount` | NUMERIC(18, 4)| DEFAULT 0.0000 | State GST amount. |
| `igst_amount` | NUMERIC(18, 4)| DEFAULT 0.0000 | Integrated GST amount. |
| `total_amount` | NUMERIC(18, 4)| NOT NULL | Total gross invoice value. |
| `paid_amount` | NUMERIC(18, 4)| DEFAULT 0.0000 | Total reconciled paid amount. |
| `outstanding_balance`| NUMERIC(18, 4)| NOT NULL | Remaining balance (`total - paid - deductions`). |
| `status` | VARCHAR(50) | NOT NULL | `unpaid`, `partially_paid`, `paid`, `overdue`, `disputed`. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp created. |

#### `invoice_lines`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Line item identifier. |
| `invoice_id` | UUID | FK -> invoices(id) | Parent invoice reference. |
| `description` | TEXT | NOT NULL | Item or service description. |
| `hsn_sac_code` | VARCHAR(20) | NULLABLE | Indian HSN/SAC statutory classification code. |
| `quantity` | NUMERIC(14, 4)| NOT NULL | Item quantity. |
| `unit_price` | NUMERIC(18, 4)| NOT NULL | Rate per unit. |
| `tax_rate` | NUMERIC(5, 2) | NOT NULL | GST rate percentage (e.g. 5.00, 18.00). |
| `line_total` | NUMERIC(18, 4)| NOT NULL | Quantity * Unit Price + Tax. |

---

### 2.4 Payments & Reconciliation

#### `payments`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique payment identifier. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `payment_reference` | VARCHAR(100) | NULLABLE | UTR number / Cheque number / UPI Ref ID. |
| `payment_date` | DATE | NOT NULL | Date payment settled. |
| `total_amount` | NUMERIC(18, 4)| NOT NULL | Total credited amount. |
| `allocated_amount` | NUMERIC(18, 4)| DEFAULT 0.0000 | Amount allocated to invoices. |
| `unallocated_amount`| NUMERIC(18, 4)| NOT NULL | Remaining unapplied funds. |
| `raw_narration` | TEXT | NOT NULL | Raw bank statement line description. |
| `payment_mode` | VARCHAR(50) | NOT NULL | `UPI`, `NEFT`, `RTGS`, `IMPS`, `CHEQUE`, `CASH`. |
| `status` | VARCHAR(50) | NOT NULL | `unmatched`, `partially_matched`, `fully_matched`. |

#### `payment_matches` (Reconciliation Engine)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique match record. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `payment_id` | UUID | FK -> payments(id) | Source payment transaction. |
| `invoice_id` | UUID | FK -> invoices(id) | Target invoice settled. |
| `matched_amount` | NUMERIC(18, 4)| NOT NULL | Portion of payment applied. |
| `tds_deducted` | NUMERIC(18, 4)| DEFAULT 0.0000 | Detected TDS (194C/J) deduction. |
| `discount_allowed` | NUMERIC(18, 4)| DEFAULT 0.0000 | Cash discount given. |
| `bank_charges` | NUMERIC(18, 4)| DEFAULT 0.0000 | Gateway/IMPS processing fee. |
| `round_off_difference`| NUMERIC(18, 4)| DEFAULT 0.0000 | Fractional paise difference. |
| `match_type` | VARCHAR(50) | NOT NULL | `exact_deterministic`, `fuzzy_ranked`, `manual`. |
| `confidence_score`| NUMERIC(5, 4)| NOT NULL | Confidence score (1.0000 for exact). |
| `status` | VARCHAR(50) | NOT NULL | `suggested`, `confirmed`, `rejected`, `reversed`. |
| `reviewer_id` | UUID | FK -> users(id), NULL | User who confirmed/rejected match. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp match proposed. |

#### `ledger_events` (Immutable Audit & Financial History)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Event ID. |
| `tenant_id` | UUID | FK -> organizations(id) | Tenant boundary. |
| `event_type` | VARCHAR(50) | NOT NULL | `INVOICE_CREATED`, `PAYMENT_RECEIVED`, `PAYMENT_ALLOCATED`, `DISCOUNT_APPLIED`, `REVERSAL`. |
| `source_entity` | VARCHAR(50) | NOT NULL | Table name (`invoices`, `payments`, `payment_matches`). |
| `source_id` | UUID | NOT NULL | Target record primary key. |
| `amount_delta` | NUMERIC(18, 4)| NOT NULL | Positive or negative balance change. |
| `running_balance` | NUMERIC(18, 4)| NOT NULL | Verified running balance after transaction. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Immutable event timestamp. |

---

### 2.5 ML Forecasts, AegisOps & Agent Governance

#### `forecasts` & `model_runs`
- `model_runs`: Stores `model_name`, `model_version`, `training_dataset_hash`, `evaluation_metrics (JSONB)`, `artifact_uri`.
- `forecasts`: Stores `tenant_id`, `forecast_date`, `horizon_days` (7, 30, 60), `scenario` (`base`, `best`, `worst`), `projected_inflow`, `projected_outflow`, `net_cash_flow`, `model_run_id`.

#### `incidents` (AegisOps)
- `id`, `tenant_id`, `title`, `service_name`, `severity` (`P1`, `P2`, `P3`), `status` (`open`, `investigating`, `mitigated`, `resolved`), `detected_at`, `mitigated_at`, `root_cause_summary`, `telemetry_snapshot (JSONB)`.

#### `agent_runs`, `tool_invocations` & `approvals` (AgentGuard)
- `agent_runs`: `id`, `tenant_id`, `workflow_type` (`cash_investigation`, `incident_mitigation`), `status` (`running`, `paused_for_approval`, `completed`, `failed`), `state_checkpoint (JSONB)`.
- `tool_invocations`: `id`, `agent_run_id`, `tool_name`, `parameters (JSONB)`, `policy_result` (`allowed`, `denied`, `approval_required`), `executed_at`, `postcondition_status` (`passed`, `failed`).
- `approvals`: `id`, `tenant_id`, `tool_invocation_id`, `requested_action`, `reviewer_id`, `decision` (`pending`, `approved`, `rejected`), `justification`, `decided_at`.
- `audit_events`: Tamper-evident log of all user/agent interactions, actor IP, event type, redacted payload, and timestamp.
