# NexusOps AI — End-to-End System Architecture

**Document Version:** 1.0.0  
**Phase:** A0.1 — System Design & Visual Architecture  
**Status:** Approved Specification  

---

## 1. High-Level System Architecture

NexusOps AI is architected as a **Modular Monolith with Asynchronous Task Workers**. It delivers real-time HTTP operations via FastAPI, heavy document extraction and ML inference via asynchronous Redis/Celery workers, and stores authoritative financial state and vector embeddings in PostgreSQL 16.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & User Layer"]
        UI["React 18 + TypeScript + Tailwind CSS\n(Recharts Dashboards & HITL Approval Modal)"]
    end

    subgraph IngressSecurity ["Ingress & Auth Boundary"]
        Proxy["Reverse Proxy / TLS Termination"]
        AuthFilter["Tenant-Scoped Auth (JWT/Session)\nRBAC Role Check"]
    end

    subgraph CoreBackend ["FastAPI Modular Monolith"]
        API["REST API Router (/api/v1)"]
        
        subgraph DomainModules ["Domain Modules"]
            VS["VyaparShield\n(Finance, Invoices, Reconciliation)"]
            AO["AegisOps\n(Telemetry, Incidents, Runbooks)"]
            AG["AgentGuard & PromptShield\n(Policy Gate & HITL Approvals)"]
        end

        DRules["Deterministic Financial Invariant Engine\n(Fixed-Point Decimal Math, Balanced Ledgers)"]
        Audit["Immutable Audit Logger"]
    end

    subgraph AsyncWorkerLayer ["Asynchronous Processing Layer"]
        RQueue[("Redis Message Broker & Result Backend")]
        W1["Document / OCR Worker\n(PyMuPDF, Tesseract/EasyOCR)"]
        W2["ML & Forecasting Worker\n(XGBoost / Statsmodels)"]
        W3["Agent Workflow Worker\n(LangGraph / State Machine)"]
    end

    subgraph StorageLayer ["Persistence & Object Storage"]
        PG[("PostgreSQL 16 (Authoritative Store)\n• Relational Tables\n• pgvector Embeddings\n• Ledger Events & Audit Logs")]
        S3[("Object Storage (S3 / MinIO)\n• Raw Invoices, Scans, Reports")]
    end

    subgraph ExternalServices ["External Providers"]
        LLM["LLM Provider (OpenAI / Gemini / Claude / Ollama)"]
        SMTP["SMTP / Email Gateway (Notifications)"]
    end

    %% Connections
    UI <-->|HTTPS / REST| Proxy
    Proxy --> AuthFilter
    AuthFilter --> API
    API --> DomainModules
    DomainModules --> DRules
    DomainModules --> Audit
    Audit --> PG
    DRules --> PG
    
    API -->|Enqueue Long Jobs| RQueue
    RQueue --> W1
    RQueue --> W2
    RQueue --> W3
    
    W1 --> S3
    W1 --> PG
    W2 --> PG
    W3 --> AG
    
    AG -->|Tool Call Proposal| LLM
    AG -->|Approved Alerts| SMTP
```

---

## 2. VyaparShield: End-to-End Invoice-to-Cash Pipeline

The financial pipeline converts untrusted source files (invoices, bank statements, transaction logs) into verified, reconciled accounts receivable records and grounded business insights:

```mermaid
sequenceDiagram
    autonumber
    actor User as Finance User / MSME Owner
    participant Web as Frontend Dashboard
    participant API as FastAPI Ingestion Router
    participant Queue as Redis Queue
    participant Worker as Document / OCR Worker
    participant Engine as Deterministic Finance Engine
    participant DB as PostgreSQL Authoritative Store
    participant Agent as Finance Assistant (RAG + AgentGuard)

    User->>Web: Upload Invoice (PDF) or Statement (CSV)
    Web->>API: POST /api/v1/documents (Multi-tenant scoped)
    API->>DB: Record Document Metadata (Status: QUEUED)
    API->>Queue: Enqueue Extraction Job
    API-->>Web: Return 202 Accepted (Job ID)

    Queue->>Worker: Consume Extraction Task
    Worker->>Worker: Parse & Validate File Schema / Run OCR
    Worker->>Worker: Extract GSTIN, Vendor, Dates, Amounts, Line Items
    Worker->>DB: Store Raw Extraction & Per-Field Confidence Scores
    
    alt Confidence < Threshold or Validation Fails
        Worker->>DB: Route to Human Correction Queue
    else Validated
        Worker->>Engine: Trigger Reconciliation Cascade
        Engine->>Engine: 1. Exact Match (Inv No, Amount, Customer)
        Engine->>Engine: 2. Parse UPI/NEFT Narrations & Aliases
        Engine->>Engine: 3. Detect TDS (194C/194J), Bank Fees, Round-Offs
        Engine->>DB: Persist Reconciled Status & Ledger Events
    end

    User->>Web: Ask: "Why is cash flow projected to dip next month?"
    Web->>Agent: Query Finance Assistant
    Agent->>Engine: Invoke Typed Read-Only Tools (GetAging, GetForecast)
    Engine->>DB: Fetch Authoritative Receivables & Forecast Data
    Engine-->>Agent: Return Verified Financial Metrics
    Agent->>Agent: Generate Grounded Answer with Source Citations
    Agent-->>Web: Display Verified Insight with Citation Links
