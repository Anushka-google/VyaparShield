# VyaparShield — Financial Invariants & Accounting Rules

**Phase:** Phase 0 — Mathematical Specifications & Statutory Rules  
**Compliance Target:** Indian Accounting Standards (Ind AS), GST Rules, Income Tax Act (Sections 194C/J)  

---

## 1. Monetary Type System & Decimal Safety

### Rules
1. All monetary fields MUST be represented as fixed-point `decimal.Decimal` in Python and `NUMERIC(18, 4)` in PostgreSQL.
2. Floating-point primitives (`float` in Python, `FLOAT` in PostgreSQL) are strictly forbidden in any financial calculation.
3. Quantization to Indian paise (2 decimal places) must be executed explicitly using `ROUND_HALF_UP`:
   $$\text{paise\_rounded} = \text{Decimal}(x).\text{quantize}(\text{Decimal}('0.01'), \text{rounding}=\text{ROUND\_HALF\_UP})$$

---

## 2. Invoice Calculations & GST Rules

### 2.1 Line Item Calculation
For each invoice line $i$:
$$\text{TaxableAmount}_i = \text{round}(\text{Quantity}_i \times \text{UnitPrice}_i)$$
$$\text{TaxAmount}_i = \text{round}\left(\text{TaxableAmount}_i \times \frac{\text{TaxRate}_i}{100}\right)$$
$$\text{LineTotal}_i = \text{TaxableAmount}_i + \text{TaxAmount}_i$$

### 2.2 GST Jurisdiction Splitting
GST is split based on the supplier's state code vs. the buyer's state code (extracted from the first 2 digits of the GSTIN):

- **Intra-State Supply (Supplier State == Buyer State):**
  $$\text{CGST} = \text{round}\left(\frac{\sum \text{TaxAmount}_i}{2}\right)$$
  $$\text{SGST} = \sum \text{TaxAmount}_i - \text{CGST}$$
  $$\text{IGST} = 0$$
- **Inter-State Supply (Supplier State != Buyer State):**
  $$\text{CGST} = 0, \quad \text{SGST} = 0$$
  $$\text{IGST} = \sum \text{TaxAmount}_i$$

### 2.3 Invoice Total & Outstanding Balance
$$\text{TotalAmount} = \sum \text{TaxableAmount}_i + \text{CGST} + \text{SGST} + \text{IGST}$$
$$\text{EffectiveSettled} = \sum (\text{AllocatedAmount} + \text{TDSDeducted} + \text{DiscountAllowed} + \text{RoundOffDiff})$$
$$\text{OutstandingBalance} = \text{TotalAmount} - \text{EffectiveSettled}$$

**Invariant Check:** $\text{OutstandingBalance} \ge 0$. Any mutation that would result in $\text{OutstandingBalance} < 0$ MUST be rejected with HTTP 422.

---

## 3. Payment Conservation & Allocation Invariant

A payment of total amount $P_{\text{total}}$ received from a customer is governed by strict conservation of funds:

$$P_{\text{total}} = P_{\text{allocated}} + P_{\text{unallocated}}$$

### Allocation Rules
1. $P_{\text{allocated}} \le P_{\text{total}}$ at all times.
2. An allocation operation must execute inside an ACID database transaction with row-level locking (`SELECT ... FOR UPDATE`) on the payment record.
3. Reversing a payment allocation reverses the ledger delta, restores the invoice outstanding balance, and increments $P_{\text{unallocated}}$ by the exact allocated amount.

---

## 4. Statutory TDS (Tax Deducted at Source) Heuristics

Indian B2B customers frequently deduct statutory TDS before remitting payment. VyaparShield uses deterministic matching rules to detect known TDS slabs rather than treating short payments as unexplained defaults:

| Section | Nature of Payment | Standard Rates | Heuristic Match Criteria |
| :--- | :--- | :--- | :--- |
| **Section 194C** | Payment to Contractors / Transporters | **1%** (Individual/HUF), **2%** (Company/LLP) | Shortfall equals exactly $1\%$ or $2\%$ of pre-tax or total invoice value ($\pm ₹1.00$ round-off). |
| **Section 194J** | Professional / Technical Fees | **10%** (Professional), **2%** (Technical) | Shortfall equals exactly $10\%$ of invoice amount. |
| **Section 194Q** | Purchase of Goods ($> ₹50$ Lakhs) | **0.1%** | Shortfall equals exactly $0.1\%$ of transaction amount. |

When a shortfall matches a statutory TDS slab, the engine marks the residual as `tds_deducted` (pending Form 16A TDS certificate reconciliation) rather than flagging the customer as delinquent.

---

## 5. Ledger Double-Entry Rules

Every financial mutation emits an immutable `ledger_event`:
- `INVOICE_ISSUED`: Debit Accounts Receivable, Credit Sales / GST Payable.
- `PAYMENT_RECEIVED`: Debit Bank Account, Credit Unallocated Payments.
- `PAYMENT_ALLOCATED`: Debit Unallocated Payments, Credit Accounts Receivable.
- `TDS_RECORDED`: Debit TDS Receivable, Credit Accounts Receivable.
- `DISCOUNT_GIVEN`: Debit Cash Discount Expense, Credit Accounts Receivable.

The sum of all ledger events for a given invoice must equal zero when fully paid.
