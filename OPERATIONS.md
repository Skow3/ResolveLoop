# Maximor AI / ResolveLoop: Agent Operations & Task Matrix

> **Workforce Classification:** Autonomous Finance, Accounting, Treasury & Revenue Operations  
> **Architecture Reference:** Multi-Tier Specialist Workforce (Tier 0 to Tier 4) with Human Review Escrow  
> **Associated Documents:** [FLOWS.md](FLOWS.md), [README.md](README.md)

---

## 1. Executive Overview & Workforce Hierarchy

Maximor AI operates as an autonomous, experience-driven multi-agent workforce designed for enterprise finance operations. Rather than routing all incoming inquiries to a single generic AI prompt, Maximor AI implements a **tiered specialist workforce** governed by strict authority boundaries, versioned corporate accounting controls, and audit trails.

### Workforce Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Tier 0: Orchestrator / Call Director               │
│         Front-Door Triage • Conversational FAQs • Intent Classification  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Tier 1 Specialist│       │ Tier 2 Specialist│       │ Tier 3 Specialist│
│  Finance Triage  │       │  AR & AP Invest. │       │ Acctg & Treasury │
│ (ERP Status/KB)  │       │ (Terms Matching) │       │ (Variance/Runway)│
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │ (Escalations > $50k or Ambiguous Policies)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Tier 4: Executive Controller & Chief Risk Officer          │
│        Policy ESC-400 Overrides • High-Risk Audits • Legal Review       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Human Review Escrow (Corporate Controller / CFO)          │
│                Structured Audit Dossier Signoff & Final Authorization   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Operational Specifications

### Tier 0: Orchestrator (Call Director)

- **Agent ID:** `agent_orchestrator`
- **Role Title:** Call Director & Front-Door Concierge
- **Primary Objective:** Welcome the caller, establish conversational rapport, answer general identity and system capability inquiries directly, classify incoming intents, and execute warm contextual transfers to the appropriate specialist.