```

---

## 3. AegisOps: Incident-to-Resolution Pipeline

AegisOps monitors telemetry emitted by a simulated test service, detects operational anomalies, retrieves runbooks, and coordinates policy-checked remediation:

```mermaid
flowchart LR
    subgraph Emulation ["Telemetry Emulation"]
        Sim["Simulated Microservice\n(FastAPI / Locust Load / Injected Faults)"]
    end

    subgraph Observability ["Observability Pipeline"]
        Prom["Prometheus / OpenTelemetry\n(p95 Latency, Error Rates, Queue Lag)"]
        Logs["Structured JSON Logs"]
    end

    subgraph IncidentManagement ["Incident Correlation"]
        Detector["Anomaly Detector & Incident Grouper"]
        IncDB[("Incidents & Timeline Store")]
    end

    subgraph Investigation ["Agentic Investigation & Runbooks"]
        RAG["Runbook RAG\n(pgvector retrieval)"]
        Hypo["Hypothesis Ranking Engine"]
    end

    subgraph Governance ["AgentGuard Policy Gate"]
        Gate{"Requires Human Approval?"}
        HITL["Human Operator Approval Modal"]
        Exec["Restricted Command Executor\n(Restart, Rollback, Cache Flush)"]
        Verify["Postcondition Health Verification"]
    end

    Sim -->|Metrics| Prom
    Sim -->|Logs| Logs
    Prom --> Detector
    Logs --> Detector
    Detector --> IncDB
    IncDB --> Investigation
    RAG --> Hypo
    Hypo --> Gate
    Gate -->|Yes: High Impact| HITL
    HITL -->|Approved| Exec
    Gate -->|No: Low Impact Read| Exec
    Exec --> Sim
    Exec --> Verify
    Verify -->|Healthy| IncDB
```

---

## 4. AgentGuard: Multi-Stage Execution Gate

Every autonomous action proposed by an agent (e.g., dispatching overdue reminder notices or applying ledger adjustments) must pass through independent server-side enforcement:

```mermaid
stateDiagram-v2
    [*] --> ToolProposal: Agent Generates Tool Call
    
    state ToolProposal {
        [*] --> SchemaValidation: Validate Against Pydantic Contract
        SchemaValidation --> PolicyCheck: Valid Types & Parameters
        SchemaValidation --> Rejected: Malformed Schema
    }

    state PolicyCheck {
        [*] --> RoleAuthCheck: Check User Role & Tenant Scope
        RoleAuthCheck --> ImpactClassification: Tenant Verified
        RoleAuthCheck --> Denied: Cross-Tenant or Unauthorized Role
    }

    state ImpactClassification {
        [*] --> EvaluateImpact
        EvaluateImpact --> LowImpact: Read-Only Tool
        EvaluateImpact --> HighImpact: Mutating / External Side-Effect
    }

    LowImpact --> ExecuteSafely: Auto-Permitted
    HighImpact --> HumanApprovalQueue: Create Pending Approval Request
    
    state HumanApprovalQueue {
        [*] --> AwaitingUser
        AwaitingUser --> Approved: Business Owner Approves
        AwaitingUser --> RejectedByUser: Business Owner Rejects
    }

    Approved --> ExecuteSafely
    RejectedByUser --> AbortAction: Log Reason to Audit Trail
    Denied --> AbortAction: Record Security Event
    Rejected --> AbortAction: Return Error to Agent

    state ExecuteSafely {
        [*] --> RunInTestSandbox
        RunInTestSandbox --> PostconditionCheck: Verify DB State Change
    }

    PostconditionCheck --> Success: Invariants Verified
    PostconditionCheck --> Rollback: Invariant Failed / Error
    
    Success --> [*]: Commit & Write Immutable Audit Log
    Rollback --> [*]: Revert & Alert SRE
    AbortAction --> [*]
```

---

## 5. Network, Storage and Boundary Summary

| Boundary | Ingress Protocol | Protection Mechanism | Failure Behavior |
| :--- | :--- | :--- | :--- |
| **Client → API** | HTTPS / TLS 1.3 | JWT Auth, CORS, Rate Limiting (Redis token bucket) | HTTP 401 Unauthorized / 429 Too Many Requests |
| **API → PostgreSQL** | PostgreSQL Wire (SSL) | Connection Pool (SQLAlchemy async), Tenant RLS | Connection retry with exponential backoff |
| **API → Redis** | RESP over TCP (Auth) | Bounded queue depths, dead-letter exchange (DLQ) | Graceful degradation to sync fallback or queue alert |
| **Backend → LLM API** | HTTPS | Token budget limiter, prompt injection scrubber, secret masking | Fallback to cached template or missing-data notice |
