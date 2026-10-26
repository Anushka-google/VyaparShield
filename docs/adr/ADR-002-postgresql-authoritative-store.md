# ADR-002: PostgreSQL as the Single Authoritative Data Store & Vector Engine

**Status:** Accepted  
**Date:** 2026-10-25  
**Deciders:** Core Engineering Team  
**Context:** NexusOps AI Persistence Strategy  

---

## Context and Problem Statement
NexusOps AI requires persistence for:
1. Strict relational financial records (organizations, users, customers, invoices, payments, reconciliations, immutable ledger events).
2. Asynchronous job metadata and state machine checkpoints.
3. Audit trails and security policy events.
4. Document text chunks and high-dimensional semantic embeddings for authorized RAG retrieval.

Using separate specialized databases (e.g., Pinecone/Milvus for vectors, MongoDB for documents, PostgreSQL for relational data) introduces significant distributed system problems:
- **Dual-write consistency failures:** An invoice might be deleted in the relational DB but still return in vector search results.
- **Tenant isolation complexity:** Enforcing unified RBAC and `tenant_id` filtering across disparate databases is prone to IDOR leaks.
- **Operational overhead:** Managing 3+ separate data services locally and in cloud infrastructure.

## Considered Options
1. **Polyglot Persistence:** PostgreSQL (Relational) + Pinecone/Qdrant (Vector DB) + DynamoDB (Job States).
2. **PostgreSQL 16 with `pgvector` & Object Storage (Chosen):** PostgreSQL as the single relational and vector store, backed by S3/MinIO (or local filesystem in dev) for binary raw files (PDFs/scans).

## Decision
We select **PostgreSQL 16 with the `pgvector` extension** as the single authoritative database for all structured business entities, audit logs, and embedding vectors.

### Architectural Rules
- All tables must include a `tenant_id UUID` foreign key column with composite indices (`(tenant_id, id)`).
- Raw PDF/image assets are stored in object storage (MinIO / S3); PostgreSQL only stores the document metadata, storage URI, extracted text, and chunks.
- Vector search queries MUST always include a relational `WHERE tenant_id = :current_tenant` pre-filter to prevent cross-tenant vector retrieval.
- Database schema migrations are strictly managed via versioned **Alembic** migration scripts.

## Consequences
### Positive
- **Guaranteed Consistency:** Relational updates and vector embeddings can be committed within the exact same database transaction.
- **Unified Tenant Security:** Standard SQL filters enforce tenant boundaries across both structured data and semantic embeddings.
- **Hybrid Search Capability:** Enables unified SQL queries combining keyword search (`tsvector`), metadata filters (`due_date`, `status`), and cosine vector distance (`<->`).
- **Simplified DevOps:** A single database container to backup, replicate, monitor, and restore.

### Negative / Trade-offs
- Dedicated vector databases (e.g., Milvus, Qdrant) can offer higher throughput at massive scale (100M+ vectors). 
- Database connection pooling (via PgBouncer or SQLAlchemy async pool) must be properly configured to prevent connection exhaustion.

## Revisit Conditions
We will evaluate a dedicated vector database or graph store only if:
1. Benchmark testing in Phase B shows vector index search latency on pgvector exceeds SLO targets (`> 150ms`) under realistic multi-tenant vector volume (`> 1,000,000` chunks).
2. Complex multi-hop graph queries (GraphRAG in Phase B4) cannot be performed efficiently via recursive Common Table Expressions (CTEs) or PostgreSQL relational graphs.
