"""Comprehensive synthetic finance seed data for Maximor AI Finance Operations.

Populates realistic enterprise financial records, organizations, policies,
and systems across Revenue, Cash, AR, AP, Close, Consolidation, and Reporting.
"""
import json
import logging
from datetime import date, datetime, timezone
from .db import db

logger = logging.getLogger("maximor.seeds")

def seed_database():
    """Populate database with rich synthetic finance records."""
    db.init_schema()

    # 1. Organizations
    orgs = [
        ("org_apex", "Apex Global Technologies", "B2B Enterprise Software", "America/New_York", "active"),
        ("org_meridian", "Meridian Health Solutions", "Healthcare FinOps & Medical Systems", "America/Chicago", "active"),
        ("org_lumina", "Lumina Digital Commerce", "Omnichannel E-Commerce & Retail", "America/Los_Angeles", "active"),
    ]
    for org_id, name, ind, tz, st in orgs:
        db.execute(
            """INSERT INTO organizations (id, name, industry, timezone, status)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, industry=EXCLUDED.industry;""",
            (org_id, name, ind, tz, st)
        )

    # 2. Users (Internal Finance Operations Team)
    users = [
        ("usr_alice", "org_apex", "Alice Morgan", "alice.morgan@apextechnologies.com", "Controller", "active"),
        ("usr_bob", "org_lumina", "Bob Jenkins", "bob.jenkins@luminacommerce.com", "AR Manager", "active"),
        ("usr_charlie", "org_meridian", "Charlie Davis", "charlie.davis@meridianhealth.com", "CFO", "active"),
        ("usr_diana", "org_apex", "Diana Ross", "diana.ross@apextechnologies.com", "FP&A Director", "active"),
        ("usr_elena", "org_apex", "Elena Rostova", "elena.rostova@apextechnologies.com", "AP Manager", "active"),
    ]
    for uid, oid, name, email, role, st in users:
        db.execute(
            """INSERT INTO users (id, organization_id, name, email, role, status)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role;""",
            (uid, oid, name, email, role, st)
        )

    # 3. Customers / Client Contacts
    customers = [
        ("cust1", "org_apex", "Alice Morgan", "alice@apextechnologies.com", "+1-415-555-0192", "Finance Director", "voice", "good_standing"),
        ("cust2", "org_lumina", "Bob Jenkins", "bob@luminacommerce.com", "+1-312-555-0144", "Operations Lead", "voice", "good_standing"),
        ("cust3", "org_meridian", "Charlie Davis", "charlie@meridianhealth.com", "+1-212-555-0188", "Chief Financial Officer", "voice", "vip_enterprise"),
    ]
    for cid, oid, name, email, phone, role, pref, st in customers:
        db.execute(
            """INSERT INTO customers (id, organization_id, name, email, phone, role, preferred_channel, account_status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role;""",
            (cid, oid, name, email, phone, role, pref, st)
        )

    # 4. Finance Systems
    systems = [
        ("sys_netsuite", "org_apex", "NetSuite OneWorld", "ERP", "Oracle NetSuite", "connected", json.dumps({"sync_frequency": "15m", "gl_version": "2026.1"})),
        ("sys_stripe", "org_apex", "Stripe Corporate Billing", "Billing", "Stripe", "connected", json.dumps({"currencies": ["USD", "EUR", "GBP"]})),
        ("sys_salesforce", "org_apex", "Salesforce CPQ & RevOps", "CRM", "Salesforce", "connected", json.dumps({"pipeline_sync": True})),
        ("sys_jpmc", "org_apex", "JPMorgan Chase Global Treasury", "Bank", "JPMorgan", "connected", json.dumps({"feed": "BAI2_realtime", "account_ending": "8841"})),
        ("sys_workday", "org_apex", "Workday Adaptive Planning", "Spreadsheet", "Workday", "connected", json.dumps({"plan_cycle": "Q3_2026"})),
    ]
    for sid, oid, name, stype, prov, cstat, meta in systems:
        db.execute(
            """INSERT INTO finance_systems (id, organization_id, name, system_type, provider, connection_status, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, connection_status=EXCLUDED.connection_status;""",
            (sid, oid, name, stype, prov, cstat, meta)
        )

    # 5. Policies
    policies = [
        (
            "pol_short_pay", "org_apex", "SHORT-PAY-01", "Short-Payment Resolution & Cash Application Policy",
            "accounts_receivable",
            "Governs customer payment deductions. Permits automated discount credit if payment arrived within early payment discount terms (e.g. 2/10 Net 30). Disputed deductions under $500 can be resolved by L2. Deductions > $500 require customer statement verification.",
            json.dumps({"max_auto_discount": 500.00, "term_tolerance_days": 2, "required_tier": 2}),
            "v2.1", "corporate_treasury", True
        ),
        (
            "pol_rev_rec", "org_apex", "REV-REC-01", "ASC 606 Revenue Recognition for Multi-Element Contracts",
            "revenue",
            "Software license fees recognized ratably over the contract duration. Professional services recognized upon milestone completion. Mid-contract modifications must be treated as prospective adjustments.",
            json.dumps({"standard": "ASC 606", "ratable": True, "milestone_threshold_pct": 100}),
            "v3.0", "audit_committee", True
        ),
        (
            "pol_ap_match", "org_apex", "AP-MATCH-01", "Accounts Payable 3-Way Match & Duplicate Invoice Control",
            "accounts_payable",
            "Vendor invoices must match Purchase Order and Receipt within 1.5% variance tolerance. Duplicate vendor invoice numbers or billing within 14 days trigger automated block.",
            json.dumps({"tolerance_pct": 1.5, "duplicate_check_days": 14}),
            "v1.4", "controller_office", True
        ),
        (
            "pol_accrual", "org_apex", "ACCRUE-01", "Prepaid Expense Amortization & Month-End Accruals",
            "close",
            "Prepaid vendor software and hosting contracts exceeding $10,000 must be amortized straight-line over service life. Accruals must post by day 2 of calendar month.",
            json.dumps({"min_capitalization_usd": 10000.00, "method": "straight_line"}),
            "v1.2", "accounting_policy", True
        ),
        (
            "pol_exec_override", "org_apex", "ESC-400", "Executive Financial Authority & Policy Override Matrix",
            "general_finance",
            "Any variance explanation or single transaction adjustment exceeding $50,000, or legal dispute involving credit terms, requires escalation to L4 Controller or CFO signoff.",
            json.dumps({"threshold_usd": 50000.00, "requires_cfo": True}),
            "v1.0", "board_of_directors", True
        ),
    ]
    for pid, oid, pcode, name, dom, desc, rules, ver, src, act in policies:
        db.execute(
            """INSERT INTO policies (id, organization_id, policy_code, name, domain, description, rules, version, source, active)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET rules=EXCLUDED.rules, version=EXCLUDED.version;""",
            (pid, oid, pcode, name, dom, desc, rules, ver, src, act)
        )

    # 6. Finance Records (Invoices, Payments, Bills, JEs, Reconciliations, Schedules)
    records = [
        # Accounts Receivable: Invoices & Payments
        (
            "rec_inv_4471", "org_apex", "sys_netsuite", "invoice", "INV-4471", "Acme Corp",
            12500.00, "USD", "partially_paid", date(2026, 8, 15),
            json.dumps({
                "customer_id": "cust1",
                "po_number": "PO-99120",
                "terms": "2/10 Net 30",
                "due_date": "2026-09-14",
                "items": [{"name": "Enterprise ResolveLoop Cloud Platform - Q3", "qty": 1, "rate": 12500.00}],
                "paid_amount": 12250.00,
                "balance_due": 250.00,
                "notes": "Customer claimed $250 early payment discount per 2/10 Net 30 terms."
            })
        ),
        (
            "rec_pmt_8821", "org_apex", "sys_stripe", "payment", "PMT-8821", "Acme Corp",
            12250.00, "USD", "settled", date(2026, 8, 23),
            json.dumps({
                "customer_id": "cust1",
                "matched_invoice": "INV-4471",
                "invoice_total": 12500.00,
                "short_payment_amount": 250.00,
                "remittance_advice": "Remitted $12,250 net of $250 discount for payment within 10 days of invoice date.",
                "status": "short_payment_identified",
                "resolution_policy": "SHORT-PAY-01"
            })
        ),
        (
            "rec_inv_4472", "org_apex", "sys_netsuite", "invoice", "INV-4472", "Nexus Logistics",
            4800.00, "USD", "overdue", date(2026, 7, 20),
            json.dumps({
                "customer_id": "cust2",
                "po_number": "PO-88102",
                "terms": "Net 30",
                "due_date": "2026-08-19",
                "items": [{"name": "API Data Pipeline Connector Subscriptions", "qty": 4, "rate": 1200.00}],
                "paid_amount": 0.00,
                "balance_due": 4800.00,
                "aging_bucket": "31-60_days"
            })
        ),
        (
            "rec_inv_9001", "org_apex", "sys_netsuite", "invoice", "INV-9001", "Global Health Network",
            180000.00, "USD", "paid", date(2026, 6, 1),
            json.dumps({
                "customer_id": "cust3",
                "contract_id": "CTR-2026-GHN",
                "terms": "Net 45",
                "items": [{"name": "Maximor AI Enterprise Financial Core (Annual)", "qty": 1, "rate": 180000.00}],
                "paid_amount": 180000.00,
                "balance_due": 0.00
            })
        ),

        # Accounts Payable: Vendor Invoices & Bills
        (
            "rec_bill_7701", "org_apex", "sys_netsuite", "bill", "BILL-7701", "Amazon Web Services (AWS)",
            68400.00, "USD", "approved", date(2026, 8, 31),
            json.dumps({
                "vendor_id": "VEND-AWS",
                "budget_amount": 58000.00,
                "variance_amount": 10400.00,
                "variance_pct": 17.93,
                "flux_category": "Cloud Infrastructure Overrun",
                "root_cause": "Increased GPU token throughput on gpt-5-nano inference during live enterprise trials",
                "system_source": "AWS Cost Explorer API -> NetSuite AP"
            })
        ),
        (
            "rec_bill_7702", "org_apex", "sys_netsuite", "bill", "BILL-7702", "Snowflake Data Cloud",
            14200.00, "USD", "pending_approval", date(2026, 9, 1),
            json.dumps({
                "vendor_id": "VEND-SNOW",
                "budget_amount": 15000.00,
                "variance_amount": -800.00,
                "variance_pct": -5.33,
                "status": "within_budget"
            })
        ),

        # Close & Journal Entries
        (
            "rec_je_2026_03", "org_apex", "sys_netsuite", "journal_entry", "JE-2026-03", "Apex Accounting",
            10400.00, "USD", "posted", date(2026, 8, 31),
            json.dumps({
                "memo": "Month-end August Cloud Infrastructure Compute Accrual",
                "lines": [
                    {"account": "6100 - Software & Hosting", "type": "debit", "amount": 10400.00},
                    {"account": "2100 - Accrued Operating Expenses", "type": "credit", "amount": 10400.00}
                ],
                "approved_by": "usr_alice"
            })
        ),

        # Cash & Treasury Position
        (
            "rec_cash_pos", "org_apex", "sys_jpmc", "cash_balance", "CASH-2026-09", "JPMC Treasury",
            18450000.00, "USD", "verified", date(2026, 9, 1),
            json.dumps({
                "operating_checking": 8200000.00,
                "treasury_money_market": 10250000.00,
                "weighted_yield": "5.12%",
                "monthly_burn_net": 650000.00,
                "runway_months": 28.38,
                "13_week_forecast": [
                    {"week": "W1", "projected_inflow": 1250000, "projected_outflow": 820000, "net_end": 18880000},
                    {"week": "W2", "projected_inflow": 450000, "projected_outflow": 910000, "net_end": 18420000},
                    {"week": "W3", "projected_inflow": 890000, "projected_outflow": 730000, "net_end": 18580000}
                ]
            })
        ),

        # Revenue Recognition Schedule (ASC 606)
        (
            "rec_rev_sch_01", "org_apex", "sys_netsuite", "revenue_schedule", "REV-SCH-01", "Global Health Network",
            180000.00, "USD", "active", date(2026, 6, 1),
            json.dumps({
                "customer_id": "cust3",
                "contract_id": "CTR-2026-GHN",
                "rule": "ASC 606 Ratable Recognition",
                "start_date": "2026-06-01",
                "end_date": "2027-05-31",
                "monthly_recognition": 15000.00,
                "recognized_to_date": 45000.00,
                "deferred_revenue_balance": 135000.00
            })
        ),

        # Multi-Entity Consolidation & Reporting
        (
            "rec_consol_01", "org_apex", "sys_netsuite", "reconciliation", "CONSOL-2026-Q2", "Apex Global Group",
            48200000.00, "USD", "completed", date(2026, 6, 30),
            json.dumps({
                "entities": [
                    {"name": "Apex Global Tech Inc (US)", "currency": "USD", "revenue": 34200000.00},
                    {"name": "Apex Technologies UK Ltd", "currency": "GBP", "revenue_gbp": 8100000.00, "fx_rate": 1.28, "revenue_usd": 10368000.00},
                    {"name": "Apex APAC Pte Ltd", "currency": "SGD", "revenue_sgd": 4800000.00, "fx_rate": 0.75, "revenue_usd": 3600000.00}
                ],
                "intercompany_eliminations_usd": -1200000.00,
                "consolidated_revenue_usd": 46968000.00
            })
        ),
    ]

    for rid, oid, fsid, rtype, ext_id, ename, amt, curr, st, dt, data_json in records:
        db.execute(
            """INSERT INTO finance_records (id, organization_id, finance_system_id, record_type, external_id, entity_name, amount, currency, status, transaction_date, data)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET amount=EXCLUDED.amount, status=EXCLUDED.status, data=EXCLUDED.data;""",
            (rid, oid, fsid, rtype, ext_id, ename, amt, curr, st, dt, data_json)
        )

    # 7. Seed Experiences (Closed Learning Loop Memory)
    experiences = [
        (
            "exp_short_pay_01", "org_apex", None, "accounts_receivable",
            "Customer Acme Corp remitted $12,250 on $12,500 invoice INV-4471, short by $250.",
            json.dumps({"invoice_id": "INV-4471", "payment_id": "PMT-8821", "terms": "2/10 Net 30"}),
            "Verified payment date fell within 10-day early discount window. Approved $250 prompt payment discount credit without escalation to Controller.",
            "Invoice marked paid in full; customer statement updated; zero bad-debt write-off.",
            "Policy SHORT-PAY-01 lookup and discount verification succeeded immediately.",
            "Initial L1 attempt failed due to lack of credit authorization authority.",
            "Route short-payment inquiries directly to L2. If payment arrived within 10 calendar days on 2/10 Net 30 terms, auto-apply discount credit.",
            json.dumps(["short_payment", "discount", "2/10_Net_30", "accounts_receivable"]),
            0.96, True
        ),
        (
            "exp_aws_flux_01", "org_apex", None, "reporting",
            "Executive asked why cloud infrastructure expense on BILL-7701 was $10,400 (17.9%) over budget.",
            json.dumps({"bill_id": "BILL-7701", "vendor": "AWS", "budget": 58000.00, "actual": 68400.00}),
            "Extracted Datadog APM metrics and correlated compute surge with OpenAI gpt-5-nano inference volume during enterprise customer onboarding.",
            "CFO approved variance report with complete audit trail; accrual JE-2026-03 confirmed.",
            "Cross-referencing AP bills with system telemetry provided immediate root-cause explanation.",
            "Manual review took 3 days in previous quarter due to disconnected billing records.",
            "For cloud hosting budget variances >15%, retrieve GPU cluster consumption metrics before escalating to FP&A.",
            json.dumps(["variance", "aws", "hosting", "flux_analysis", "reporting"]),
            0.94, True
        )
    ]

    for eid, oid, cid, dom, sit, ctx, act, out, ww, wf, les, tags, conf, reus in experiences:
        db.execute(
            """INSERT INTO experiences (id, organization_id, case_id, domain, situation, context, action_taken, outcome, what_worked, what_failed, lesson, tags, confidence, reusable)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET lesson=EXCLUDED.lesson, confidence=EXCLUDED.confidence;""",
            (eid, oid, cid, dom, sit, ctx, act, out, ww, wf, les, tags, conf, reus)
        )

    logger.info("Successfully seeded synthetic finance database.")

if __name__ == "__main__":
    seed_database()
    print("Maximor Finance synthetic seeds populated successfully.")
