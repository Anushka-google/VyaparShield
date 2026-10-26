# NexusOps AI & VyaparShield — Product Requirements Document (PRD)

**Document Version:** 1.0.0  
**Phase:** A0.1 — Scope, Requirements, and Acceptance Criteria  
**Status:** Approved Specification  

---

## 1. Executive Summary & Product Objective

**NexusOps AI** is a unified operational intelligence platform combining applied AI/ML, GenAI, Agentic AI, robust backend engineering, AI security (AgentGuard / PromptShield), DevOps, and SRE.

The V1 release targets two tightly coupled operational domains:
1. **VyaparShield (Flagship Domain):** An intelligent, evidence-grounded financial intelligence and invoice-to-cash platform tailored for Indian MSMEs (Micro, Small, and Medium Enterprises). It solves cash-flow blindness, complex invoice/payment reconciliation, overdue receivables, and unexplainable discrepancies.
2. **AegisOps (Operational SRE Domain):** A bounded incident investigation service that correlates operational telemetry (metrics, logs, traces) to rank root-cause hypotheses and recommend safe, policy-gated remediations.
3. **AgentGuard & PromptShield (Cross-Cutting AI Governance):** Server-side policy enforcement, tool allowlists, prompt-injection defense, and human-in-the-loop approval gates.

---

## 2. Target Users, Roles & Permissions (RBAC)

The system enforces multi-tenant isolation where each business organization has its own strictly segregated data partition.

| Role | Responsibilities | Permitted Actions | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **Business Owner** | Executive oversight, strategic cash management, approval of high-value actions. | Full read access to financial dashboards, analytics, and audit logs; approve/reject actions (e.g., sending collection notices, ledger write-offs). | Cannot bypass security gates; cannot directly modify database records. |
| **Finance User / Accountant** | Day-to-day invoice uploading, payment entries, and reconciliation management. | Upload documents (CSV/XLSX/PDF), trigger OCR/parsing, initiate reconciliation runs, confirm suggested matches, query the finance analyst assistant. | Cannot approve external customer communications or balance write-offs; cannot access other tenants. |
| **Reviewer / Auditor** | Exception resolution and compliance auditing. | Review OCR low-confidence fields, inspect reconciliation residuals, view system audit logs and model run metadata. | Cannot alter raw invoice data without an audit event; cannot approve financial write-offs. |
| **Admin** | System configuration and user lifecycle management. | Manage organization members, view system health and error budgets, configure integrations. | Cannot view unmasked financial transaction payloads without audit logging. |

---

## 3. Core Business Scenario: Indian MSME Invoice-to-Cash Workflow

The end-to-end V1 user story follows a real-world Indian MSME operational flow:

```
[Upload Documents & Statements]
           │
           ▼
[Validation, Classification & OCR Extraction]
           │
           ▼
[Deterministic Invariant Verification & Storage]
           │
           ▼
[Reconciliation Engine (Exact Match -> Ranked Fuzzy)]
           │
           ▼
[Cash Flow Projections & Anomaly Detection]
           │
           ▼
[Natural Language Finance Analyst (Authorized RAG)]
           │
           ▼
[Agent-Assisted Collection Draft & Human Approval]
           │
           ▼
[Execution, Outcome Tracking & Audit Logging]
```

### Specific India-Focused Nuances & Edge Cases
1. **Goods & Services Tax (GST):**
   - Extraction and validation of 15-character alphanumeric **GSTIN** (e.g., `27AAAAA0000A1Z5` with state code, PAN, entity number, checksum).
   - Segregation of tax components: Central GST (**CGST**), State GST (**SGST**), and Integrated GST (**IGST**).
   - Reverse Charge Mechanism (RCM) flags.
2. **Indian Banking & Payment Narrations:**
   - Normalization of bank transaction narrations containing ambiguous references:
     - **UPI:** `UPI/412345678901/PAYMENT TO ACME/BARB0...`
     - **NEFT/RTGS:** `NEFT-N123456789012-ABC TRADERS-HDFC0000123...`
     - **IMPS:** `IMPS/P2A/412312345678/VendorName/...`
   - Matching payer aliases when bank names do not match vendor invoice names (e.g., invoice from "Sharma Enterprises", payment from "Sharma Textiles Private Limited").
