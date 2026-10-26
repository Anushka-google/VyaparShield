# ADR-001: Modular Monolith with Asynchronous Workers Architecture

**Status:** Accepted  
**Date:** 2026-10-25  
**Deciders:** Core Engineering Team  
**Context:** NexusOps AI Architecture Strategy  

---

## Context and Problem Statement
Large enterprise AI and DevOps projects often fail or stall during development due to premature distributed microservices overhead (distributed transactions, network partitioning, complex deployments, multiple CI/CD pipelines, and multi-repo coordination). 

NexusOps AI requires multi-tenant financial data management (VyaparShield), telemetry and incident investigation (AegisOps), and autonomous agent coordination (AgentGuard). We need an architectural design that ensures rapid development, clean separation of concerns, strict transactional data consistency, and high operational reliability without unnecessary infrastructure complexity.

## Considered Options
1. **Full Distributed Microservices:** Independent services for Auth, Ingestion, Finance, SRE Incidents, and Agent Governance communicating over gRPC/HTTP/Kafka.
2. **Standard Unstructured Monolith:** A single code base with shared models and circular dependencies across domains.
3. **Modular Monolith + Asynchronous Workers (Chosen):** A single deployable codebase organized into strict domain modules (`modules/finance/`, `modules/incidents/`, `modules/ai_security/`, `shared/`) with isolated database schemas/interfaces, backed by asynchronous Redis workers (`workers/`) for long-running tasks.

## Decision
We choose the **Modular Monolith + Asynchronous Workers** architecture using **FastAPI, SQLAlchemy 2.0, PostgreSQL, and Redis/Celery**.

### Architectural Rules
- Domain modules must only communicate via defined public Python service interfaces or shared events, never by directly mutating another module's internal models.
- HTTP API requests must complete in sub-second time. Any task exceeding 200ms (document OCR, file parsing, ML inference, vector embedding generation, external notifications) MUST be dispatched to asynchronous workers via Redis.
- The monorepo houses backend, frontend, ML, workers, infrastructure, and tests.

## Consequences
### Positive
- **Single Deployment Target:** Local development runs seamlessly via a single `docker-compose.yml` or native terminal commands.
- **ACID Transactions:** Full database transactional guarantees across invoices, payments, and ledger events without distributed 2-phase commit protocols.
- **High Developer Velocity:** Shared typing (Pydantic), common test suites, and unified CI pipelines.
- **Easy Future Decomposition:** If a specific module (e.g., OCR document extraction) requires independent scaling or GPU acceleration in Phase B, it can be easily extracted into a standalone service without refactoring business logic.

### Negative / Trade-offs
- Requires discipline to prevent developers from bypassing domain interfaces and writing direct cross-module database joins.
- Heavy background jobs share the core application codebase, requiring container image layering.

## Revisit Conditions
We will consider decomposing into standalone microservices only if:
1. Continuous operational metrics in Phase A8 show that a single domain component (e.g., OCR or ML serving) creates an unresolvable resource bottleneck that vertical scaling and separate worker containers cannot resolve.
2. Independent deployment frequency or regulatory compliance necessitates distinct isolated infrastructure for security boundaries.
