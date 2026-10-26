# ADR-003: Deterministic-First Business Logic and Financial Invariants

**Status:** Accepted  
**Date:** 2026-10-25  
**Deciders:** Core Engineering Team  
**Context:** Financial Integrity and Arithmetic Reliability Strategy  

---

## Context and Problem Statement
Financial software for MSMEs must be 100% mathematically correct, auditable, and reproducible. A common failure mode in GenAI-enabled systems is delegating arithmetic (e.g., computing invoice balances, overdue aging buckets, tax deductions, or reconciliation candidate matching) to LLM prompts. 

Large Language Models:
- Are probabilistic sequence predictors prone to subtle arithmetic hallucination.
- Lack deterministic precision, especially when dealing with Indian currency units, fractional GST, TDS, and rounding nuances.
- Produce non-reproducible answers when system prompts, temperatures, or base models change.

## Considered Options
1. **LLM Prompt-Based Calculation:** Feeding invoice and payment text to the model and asking it to calculate balances and match payments.
2. **LLM Code-Interpreter Sandbox:** Allowing the LLM to write and execute arbitrary Python scripts in a runtime sandbox to calculate totals.
3. **Deterministic Backend Services + Read-Only LLM Tools (Chosen):** All accounting calculations, receivables aging, exact/fuzzy reconciliation ranking, and financial invariants are executed by deterministic Python backend services using fixed-point arithmetic (`decimal.Decimal`). The LLM interacts strictly via typed read-only tools that query pre-calculated authoritative figures.

## Decision
We mandate **Deterministic-First Business Logic** for all financial calculations and reconciliation operations.

### Architectural Rules
1. **No Floating-Point Math:** All currency fields must use Python `decimal.Decimal` and PostgreSQL `NUMERIC(18, 4)`. Native IEEE 754 floating-point values (`float` in Python or `FLOAT/REAL` in SQL) are forbidden in the financial path.
2. **Standardized Rounding Policy:** Rounding must be explicit using `ROUND_HALF_UP` to two decimal places (paise) unless specified otherwise by statutory guidelines.
3. **Deterministic Reconciliation Cascade:**
   - **Step 1 (Deterministic Exact Match):** Exact Match on `(invoice_number, amount, customer_id, date_window)`.
   - **Step 2 (Rule-Based Normalization):** Stripping bank narrations (UPI/NEFT/IMPS prefixes), resolving vendor aliases, and calculating standard deductions (TDS Section 194C @ 1%/2%, Section 194J @ 10%, bank gateway charges).
   - **Step 3 (Ranked Candidates with Explainable Signals):** Remaining ambiguous candidates are ranked using explainable weighted scoring (Amount similarity, Narration fuzzy ratio, Due-date proximity).
   - **Step 4 (Human Confirmation):** Ambiguous or partial matches are queued for human review. The system NEVER silently marks an ambiguous candidate as confirmed.
4. **LLM Grounding Role:** The GenAI Assistant only retrieves verified calculations and facts. If required calculation data is missing, the LLM is instructed to refuse speculation and state that data is missing.

## Consequences
### Positive
- **100% Auditability:** Every balance and reconciliation decision can be reconstructed and independently verified against source database records.
- **Statutory Compliance:** Correct Indian GST, TDS, and ledger entries adhering to accounting standards.
- **Robust Against Model Drifts:** Updating or swapping the LLM provider will never corrupt financial calculations.

### Negative / Trade-offs
- Requires implementing comprehensive deterministic business logic and test fixtures covering edge cases (partial payments, split payments, credit notes, discounts).

## Revisit Conditions
This ADR is permanent for all V1 and V2 financial engines. Machine Learning algorithms may be used to predict late payment probabilities or rank ambiguous candidates, but authoritative ledger mutations will always remain deterministic and rule-governed.
