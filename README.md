# NexusOps AI — Unified Operational Intelligence Platform

[![NexusOps CI](https://github.com/nexusops-ai/nexusops/actions/workflows/ci.yml/badge.svg)](https://github.com/nexusops-ai/nexusops/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-emerald.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-cyan.svg)](https://react.dev/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://github.com/pgvector/pgvector)

**NexusOps AI** is a production-grade, enterprise operational intelligence platform combining **Applied AI/ML, GenAI, Agentic AI, AI Security, and DevSecOps**.

---

## 🏛️ System Domains

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                       NexusOps AI                        │
                               └────────────────────────────┬─────────────────────────────┘
                                                            │
                 ┌──────────────────────────────────────────┼──────────────────────────────────────────┐
                 ▼                                          ▼                                          ▼
     ┌───────────────────────┐                  ┌───────────────────────┐                  ┌───────────────────────┐
     │     VyaparShield      │                  │       AegisOps        │                  │      AgentGuard       │
     │ (Financial Intel)     │                  │ (Incident Operations) │                  │  (AI Safety Policy)   │
     ├───────────────────────┤                  ├───────────────────────┤                  ├───────────────────────┤
     │ • Indian MSME Cash    │                  │ • Simulated Telemetry │                  │ • Deny-By-Default     │
     │ • GST & Invoices      │                  │ • Anomaly Correlation │                  │ • Server-Side Gate    │
     │ • UPI/NEFT Reconcile  │                  │ • Runbook RAG         │                  │ • HITL Human Approval │
     │ • Grounded AI Analyst │                  │ • Policy Remediation  │                  │ • Postcondition Audit │
     └───────────────────────┘                  └───────────────────────┘                  └───────────────────────┘
```

1. **VyaparShield (Flagship MSME Domain):** Solves cash-flow blindness, overdue receivables, and reconciliation complexity for Indian MSMEs with strict financial invariants (decimal-safe money, balanced ledgers, and zero LLM mental math).
2. **AegisOps (Incident Operations & SRE):** Autonomous incident triage correlating telemetry anomalies, matching approved runbooks, and generating evidence-backed hypotheses.
3. **AgentGuard & PromptShield (Governance & Safety):** Enforces server-side authorization allowlists, indirect prompt-injection sanitization, and human-in-the-loop approval gates for all consequential actions.

---

## 📁 Repository Architecture

```text
nexusops-ai/
├── backend/                  # FastAPI REST API & Core Services
│   ├── app/
│   │   ├── api/v1/           # Versioned API routes
│   │   ├── business_rules/   # Deterministic financial & accounting rules
│   │   ├── modules/          # Isolated domain modules (finance, incidents, security)
│   │   ├── models/           # SQLAlchemy 2.0 database entities
│   │   └── core/             # Pydantic Settings & Auth configuration
│   └── Dockerfile
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/       # Reusable UI widgets & Recharts dashboards
│   │   └── modules/          # Domain views (VyaparShield, AegisOps, Approvals)
│   └── Dockerfile
├── ml/                       # Machine Learning & Feature Engineering
│   ├── features/             # Chronological feature stores
│   ├── training/             # XGBoost/LightGBM vs simple baseline
│   └── evaluation/           # Backtests, lift analysis, and drift detection
├── workers/                  # Asynchronous task workers (Celery + Redis)
│   ├── document_worker.py    # Invoice parsing & OCR extraction
│   └── workflow_worker.py    # Stateful agent execution
├── infrastructure/           # Docker, Terraform IaC, Prometheus/Grafana configs
├── tests/                    # Test suites (unit, integration, security, e2e)
├── docs/                     # Architecture & Governance Documentation
│   ├── adr/                  # Architecture Decision Records (ADR-001 to ADR-005)
│   ├── requirements.md       # Product Requirements & Indian MSME specs
│   ├── threat_model.md       # Threat analysis & prompt-injection mitigations
│   ├── data_dictionary.md    # PostgreSQL schema catalog
│   └── acceptance_checklist.md # Measurable quality gates
├── docker-compose.yml        # Multi-container local orchestration
└── .env.example              # Environment variables template
```

---

## 🚀 Quickstart

### Prerequisites
- [Docker Desktop](https://www.docker.com/) (recommended) **OR** Python 3.12+ and Node.js 20+

### 1. Using Docker Compose (Single Command)
```bash
# Clone the repository
git clone https://github.com/nexusops-ai/nexusops.git
cd nexusops

# Copy environment variables
cp .env.example .env

# Start all services (PostgreSQL + pgvector, Redis, Backend, Worker, Frontend)
docker compose up -d --build
```
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Probe:** [http://localhost:8000/healthz](http://localhost:8000/healthz)

### 2. Native Local Development Setup

#### Backend:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

#### Run Unit Tests:
```bash
pytest tests/unit -v
```

---

## 📚 Key Architectural Documents
- [Product Requirements & MSME Specs](docs/requirements.md)
- [Threat Model & AgentGuard Defense](docs/threat_model.md)
- [System Architecture & Visual Diagrams](docs/architecture.md)
- [Data Dictionary & PostgreSQL Schema](docs/data_dictionary.md)
- [Acceptance Quality Gates](docs/acceptance_checklist.md)
- [ADR Index](docs/adr/)
  - [ADR-001: Modular Monolith + Async Workers](docs/adr/ADR-001-modular-monolith.md)
  - [ADR-002: PostgreSQL as Authoritative Store & pgvector](docs/adr/ADR-002-postgresql-authoritative-store.md)
  - [ADR-003: Deterministic Accounting over LLM Math](docs/adr/ADR-003-deterministic-business-arithmetic.md)
  - [ADR-004: AgentGuard Policy Engine & HITL Approvals](docs/adr/ADR-004-agentguard-policy-and-approval-gate.md)
  - [ADR-005: Deferral Strategy for Complex Infrastructure](docs/adr/ADR-005-deferred-technologies.md)

---

## 🎯 Master Roadmap Progress

- [x] **Phase A0 — Scope, Architecture, ADRs & Monorepo Setup** (Complete)
- [ ] **Phase A1 — Shared Foundation, Data Model & Tenant Security** (Next)
- [ ] **Phase A2 — Ingestion, Document Intelligence & Background Tasks**
- [ ] **Phase A3 — Deterministic Finance Engine & Anomaly Triage**
- [ ] **Phase A4 — Domain ML & Forecasting Lifecycle**
- [ ] **Phase A5 — Authorized RAG, GenAI & Grounded Assistant**
- [ ] **Phase A6 — Cross-Domain Telemetry & Observability**
- [ ] **Phase A7 — Stateful Agent Workflows & Security Gate**
- [ ] **Phase A8 — Production Hardening, CI/CD & V1 Release**
- [ ] **Roadmap B — Advanced Capabilities (V2+)**
