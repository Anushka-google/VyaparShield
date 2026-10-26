# ADR-004: AgentGuard Server-Side Policy Gate & Human Approval Workflow

**Status:** Accepted  
**Date:** 2026-10-25  
**Deciders:** Core Engineering Team  
**Context:** AI Safety, Agent Governance, and Execution Control Strategy  

---

## Context and Problem Statement
Autonomous AI agents in NexusOps AI (VyaparShield financial investigator and AegisOps incident responder) have access to tools that can alter system state, send external communications (e.g., payment reminders via email/SMS), or trigger infrastructure remediation actions.

Relying on the LLM's own internal reasoning or system prompts to respect safety rules is inherently flawed due to:
- Prompt injection and jailbreaking vulnerabilities.
- Non-deterministic model outputs.
- Lack of cryptographic auditability.

Allowing direct, unvetted agent execution creates severe operational and legal risks (e.g., sending unauthorized aggressive debt collection notices to high-value MSME clients, or executing destructive remediation commands).

## Considered Options
1. **Unrestricted Agent Execution:** Granting the agent API keys and letting it call tools directly whenever it deems necessary.
2. **Prompt-Only Guardrails:** Instructing the model in its system prompt: *"Only perform action X if user Y approves"*.
3. **AgentGuard Server-Side Policy Engine with Human-in-the-Loop Approval (Chosen):** Decoupling agent planning from tool execution. The agent only outputs a structured proposal. The server evaluates a deterministic policy gate (deny-by-default), pauses execution for human approval on consequential actions, logs cryptographic audit events, and verifies postconditions after execution.

## Decision
We implement **AgentGuard** as an independent, server-side policy and authorization gate.

### Architectural Rules
1. **Server-Side Deny-By-Default:**
   - The LLM cannot directly trigger execution. A tool call request is submitted to the backend as a `ToolInvocationRequest`.
   - The policy engine checks:
     - Is the requesting agent authorized for this tool?
     - Is the target entity within the current `tenant_id`?
     - Does the caller possess the requisite RBAC role?
     - Does the parameter payload pass strict Pydantic validation?
2. **Mandatory Human-in-the-Loop (HITL) Gate:**
   - Any tool with high impact (classified as `ACTION_HIGH_IMPACT`) enters the `PENDING_APPROVAL` state.
   - High-impact tools include:
     - `send_collection_reminder`
     - `write_off_invoice_balance`
     - `reverse_reconciliation_match`
     - `execute_service_remediation` (AegisOps)
   - The workflow pauses and emits a notification to the designated reviewer/owner.
   - Execution resumes ONLY after an authenticated human submits an explicit approval with timestamp and signature.
3. **Postcondition Verification:**
   - After an approved action executes, the system queries the actual resulting state (e.g., verifying the email delivery status or checking the ledger balance change).
   - If the postcondition fails, the transaction is safely rolled back or placed into an escalation queue.
4. **Tamper-Evident Audit Trail:**
   - Every proposal, policy check outcome, approval decision, and postcondition verification is logged in an immutable `audit_events` table.

## Consequences
### Positive
- **Absolute Safety:** Model compromise or prompt injection cannot bypass hardcoded server policy rules.
- **Enterprise Ready:** Clear accountability—every action is traceable to an approver.
- **Resilient Workflows:** Stateful pause/resume architecture prevents repeated execution or duplicate emails.

### Negative / Trade-offs
- Introduces state machine persistence overhead (requiring database-backed workflow state tracking).
- Workflows requiring human approval are asynchronous and depend on user responsiveness.

## Revisit Conditions
This policy framework is foundational and mandatory for NexusOps AI V1 and all future versions.
