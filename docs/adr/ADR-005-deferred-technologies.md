# ADR-005: Deferral Strategy for Advanced Infrastructure and Orchestration

**Status:** Accepted  
**Date:** 2026-10-25  
**Deciders:** Core Engineering Team  
**Context:** Technology Selection & Complexity Management  

---

## Context and Problem Statement
Modern AI and DevOps projects frequently suffer from "resume-driven development", where teams integrate complex distributed tools (Kubernetes, Kafka, GraphRAG, vLLM, model fine-tuning, and complex multi-agent frameworks) before having a single reliable, working vertical slice.

Premature adoption of these technologies introduces high operational friction, costly cloud infrastructure bills, difficult local reproduction for evaluators, and debugging complexity that distracts from core business and AI reliability.

## Considered Options
1. **Kitchen-Sink Architecture:** Build V1 with Kubernetes, Kafka event streaming, Neo4j GraphRAG, self-hosted vLLM inference on GPU instances, and a 5-agent swarm from Day 1.
2. **Evidence-Driven Progressive Adoption (Chosen):** Implement V1 with a lean, highly dependable stack (Docker Compose, Redis, PostgreSQL + pgvector, hosted/local LLM APIs, single bounded state machine). Explicitly defer advanced technologies to Roadmap B (V2+) until empirical measurements, benchmark failures, or workload scale demand them.

## Decision
We formally defer the following technologies for Phase A (V1) and establish empirical triggers for their introduction in Phase B (V2+):

### 1. Kafka → Deferred in favor of Redis Queue
- **Current Choice:** Redis + Celery / RQ.
- **Why Deferred:** Redis handles thousands of background jobs per second with sub-millisecond dispatch and minimal memory footprint.
- **Adoption Trigger for Kafka (Phase B5):** Introduce Kafka only if event volume exceeds 10,000 events/second, or when multiple independent microservices require event replay and persistent log retention.

### 2. Kubernetes + Helm → Deferred in favor of Docker & Terraform (VM / Container Service)
- **Current Choice:** Docker, Docker Compose (local dev), Terraform + AWS VM / ECS.
- **Why Deferred:** Kubernetes introduces massive setup overhead (control plane, ingress controllers, CNI, storage classes) that offers zero benefit for a single modular monolith.
- **Adoption Trigger for Kubernetes (Phase B5):** Introduce Kubernetes only if multi-service autoscaling, cluster-level zero-downtime rolling canary deployments, or multi-cloud workload portability is empirically required.

### 3. GraphRAG / Knowledge Graphs → Deferred in favor of Hybrid Search (pgvector + tsvector)
- **Current Choice:** PostgreSQL 16 with `pgvector` and full-text keyword indexing (`tsvector`).
- **Why Deferred:** Graph databases (Neo4j) add significant schema maintenance and entity-extraction pipeline failure points.
- **Adoption Trigger for GraphRAG (Phase B4):** Introduce GraphRAG only if evaluation benchmarks on 100+ relationship-heavy questions (e.g., multi-tier supplier-to-subcontractor fraud loops) demonstrate that hybrid search fails to retrieve required evidence.

### 4. Self-Hosted vLLM / Fine-Tuning → Deferred in favor of API & In-Context Grounding
- **Current Choice:** Managed LLM APIs (or lightweight local Ollama for development) with RAG and structured tool calling.
- **Why Deferred:** Fine-tuning and self-hosted vLLM require high-cost GPU infrastructure and ongoing model drift management. Prompt engineering and RAG solve 95% of factual financial grounding needs.
- **Adoption Trigger for vLLM / LoRA (Phase B4):** Introduce fine-tuning only when a specific extraction or reasoning task has 1,000+ curated domain examples and prompt/RAG techniques leave a measurable, repeatable quality gap.

### 5. Multi-Agent Swarms → Deferred in favor of Bounded Single-Agent State Machine
- **Current Choice:** Python state machine (or LangGraph) with explicit checkpoints and human approval.
- **Why Deferred:** Unconstrained multi-agent swarms suffer from message looping, high token costs, coordination overhead, and unpredictable failure recovery.
- **Adoption Trigger for Multi-Agent (Phase B3):** Introduce a multi-agent topology only when distinct specialist roles (e.g., an independent Adversarial Auditor checking an Investigator's work) have conflicting objectives that cannot be encapsulated in a single state machine.

## Consequences
### Positive
- **Guaranteed Fast Delivery:** Development focuses on core business logic, financial invariants, and security gates rather than infrastructure maintenance.
- **Reproducible for Anyone:** A reviewer or evaluator can clone the repository and run the entire platform with one `docker compose up` command.
- **Strong Interview Narrative:** Demonstrates maturity, architectural restraint, and cost-conscious engineering judgment.

## Revisit Conditions
Each deferred technology will be revisited during Phase B planning with an empirical evaluation report comparing the existing baseline against the proposed tool.