#### Authorized Tasks & Capabilities
- Greet the caller dynamically using their name and corporate affiliation from [`customers`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/db.py#L43-L54).
- Answer meta-questions about Maximor AI’s role, architecture, connected ERPs, and operational capabilities without transferring.
- Detect caller intent and extract financial entities (e.g. invoice numbers, payment IDs, amounts, vendor names).
- Issue conversational transfer statements (*"I've got the details. Let me bring in our Accounts Receivable specialist..."*).
- Assemble structured [`HandoffContext`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/handoff.py#L91-L121) objects containing caller profile, pre-fetched ERP records, and identified entities.
- Stay on the line as a graceful failover fallback if a specialist initialization experiences a timeout or network glitch (Test Case G).

#### Authority Boundaries & Restrictions
- **CANNOT** modify customer balances or approve discount credits.
- **CANNOT** execute journal entries or post to the General Ledger.
- **CANNOT** override corporate accounting controls or policies.

#### Example Questions & Scenarios Handled Directly

| Inbound Question / Request | Orchestrator Action & Output |
| :--- | :--- |
| *"Who are you and what can you help me with?"* | Answers directly without transfer: *"You're speaking with Maximor AI. I'm a finance operations assistant. I can help with invoices, payments, revenue, cash, reporting, and other finance operations. What can I help you with today?"* |
| *"What is Maximor AI?"* | Explains Maximor's autonomous finance workforce and self-improving episodic memory. |
| *"Can you tell me what ERP and billing systems you connect to?"* | Confirms integrations with Oracle NetSuite OneWorld, Stripe Corporate Billing, Salesforce CPQ, and JPMorgan Chase Treasury. |
| *"Hello, I'm calling from Acme Corp to ask about our accounts."* | Acknowledges Alice Morgan at Acme Corp and prompts for the specific invoice, payment, or ledger topic. |
| *"What can your team do if our payment was short?"* | Explains that our Accounts Receivable Specialist will cross-reference the invoice terms and remittance advice. |

---

### Tier 1: Finance Triage Specialist

- **Agent ID:** `agent_l1_triage`
- **Role Title:** Basic Finance Triage & Knowledge Base Specialist
- **Primary Objective:** Provide first-contact resolution for non-disputed factual inquiries, invoice status checks in NetSuite ERP, customer profile verifications, and knowledge base search.

#### Authorized Tasks & Capabilities
- Query NetSuite ERP invoice records via [`get_invoice`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L86-L105).
- Report open balances, due dates, payment terms, and aging status (e.g. Current, Overdue, Partially Paid).
- Search corporate finance policy documentation via [`search_policy`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L172-L184).
- Acknowledge incoming warm handoff context from the Call Director without asking the customer to repeat themselves.

#### Authority Boundaries & Restrictions
- **CANNOT** authorize payment discount credits or write off short payments (requires Tier 2).
- **CANNOT** investigate cloud compute budget variances or review GL accruals (requires Tier 3).
- **CANNOT** approve policy exceptions or transactions exceeding standard tolerances (requires Tier 4).

#### Example Questions & Scenarios Handled

| Inbound Question / Request | Specialist Action & Resolution |
| :--- | :--- |
| *"What's the status of invoice INV-4471?"* | Calls `get_invoice("INV-4471")` in NetSuite ERP. Reports: *$12,500 total amount for Acme Corp, status is Partially Paid with a remaining balance of $250. Remittance PMT-8821 for $12,250 received August 23, 2026.* |
| *"Where is invoice INV-4472 and is it overdue?"* | Queries `INV-4472` in NetSuite. Reports: *Invoice for Nexus Logistics in the amount of $4,800 is currently Overdue (due August 19, 2026 under Net 30 terms).* |
| *"Has invoice INV-9001 for Global Health Network been settled?"* | Queries `INV-9001`. Confirms: *Invoice for $180,000 was paid in full on June 1, 2026; balance is $0.* |
| *"What are the standard payment terms on our account?"* | Checks customer profile for Acme Corp. Confirms standard contractual terms are 2/10 Net 30. |
| *"Can you provide our organization's billing address and contact on file?"* | Retrieves Alice Morgan, Finance Director, Apex Global Technologies (`cust1`). |
| *"Where can I submit a remittance advice document?"* | Directs caller to the corporate billing portal and provides instructions for Stripe/NetSuite sync. |

---

### Tier 2: Accounts Receivable Specialist

- **Agent ID:** `agent_l2_ar`
- **Role Title:** Accounts Receivable & Deductions Specialist
- **Primary Objective:** Resolve customer deductions, short payments, remittance matching, and credit discount authorizations in accordance with corporate policy `SHORT-PAY-01`.

#### Authorized Tasks & Capabilities
- Cross-reference invoices (`get_invoice`) with banking and Stripe payment remittances (`get_payment`).
- Query customer payment history and historical payment timeliness (`get_customer_history`).
- Inspect versioned AR credit policies (`get_policy_version("SHORT-PAY-01", "v2.1")`).
- Validate early payment discount compliance (e.g. 2% discount within 10 calendar days under 2/10 Net 30 terms).
- Approve discount credit adjustments up to $500.00 and mark invoices settled in full.
- Record structured audit trail events for prompt payment credit applications.

#### Authority Boundaries & Restrictions
- **CANNOT** approve unearned discount deductions exceeding $500.00 without escalation.
- **CANNOT** post General Ledger journal entries or modify revenue schedules (requires Tier 3).
- **CANNOT** grant policy overrides for disputed amounts exceeding $50,000 (requires Tier 4).

#### Example Questions & Scenarios Handled

| Inbound Question / Request | Specialist Action & Resolution |
| :--- | :--- |
| *"Why was our Acme payment short by $250 on invoice INV-4471?"* | Queries `INV-4471` ($12,500), `PMT-8821` ($12,250), and policy `SHORT-PAY-01`. Confirms remittance arrived August 23 (8 days after August 15 invoice date, within 10-day window). Approves $250 discount credit; updates invoice balance to $0. |
| *"We took a prompt payment discount on our invoice, but our portal still shows $250 due."* | Evaluates remittance advice, validates 2/10 Net 30 eligibility, authorizes the credit adjustment, and clears the open portal balance. |
| *"Does Acme Corp qualify for early settlement discounts on our Q3 platform bill?"* | Reviews contract terms: 2% deduction allowed if paid within 10 days; explains cash savings and calculation. |
| *"Why was payment remittance PMT-8821 flagged as short?"* | Explains that automated ingestion flagged a $250 differential between the $12,500 invoice and $12,250 remittance, which has now been validated and approved. |
| *"Can you pull our average days to pay and payment track record?"* | Queries `get_customer_history`. Reports: average days to pay is 8.2 days, account in good standing with $1.2M lifetime transaction volume. |
| *"What is our current Accounts Receivable exposure with Acme Corp?"* | Summarizes all open, partially paid, and settled invoices across the active fiscal quarter. |

---

### Tier 2: Order & Fulfillment Specialist

- **Agent ID:** `agent_l2_order`
- **Role Title:** Order & Fulfillment Operations Specialist
- **Primary Objective:** Track software connector orders, verify license provisioning status, and execute cancellations prior to key dispatch.

#### Authorized Tasks & Capabilities
- Query purchase order and fulfillment records via [`lookup_order`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/mock_services.py#L50-L58).
- Verify fulfillment tracking numbers and software license provisioning telemetry.
- Execute order cancellations via [`cancel_order`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/mock_services.py#L60-L70).

#### Example Questions & Scenarios Handled
- *"What is the status of purchase order PO-88102 for API Data Pipeline Connectors?"*
- *"Can we cancel our connector subscription order PO-88102 before provisioning completes?"*
- *"Where can I find the tracking information for our hardware security key shipment?"*

---

### Tier 3: Accounting Authority Specialist

- **Agent ID:** `agent_l3_accounting`
- **Role Title:** Accounting Authority & General Ledger Specialist
- **Primary Objective:** Analyze vendor bill budget variances, correlate infrastructure spend against engineering compute telemetry, verify month-end General Ledger accruals, and govern ASC 606 revenue recognition.

#### Authorized Tasks & Capabilities
- Query vendor accounts payable bills via [`get_bill`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L125-L148).
- Analyze budget vs. actual budget variances (flux analysis).
- Cross-reference vendor billing overruns with Datadog APM and OpenAI inference token telemetry.
- Retrieve and verify General Ledger accrual journal entries via [`get_journal_entry`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L207-L218).
- Query ASC 606 revenue recognition schedules via [`get_revenue_schedule`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L240-L252).
- Inspect multi-entity consolidation balance reports via [`get_reconciliation`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L220-L238).

#### Authority Boundaries & Restrictions
- **CANNOT** approve unbudgeted variances or single adjustments exceeding $50,000 without Tier 4 Controller signoff (`ESC-400`).
- **CANNOT** execute retrospective modifications to ASC 606 contracts without audit committee review.

#### Example Questions & Scenarios Handled

| Inbound Question / Request | Specialist Action & Resolution |
| :--- | :--- |
| *"Why was our August AWS hosting bill BILL-7701 $10,400 (17.9%) over budget?"* | Queries `BILL-7701` ($68,400 vs $58,000 budget). Correlates overrun with Datadog APM token throughput surge during enterprise customer trials. Confirms GL accrual entry `JE-2026-03` has posted to software hosting expenses. |
| *"Has the month-end accrual journal entry JE-2026-03 been approved and posted?"* | Queries `get_journal_entry("JE-2026-03")`. Confirms $10,400 debit to account 6100 (Software & Hosting) and credit to account 2100 (Accrued Expenses), approved by Controller Alice Morgan. |
| *"What is the status of Snowflake vendor bill BILL-7702?"* | Checks `BILL-7702` ($14,200 actual vs $15,000 budget). Reports: -$800 (-5.3%) variance, within budget tolerance, pending standard AP approval. |
| *"What is our ASC 606 revenue recognition schedule on contract CTR-2026-GHN?"* | Queries `get_revenue_schedule`. Reports: $180,000 annual contract, recognized ratably at $15,000/month; $45,000 recognized to date, $135,000 deferred revenue balance. |
| *"What was our consolidated Q2 revenue across all international entities?"* | Queries `get_reconciliation("CONSOL-2026-Q2")`. Reports: US ($34.2M), UK (£8.1M / $10.37M USD), APAC ($3.6M USD), intercompany eliminations of -$1.2M, yielding **$46,968,000 consolidated revenue**. |
| *"Does AWS bill BILL-7701 satisfy our 3-way match policy under AP-MATCH-01?"* | Evaluates tolerance rules: variance exceeded 1.5% threshold, triggering flux review which was documented and resolved via accrual. |

---

### Tier 3: Treasury & Liquidity Specialist

- **Agent ID:** `agent_l3_treasury`
- **Role Title:** Treasury Operations & Cash Liquidity Specialist
- **Primary Objective:** Monitor corporate bank account positions, calculate interest-bearing yields, track net burn rates, and project 13-week cash runway models.

#### Authorized Tasks & Capabilities
- Query real-time cash balances across operating and money market accounts via [`get_cash_position`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L253-L264).
- Extract 13-week FP&A cash flow forecasts and net burn rates via [`get_forecast`](file:///home/jankari/.ao/data/worktrees/syndicate_ao/syndicate_ao-2/resolve_loop/finance_tools.py#L265-L277).
- Analyze liquidity runway under variable operational revenue and disbursement scenarios.

#### Example Questions & Scenarios Handled

| Inbound Question / Request | Specialist Action & Resolution |
| :--- | :--- |
| *"What is our total cash position across all bank accounts today?"* | Queries `get_cash_position`. Reports: **$18.45M total cash** ($8.2M operating checking, $10.25M treasury money market at JPMorgan Chase). |
| *"How many months of runway do we have based on current net burn?"* | Extracts burn telemetry: monthly net burn is $650,000, providing **28.4 months of runway**. |
| *"What is the yield on our JPMorgan Chase Treasury money market account?"* | Confirms weighted money market yield is currently **5.12%**. |
| *"What does our 13-week cash forecast project for ending liquidity in Week 3?"* | Queries `get_forecast("13_week")`. Reports: Week 1 ending $18.88M, Week 2 ending $18.42M, Week 3 ending $18.58M with stable operational cash flow. |
| *"Are operating cash reserves sufficient for upcoming payroll and vendor payables?"* | Validates that $8.2M in operating checking exceeds minimum 60-day operational reserve threshold. |

---

### Tier 4: Executive Controller & Risk Authority

- **Agent ID:** `agent_l4_executive`
- **Role Title:** Executive Controller & Chief Risk Officer
- **Primary Objective:** Govern high-exposure financial adjustments exceeding $50,000, enforce policy `ESC-400`, adjudicate ambiguous contract terms, compile comprehensive audit dossiers, and escrow cases for Human Controller / CFO signoff.

#### Authorized Tasks & Capabilities
- Evaluate material financial exceptions and credit term disputes under policy `ESC-400`.
- Block automated settlement on adjustments $\ge \$50,000.00$.
- Compile complete Human Review audit dossiers including customer history, GL impact, policy references, and risk assessments.
- Dispatch high-priority escalation tickets for Controller and CFO signoff.
- Set `human_review_required: True` in case resolution payloads and audit journals.

#### Authority Boundaries & Restrictions
- **CANNOT** bypass CFO signoff on transactions exceeding $50,000.
- **MUST** log full cryptographic audit traces to `audit_events` and `escalations` tables.

#### Example Questions & Scenarios Handled

| Inbound Question / Request | Specialist Action & Resolution |
| :--- | :--- |
| *"We need an override for a $65,000 transaction under ambiguous policy terms."* | Evaluates policy `ESC-400` ($50k+ threshold). Restricts automated settlement. Generates priority audit dossier, dispatches escalation ticket `MX-ESC-...`, and routes to Controller and CFO for final signoff within 2 hours. |
| *"A strategic enterprise client demands a $75,000 credit deduction outside contractual terms."* | Identifies material exposure, checks customer contract and historical LTV, freezes automated AR adjustments, and compiles an Executive Review dossier. |
| *"Can we grant a special exception to policy ESC-400 for our largest healthcare customer?"* | Evaluates risk profile, determines required authorization tier (Board / CFO), and schedules formal controller review. |
| *"Prepare an executive audit file for the CFO regarding our Q3 cloud hosting overages."* | Aggregates all vendor bills, Datadog telemetry logs, GL accrual entries, and flux analysis into an audit package. |

---

## 3. Operational Handoff Rules & Routing Reference

The ResolveLoop engine determines the appropriate agent tier using a 4-tier decision cascade:

```
Step 1: Check General Conversational Patterns
   ├── Matches "Who are you?", "What is Maximor?", "Help me with..."
   └── NO financial entities detected ──► TIER 0: ORCHESTRATOR DIRECT (No Transfer)

Step 2: Check Episodic Memory & Procedural Rules
   ├── Past similar case required L2/L3?
   └── Procedural rule active (e.g. billing dispute, short pay)? ──► PROMOTE TO TARGET TIER

Step 3: Multi-Tier Intent & Entity Classifier (gpt-5-nano / Heuristic)
   ├── High risk, > $50k, override, ambiguous terms ──────────────► TIER 4: EXECUTIVE CONTROLLER
   ├── Budget variance, GL accrual, ASC 606, Treasury runway ──────► TIER 3: ACCOUNTING / TREASURY
   ├── Short payment, 2/10 Net 30, remittance matching ───────────► TIER 2: AR SPECIALIST
   ├── Order tracking, connector shipment ────────────────────────► TIER 2: ORDER SPECIALIST
   └── Invoice status check, balance inquiry, KB lookup ──────────► TIER 1: TRIAGE SPECIALIST

Step 4: Failover Safe Mode
   └── Specialist initialization exception or network timeout ───► FALLBACK TO ORCHESTRATOR
```

### Routing Quick Reference Matrix

| Inquiry Type | Target Agent | Governing Policy | Authorized Tools | Human Review? |
| :--- | :--- | :--- | :--- | :---: |
| **Conversational Greeting / FAQ** | Tier 0: Orchestrator | *Standard Dialog* | *None (Direct Dialog)* | No |
| **Invoice Status / Open Balance** | Tier 1: Triage | *KB / ERP FAQ* | `get_invoice`, `search_records` | No |
| **Short Payment / Terms Deduction** | Tier 2: AR Specialist | `SHORT-PAY-01` | `get_invoice`, `get_payment`, `get_policy_version` | No |
| **Order / License Provisioning** | Tier 2: Order Specialist | *Fulfillment Standard* | `lookup_order`, `cancel_order` | No |
| **Cloud Hosting Budget Flux** | Tier 3: Accounting | `ACCRUE-01` | `get_bill`, `get_journal_entry` | No |
| **ASC 606 Revenue Recognition** | Tier 3: Accounting | `REV-REC-01` | `get_revenue_schedule` | No |
| **Treasury & 13-Week Runway** | Tier 3: Treasury | *Treasury Policy* | `get_cash_position`, `get_forecast` | No |
| **Consolidated International P&L** | Tier 3: Accounting | *Consolidation Policy* | `get_reconciliation` | No |
| **Exceptions > $50,000 / Overrides** | Tier 4: Executive Controller | `ESC-400` | `policy_override`, `escalate_to_human` | **Yes (CFO/Controller)** |

---

## 4. Closed-Loop Learning & Procedural Evolution

Maximor AI improves dynamically with every interaction through its **Closed Learning Loop**:

$$\text{Inbound Case} \longrightarrow \text{Routing} \longrightarrow \text{Tool Resolution} \longrightarrow \text{Evaluation (0--100)} \longrightarrow \text{Episodic Memory} \longrightarrow \text{Procedural Rule}$$

### Real-World Learning Example: Short Payment Auto-Promotion

1. **Case 1 (Cold Start — First Time Encountered)**:
   - *Inquiry:* *"Why was payment PMT-8821 short by $250 on invoice INV-4471?"*
   - *Cold Behavior:* Naive router sends inquiry to Tier 1 Triage.
   - *Outcome:* Tier 1 lacks credit authorization authority and escalates to Tier 2.
   - *Reflection Engine:* Evaluates case, logs an escalation penalty, and records an episodic experience in PostgreSQL:
     > *"Lesson: Route short payment inquiries directly to Tier 2 Accounts Receivable. If payment arrived within 10 calendar days on 2/10 Net 30 terms, auto-apply discount credit."*
   - *Procedural Memory:* Synthesizes rule `rule_billing_or_refund` mapping short payments to Tier 2.

2. **Case 2 (Warm Start — After Learning)**:
   - *Inquiry:* *"Why was our Acme payment short?"*
   - *Warm Behavior:* Router queries episodic memory and procedural rules, identifying prior experience `exp_short_pay_01`.
   - *Outcome:* **Directly routed to Tier 2 Accounts Receivable on Turn 1.**
   - *Result:* Zero repeat escalations, resolution time cut by 60%, score increases from 65/100 to 94/100.

3. **User Feedback Reinforcement**:
   - When the user rates the resolution with **Thumbs Up** (👍):
     - PostgreSQL executes: `UPDATE experiences SET confidence = LEAST(confidence + 0.05, 0.99)`.
     - Ensures the successful resolution rule becomes a permanent corporate standard.
   - If rated with **Thumbs Down** (👎):
     - Confidence decreases (`-0.15`), and reflection logs failure memory to re-tune routing parameters.
