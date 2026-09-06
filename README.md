# Maximor AI: Autonomous Self-Improving Finance Operations Workforce

Maximor AI (powered by ResolveLoop) is an experience-driven multi-agent workforce designed for enterprise finance, accounting, treasury, and revenue operations (Hackathon Track 1: Automated Agent Engineering).

> *"Maximor AI pairs an L1–L4 tiered finance workforce with PostgreSQL episodic memory and Smallest AI voice streaming. Every reconciliation and audit trail makes the next resolution faster."*

📚 **System Documentation & Guides:**
- [**FLOWS.md**](FLOWS.md): Comprehensive end-to-end documentation of every workflow, state machine, and data lifecycle in the system.
- [**OPERATIONS.md**](OPERATIONS.md): Detailed agent task matrix, authority tiers (L1–L4), tool permissions, and domain example questions.

---

## Key Highlights & Capabilities

1. **PostgreSQL Enterprise Finance Database (`maximor_finance`)**:
   - 14 relational tables with foreign keys, indexes, timestamps, and JSONB payloads.
   - Core tables: `organizations`, `users`, `customers`, `finance_systems`, `finance_records`, `policies`, `cases`, `agent_runs`, `tool_calls`, `escalations`, `experiences`, `learned_policies`, `feedback`, and `audit_events`.
   - Rich synthetic seeds across **Revenue (ASC 606)**, **Cash (13-week runway, lockbox)**, **AR (short payments, 2/10 Net 30)**, **AP (3-way match, AWS hosting flux)**, **Close (accruals, JEs)**, and **Consolidation**.

2. **Hands-Free Customer Voice Station**:
   - Spoken greeting via Smallest AI Lightning TTS: *"Thanks for calling Maximor AI. Hi [User Name], how can I help you today?"*.
   - Continuous hands-free loop powered by Web Audio API Voice Activity Detection (VAD) with ~1.8s trailing silence detection — zero button presses between turns!
   - Smallest AI Pulse STT converts voice queries with sub-second latency.
   - Smallest AI Lightning TTS generates 24kHz natural speech responses.

3. **In-Line Thumbs Up / Down Feedback & Closed Learning Loop**:
   - Users can rate resolutions (👍 / 👎) directly on the response card without interrupting hands-free listening.
   - Ratings dynamically update experience confidence weights in PostgreSQL and feed procedural rule synthesis.
   - Subsequent similar cases route directly to the optimal tier (L1–L4) with 0% repeat escalations.

4. **Design-First UI with Dark/Light Mode**:
   - Clean dark (obsidian glass) and light (crisp modern fintech) theme toggle with `localStorage` persistence.
   - Live runtime indicators: OpenAI `gpt-5-nano`, Smallest AI `Pulse + Lightning`, and PostgreSQL `maximor_finance`.

---

## Multi-Tiered Finance Agent Architecture

- **Tier 1 (L1 Basic Finance Triage)**: Invoice status, payment receipts, basic customer profile, policy FAQs. Auto-escalates upon detecting short payments or terms discrepancies.
- **Tier 2 (L2 Contextual Investigation)**: Short payment resolution, payment-to-invoice matching across Stripe and NetSuite, credit discount authorization (e.g. 2/10 Net 30 window validation under policy `SHORT-PAY-01`).
- **Tier 3 (L3 Multi-System Authority)**: Revenue recognition schedules (ASC 606), ERP vs CRM cross-system variance, cloud hosting budget flux (`BILL-7701`), journal entries (`JE-2026-03`), bank reconciliations.
- **Tier 4 (L4 Executive Escalation / Human Review)**: Variances > $50,000 (`ESC-400`), legal exceptions, VIP risk management, human controller signoff with structured evidence dossier.

---

## Quick Start & Verification

### 1. Environment Setup
Ensure your `.env` file contains credentials:
```bash
OPENAI_API_KEY=your_openai_key
RESOLVELOOP_MODEL=gpt-5-nano
RESOLVELOOP_USE_LLM=1
SMALLEST_API_KEY=your_smallest_ai_key
DATABASE_URL=postgresql:///maximor_finance
```

### 2. Seed Synthetic Finance Data
Initialize the PostgreSQL schema and seed records:
```bash
python -m resolve_loop.seeds
```

### 3. Run the Full Test Suite
Run the 16 unit tests covering baseline benchmark, voice, finance operations, warm handoffs, and audit trails:
```bash
python -m unittest discover tests
```

### 4. Launch the Web Application
Start the interactive 3-view web dashboard:
```bash
python -m resolve_loop.main --web --port 5000
```
Open [http://localhost:5000](http://localhost:5000) in your browser:
- **Overview**: Complete closed feedback loop architecture and tier walkthrough.
- **Customer Call**: Start simulated hands-free phone call with Alice Morgan, speak naturally or test scenarios.
- **Finance Ops CRM**: Live client directory, synced systems, audit journal, and comparative learning benchmark.

---

## Database Schema Overview

```
organizations ────< users
      │
      ├───────────< customers ────< cases ────< agent_runs ────< tool_calls
      │                               │     │
      ├───────────< finance_systems   │     ├─< escalations
      │                  │            │     ├─< feedback
      │                  v            │     └─< audit_events
      ├───────────< finance_records   │
      │                               v
      ├───────────< policies ───< experiences ───< learned_policies
```

---

## Auditability & Explainability

Every case execution logs structured traces visible in the CRM and API:
```
Case Created → Routed to L2 (Confidence: 94%) → get_invoice (INV-4471) → get_payment (PMT-8821) → search_policy (SHORT-PAY-01) → 2/10 Net 30 Term Verified → $250 Discount Approved → Evaluated (Score: 94/100) → User Feedback (👍 Positive) → Experience Saved to PostgreSQL.
```
