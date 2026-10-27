# VyaparShield — Initial Test Plan & Out-of-Scope Registry

**Phase:** Phase 0 — Quality Assurance Strategy & Scope Boundary Enforcement  
**Test Framework:** Pytest + pytest-asyncio + FastAPI TestClient  

---

## 1. Test Matrix & Acceptance Gates

### 1.1 Financial Invariant Tests (`tests/unit/test_invariants.py`)
| Test ID | Test Scenario | Input Data | Expected Output / Assertion |
| :--- | :--- | :--- | :--- |
| `INV-01` | Decimal arithmetic precision | Quantity: `3`, Unit Price: `33.3333`, Tax: `18%` | Subtotal: `100.00`, Tax: `18.00`, Total: `118.00` (Exact `Decimal` check, no float drift). |
| `INV-02` | Round-off handling | Amounts ending in fractional paise (e.g. `₹100.005`) | Quantized to `100.01` via `ROUND_HALF_UP`. |
| `INV-03` | Non-negative invoice balance | Invoice Total: `₹10,000`, Attempted Allocation: `₹12,000` | HTTP 422 Unprocessable Entity / Constraint violation; balance remains `₹10,000`. |
| `INV-04` | Payment conservation | Payment: `₹50,000`, Allocation 1: `₹30,000`, Allocation 2: `₹25,000` | Allocation 2 rejected; `unallocated_amount` cannot drop below `0`. |
| `INV-05` | Statutory TDS Detection | Invoice: `₹1,00,000`, Payment: `₹98,000`, Narration contains vendor name | Reconciled with `allocated_amount = 98000.00`, `tds_deducted = 2000.00` (Section 194C 2%). |

### 1.2 Tenant Isolation & Security Negative Tests (`tests/security/test_tenant_isolation.py`)
| Test ID | Test Scenario | Attack Simulation | Expected Result |
| :--- | :--- | :--- | :--- |
| `SEC-01` | Cross-Tenant Invoice Fetch | User in Tenant A sends `GET /api/v1/invoices/{id_from_tenant_b}` | HTTP 404 Not Found (or 403 Forbidden). No leakage of existence. |
| `SEC-02` | Cross-Tenant Payment Allocation | User in Tenant A attempts to allocate Tenant A's payment to Tenant B's invoice | HTTP 404 / 403. Transaction aborted. |
| `SEC-03` | Unauthenticated Mutation | Request to `POST /api/v1/invoices` without Bearer JWT | HTTP 401 Unauthorized. |
| `SEC-04` | Non-Existent Customer Foreign Key | Create invoice with random UUID for `customer_id` | HTTP 404 Customer Not Found or DB ForeignKeyViolation. |

---

## 2. Explicit Out-of-Scope Registry for V1

To prevent scope creep and guarantee that the V1 release is independently useful and rock-solid, the following capabilities are **EXPLICITLY OUT OF SCOPE** for V1:

| Excluded Capability | Why Deferred | Where Re-evaluated |
| :--- | :--- | :--- |
| **Autonomous Live Bank Debits / Payouts** | High financial & liability risk. V1 provides payment reconciliation and drafts reminders; it does NOT execute real money transfers from the bank. | Roadmap B (after banking partner APIs & regulatory licenses). |
| **Direct Tally / SAP Direct DB Connectors** | Proprietary ERP wire protocols add massive fragile dependencies. V1 accepts standard CSV, Excel (XLSX), and PDF exports. | Phase B1 (SupplySense / ERP connectors). |
| **Autonomous Unsupervised Customer Reminder Sending** | Risk of damaging customer relationships if an agent sends an incorrect aggressive notice. Every collection notice requires **Human-in-the-Loop Approval**. | Core safety rule (never automated without approval). |
| **Distributed Microservices & Kubernetes** | Monolith + Celery workers is faster to build, test, deploy, and benchmark. K8s introduces unneeded ops overhead. | Phase B5 (if throughput metrics justify it). |
| **Self-Hosted LLM Fine-Tuning** | Requires expensive GPU infrastructure and 1,000+ curated domain examples. In-context learning and RAG achieve high accuracy at lower cost. | Phase B4 (when sufficient reviewed correction data exists). |

---

## 3. Exit Gate Criteria for Phase 0

- [x] All 3 roles (`owner`, `accountant`, `admin`) defined with concrete permissions.
- [x] Full MSME user stories and edge cases specified.
- [x] Database ER diagram and relational constraints documented.
- [x] Typed REST API contracts drafted.
- [x] Financial invariants (Decimal, GST, TDS, conservation of funds) mathematically specified.
- [x] Realistic Indian MSME synthetic datasets created.
- [x] Explicit out-of-scope boundaries defined.
