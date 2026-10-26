# NexusOps AI — Acceptance Checklist & Quality Gates

**Document Version:** 1.0.0  
**Phase:** A0.1 — Master Tracking & Quality Assurance  
**Verification Policy:** Evidence-driven release. No feature is marked complete without automated tests or benchmark proof.

---

## Master Phase Acceptance Gates

### Phase A0 — Scope, Architecture & Monorepo Setup
- [x] **A0.1:** PRD with Indian MSME workflows, GST rules, and financial invariants (`docs/requirements.md`).
- [x] **A0.1:** AI security threat model, trust boundaries, and AgentGuard specs (`docs/threat_model.md`).
- [x] **A0.1:** 5 Architecture Decision Records authored (`docs/adr/ADR-001` through `ADR-005`).
- [x] **A0.1:** Visual system architecture and sequence diagrams in Mermaid (`docs/architecture.md`).
- [x] **A0.1:** Multi-tenant PostgreSQL data dictionary and entity catalog (`docs/data_dictionary.md`).
- [ ] **A0.2:** Monorepo directory skeleton established (`frontend`, `backend`, `ml`, `workers`, `infrastructure`, `tests`).
- [ ] **A0.2:** Configuration files created (`.gitignore`, `.env.example`, `docker-compose.yml`).
- [ ] **A0.2:** CI workflow configured (`.github/workflows/ci.yml`) for linting, typing, and tests.
- [ ] **A0.2:** Master root `README.md` with architecture and quickstart commands.

---

### Phase A1 — Frontend/Backend Foundation & Tenant Isolation
- [ ] **A1.1:** React + TypeScript + Tailwind CSS dashboard shell with navigation, role-aware routing, and Indian Rupee formatting (`₹`).
- [ ] **A1.1:** Accessible Recharts dashboard with loading, empty, and error states.
- [ ] **A1.2:** FastAPI application initialized with versioned routes (`/api/v1`) and `/healthz`, `/readyz` probes.
- [ ] **A1.2:** SQLAlchemy 2.0 async engine and Alembic migration scripts for all core entities.
- [ ] **A1.3:** JWT authentication, RBAC authorization (`owner`, `finance`, `reviewer`, `admin`), and tenant-scoping middleware.
- [ ] **A1.3 Gate:** 100% pass rate on cross-tenant negative access tests (IDOR prevention).

---

### Phase A2 — Ingestion & Background Job Processing
- [ ] **A2.1:** Multi-format ingestion service for CSV, XLSX, and JSON statements.
- [ ] **A2.1:** File hash deduplication (SHA-256) and idempotent import verification.
- [ ] **A2.2:** Invoice PDF parsing and OCR extraction (GSTIN, dates, line items, totals).
- [ ] **A2.2:** Extraction confidence scoring and human correction review queue for uncertain fields.
- [ ] **A2.3:** Redis + Celery / RQ background worker pipeline with bounded retries, exponential backoff, and dead-letter queue (DLQ).
- [ ] **A2.3 Gate:** Worker restart or repeated job delivery does not corrupt data or duplicate records.

---

### Phase A3 — Deterministic Finance Engine & Anomaly Rules
- [ ] **A3.1:** Authoritative invoice receivables engine, overdue aging buckets (0–30, 31–60, 61–90, 90+ days).
- [ ] **A3.2:** Tiered reconciliation cascade:
  - Exact deterministic matching.
  - Bank narration parsing (UPI / NEFT / IMPS) & alias resolution.
  - Automatic detection of statutory TDS (194C, 194J), bank gateway fees, and paise round-offs.
  - Multi-invoice settlement (one-to-many) and installment payments (many-to-one).
- [ ] **A3.2:** Reversal and correction support with immutable ledger event tracking.
- [ ] **A3.3:** Explainable anomaly triage (unusual amounts, duplicate invoices, refund spikes).
- [ ] **A3.3:** SMTP notification integration with rate limits, delivery audits, and idempotency.
- [ ] **A3.3 Gate:** Precision/recall metrics reported on synthetic benchmark dataset; zero floating-point arithmetic errors.

---

### Phase A4 — Domain ML & Model Lifecycle
- [ ] **A4.1:** Reproducible tabular feature engineering pipeline with strict chronological/time-aware train-test splits.
- [ ] **A4.2:** Baseline model vs. Gradient-Boosted Candidate (XGBoost/LightGBM) for overdue-payment risk.
- [ ] **A4.2:** Cash-flow forecasting scenarios (best, base, worst with uncertainty intervals).
- [ ] **A4.2:** Model experiment tracking via MLflow (parameters, metrics, model artifacts).
- [ ] **A4.3:** Model serving endpoint integrated into FastAPI with model version metadata and data sufficiency warnings.
- [ ] **A4.3 Gate:** Candidate model demonstrates measurable lift over baseline on held-out test data.

---

### Phase A5 — GenAI, Authorized RAG & Finance Analyst
- [ ] **A5.1:** Tenant-scoped document chunking and vector embeddings using PostgreSQL `pgvector`.
- [ ] **A5.2:** Natural language finance analyst with typed read-only backend tools.
- [ ] **A5.2:** Zero mental math by LLM—all totals and drivers queried directly from deterministic services.
- [ ] **A5.2:** Strict source citation format (`[Invoice #INV-102]`, `[Payment #PAY-501]`) with missing-data refusal.
- [ ] **A5.3:** 50–100 question evaluation test suite measuring answer correctness, citation faithfulness, and latency.
- [ ] **A5.3 Gate:** 100% pass rate on adversarial indirect prompt injection and cross-tenant retrieval attempts.

---

### Phase A6 — Telemetry, Incident Triage & Observability (AegisOps)
- [ ] **A6.1:** Simulated microservice test harness emitting metrics, structured JSON logs, and deployment events.
- [ ] **A6.2:** Anomaly detection service grouping alerts into correlated incidents with timeline visualizations.
- [ ] **A6.3:** Incident investigation assistant with runbook RAG and ranked root-cause hypotheses.
- [ ] **A6.3 Gate:** OpenTelemetry distributed trace linking API request, Celery worker, OCR, and DB query with sensitive PII redacted.

---

### Phase A7 — Stateful Agent Workflow & AgentGuard Governance
- [ ] **A7.1:** Durable state machine / LangGraph workflow with persisted state checkpoints and pause/resume capability.
- [ ] **A7.2:** Server-side deny-by-default policy gate for all agent tool invocations.
- [ ] **A7.2:** Human-in-the-Loop (HITL) approval gate for high-impact actions (collection emails, ledger adjustments).
- [ ] **A7.2:** Postcondition verification testing actual system state delta post-execution.
- [ ] **A7.3 Gate:** Unapproved actions never execute; unauthorized tool calls remain blocked regardless of model output.

---

### Phase A8 — Containerization, CI/CD, Cloud & SRE Handover
- [ ] **A8.1:** Multi-stage Dockerfiles for backend, frontend, and workers; Docker Compose for local development.
- [ ] **A8.1:** GitHub Actions CI/CD with linting, typing, pytest, security dependency scanning, and container builds.
- [ ] **A8.2:** Terraform infrastructure as code (IaC) for AWS deployment (VM / ECS, RDS, S3).
- [ ] **A8.3:** Prometheus metrics and Grafana operational dashboards; SLIs/SLOs defined with error-budget tracking.
- [ ] **A8.3:** Database backup/restore drill and automated rollback verification.
- [ ] **A8.4 Gate:** Final portfolio evidence bundle compiled (architecture docs, benchmark reports, demo video script, verifiable resume bullets).