3. **Financial Discrepancies & Residuals:**
   - **Tax Deducted at Source (TDS):** Payments short by standard rates (e.g., 1%, 2%, 10% under Sections 194C, 194J) must be automatically detected rather than marked as an unexplained short payment.
   - **Bank Gateway / IMPS Charges:** Discrepancies of ₹5–₹25 caused by payment gateway processing deductions.
   - **Cash Discounts & Round-Offs:** Cash settlement discounts (e.g., 2% for 10-day payment) and paise round-offs (fractional rupee differences).
4. **Complex Settlement Topologies:**
   - **One-to-Many:** One bulk payment settling multiple pending invoices from a single buyer.
   - **Many-to-One:** An invoice paid in multiple partial installments over several weeks.
   - **Delayed References:** Customer payment received days before the invoice is physically logged in the system.

---

## 4. Strict Financial Invariants

To guarantee production-grade accounting integrity and eliminate AI hallucination risks, the platform enforces the following system-wide rules:

1. **Decimal-Safe Currency Arithmetic:**
   - All monetary values MUST use fixed-point arithmetic (`decimal.Decimal` in Python, `NUMERIC(18, 4)` in PostgreSQL).
   - Floating-point types (`float`, `double`) are strictly prohibited in the financial calculation pipeline.
   - Rounding must be explicit, consistent, and adhere to standard half-up or bankers' rounding (`ROUND_HALF_UP` / `ROUND_HALF_EVEN`).
2. **Balanced Double-Entry / Event Sourcing:**
   - Every financial state change is accompanied by an immutable `ledger_event`.
   - Money cannot be created or deleted in the reconciliation process: Total Invoice Amount = Total Paid + Deductions (TDS/Discounts) + Outstanding Balance.
3. **Prohibition of Double Application:**
   - A single payment transaction or fraction thereof cannot be allocated more than once. The system maintains an atomic allocated amount constraint (`allocated_amount <= total_amount`).
4. **No LLM Mental Math:**
   - LLMs and AI agents are **STRICTLY PROHIBITED** from computing financial totals, balances, or reconciliation matches internally.
   - All arithmetic, aging buckets, and reconciliation rankings are calculated by deterministic Python services. The LLM only receives verified computation payloads to explain and summarize.
5. **Immutable Financial History:**
   - Historical invoice and payment records are append-only. Adjustments or reversals generate explicit compensating transactions with linked audit references.

---

## 5. Non-Functional Requirements (NFRs)

### Performance & Latency Targets (Initial SLOs)
- **API Response Time (p95):** `< 200 ms` for standard CRUD and filtered financial listings.
- **Invoice Parsing & OCR Extraction:** `< 5 seconds` per single-page invoice; asynchronous background queue for multi-page documents.
- **Reconciliation Engine Execution:** `< 2 seconds` for 1,000 candidate records.
- **Finance Analyst RAG Response Time (p95):** `< 3.5 seconds` end-to-end including tool retrieval and grounded generation.

### Security & Compliance
- **Tenant Isolation:** Every SQL query and vector retrieval MUST include `tenant_id` filtering enforced at the service and data layer.
- **Least-Privilege Tool Execution:** Agents can only invoke allowlisted, typed functions.
- **Audit Logging:** Every mutating API call, policy decision, approval, and rejected prompt injection attempt is written to an immutable audit table.
- **Secret Redaction:** PII and credentials (API keys, account numbers) are sanitized before writing to logs, traces, or LLM context windows.

---

## 6. Phase Exit Criteria (Acceptance Gate for Phase A0.1)

1. [x] Every V1 feature has a clear purpose, dependency map, and testable exit condition.
2. [x] Indian MSME financial invariants and edge cases are formally documented.
3. [x] User roles, permissions, and tenant isolation boundaries are explicitly defined.
4. [x] Threat model and Architecture Decision Records (ADRs) are authored and cross-referenced.
