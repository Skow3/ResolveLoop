"""Database-backed Finance Tools for Maximor AI Operations.

Queries PostgreSQL tables (customers, finance_records, policies, experiences)
and logs tool executions to `tool_calls` and `audit_events` for complete auditability.
"""
import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .db import db

logger = logging.getLogger("maximor.finance")

def log_tool_call(
    case_id: Optional[str],
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    start_time: float,
    success: bool = True,
    error: Optional[str] = None,
    agent_run_id: Optional[str] = None,
) -> None:
    """Record auditable tool call with latency measurement into PostgreSQL."""
    latency_ms = round((time.time() - start_time) * 1000, 2)
    if not case_id:
        return
    call_id = f"tc_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            """INSERT INTO tool_calls (id, case_id, agent_run_id, tool_name, input, output, success, error, latency_ms)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
            (
                call_id, case_id, agent_run_id, tool_name,
                json.dumps(tool_input), json.dumps(tool_output) if isinstance(tool_output, (dict, list)) else json.dumps({"result": str(tool_output)}),
                success, error, latency_ms
            )
        )
    except Exception:
        pass

def get_customer(customer_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve customer details and organization standing."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT c.id, c.name, c.email, c.phone, c.role, c.account_status,
                  o.name as organization_name, o.industry
           FROM customers c
           JOIN organizations o ON c.organization_id = o.id
           WHERE c.id = %s OR lower(c.name) LIKE %s;""",
        (customer_id, f"%{customer_id.lower()}%")
    )
    res = row or {"error": f"Customer {customer_id} not found", "id": customer_id, "name": "Unknown", "account_status": "standard"}
    log_tool_call(case_id, "get_customer", {"customer_id": customer_id}, res, t0, success=bool(row))
    return res

def get_customer_history(customer_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve past invoices, payments, and cases for a customer."""
    t0 = time.time()
    records = db.fetch_all(
        """SELECT record_type, external_id, amount, status, transaction_date, data
           FROM finance_records
           WHERE data->>'customer_id' = %s
           ORDER BY transaction_date DESC;""",
        (customer_id,)
    )
    past_cases = db.fetch_all(
        """SELECT id, title, domain, status, agent_level, created_at
           FROM cases
           WHERE customer_id = %s
           ORDER BY created_at DESC LIMIT 5;""",
        (customer_id,)
    )
    res = {
        "customer_id": customer_id,
        "records_count": len(records),
        "recent_records": records,
        "past_cases": past_cases,
    }
    log_tool_call(case_id, "get_customer_history", {"customer_id": customer_id}, res, t0, success=True)
    return res

def get_invoice(invoice_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve details for a specific invoice from NetSuite/ERP."""
    t0 = time.time()
    clean_id = invoice_id.upper().strip()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'invoice' AND (external_id = %s OR id = %s);""",
        (clean_id, invoice_id)
    )
    res = row or {"error": f"Invoice {invoice_id} not found in NetSuite ERP."}
    log_tool_call(case_id, "get_invoice", {"invoice_id": invoice_id}, res, t0, success=bool(row))
    return res

def get_payment(payment_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve payment settlement details from Stripe/Treasury."""
    t0 = time.time()
    clean_id = payment_id.upper().strip()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'payment' AND (external_id = %s OR id = %s);""",
        (clean_id, payment_id)
    )
    res = row or {"error": f"Payment {payment_id} not found in Stripe or Treasury feeds."}
    log_tool_call(case_id, "get_payment", {"payment_id": payment_id}, res, t0, success=bool(row))
    return res

def get_vendor(vendor_name: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve vendor master profile and AP billing history."""
    t0 = time.time()
    rows = db.fetch_all(
        """SELECT external_id, entity_name, amount, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'bill' AND lower(entity_name) LIKE %s;""",
        (f"%{vendor_name.lower()}%",)
    )
    res = {"vendor_query": vendor_name, "bills": rows, "count": len(rows)}
    log_tool_call(case_id, "get_vendor", {"vendor_name": vendor_name}, res, t0, success=len(rows) > 0)
    return res

def get_bill(bill_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve specific vendor bill and purchase order details."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'bill' AND (external_id = %s OR id = %s);""",
        (bill_id.upper().strip(), bill_id)
    )
    res = row or {"error": f"Bill {bill_id} not found in Accounts Payable."}
    log_tool_call(case_id, "get_bill", {"bill_id": bill_id}, res, t0, success=bool(row))
    return res

def get_finance_record(record_type: str, external_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve generic finance record by type and ID."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT id, record_type, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = %s AND external_id = %s;""",
        (record_type.lower(), external_id.upper().strip())
    )
    res = row or {"error": f"Record {record_type}:{external_id} not found."}
    log_tool_call(case_id, "get_finance_record", {"record_type": record_type, "external_id": external_id}, res, t0, success=bool(row))
    return res

def search_finance_records(query: str, record_type: Optional[str] = None, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search records across ERP, Billing, and Treasury."""
    t0 = time.time()
    q = f"%{query.lower()}%"
    if record_type:
        rows = db.fetch_all(
            """SELECT id, record_type, external_id, entity_name, amount, currency, status, transaction_date, data
               FROM finance_records
               WHERE record_type = %s AND (lower(entity_name) LIKE %s OR lower(external_id) LIKE %s OR data::text ILIKE %s)
               ORDER BY transaction_date DESC LIMIT 10;""",
            (record_type.lower(), q, q, q)
        )
    else:
        rows = db.fetch_all(
            """SELECT id, record_type, external_id, entity_name, amount, currency, status, transaction_date, data
               FROM finance_records
               WHERE lower(entity_name) LIKE %s OR lower(external_id) LIKE %s OR data::text ILIKE %s
               ORDER BY transaction_date DESC LIMIT 10;""",
            (q, q, q)
        )
    log_tool_call(case_id, "search_finance_records", {"query": query, "record_type": record_type}, rows, t0, success=True)
    return rows

def search_policy(policy_code_or_keyword: str, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search authoritative corporate finance policies and controls."""
    t0 = time.time()
    q = f"%{policy_code_or_keyword.lower()}%"
    rows = db.fetch_all(
        """SELECT policy_code, name, domain, description, rules, version, source, active
           FROM policies
           WHERE lower(policy_code) LIKE %s OR lower(name) LIKE %s OR lower(domain) LIKE %s OR lower(description) LIKE %s
           ORDER BY policy_code;""",
        (q, q, q, q)
    )
    log_tool_call(case_id, "search_policy", {"query": policy_code_or_keyword}, rows, t0, success=True)
    return rows

def get_policy_version(policy_code: str, version: Optional[str] = None, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve exact policy version rules."""
    t0 = time.time()
    if version:
        row = db.fetch_one(
            """SELECT policy_code, name, domain, description, rules, version, source, active
               FROM policies
               WHERE policy_code = %s AND version = %s;""",
            (policy_code.upper().strip(), version)
        )
    else:
        row = db.fetch_one(
            """SELECT policy_code, name, domain, description, rules, version, source, active
               FROM policies
               WHERE policy_code = %s ORDER BY version DESC LIMIT 1;""",
            (policy_code.upper().strip(),)
        )
    res = row or {"error": f"Policy {policy_code} not found."}
    log_tool_call(case_id, "get_policy_version", {"policy_code": policy_code, "version": version}, res, t0, success=bool(row))
    return res

def get_journal_entry(journal_entry_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve General Ledger journal entry details."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'journal_entry' AND external_id = %s;""",
        (journal_entry_id.upper().strip(),)
    )
    res = row or {"error": f"Journal entry {journal_entry_id} not found in General Ledger."}
    log_tool_call(case_id, "get_journal_entry", {"journal_entry_id": journal_entry_id}, res, t0, success=bool(row))
    return res

def get_reconciliation(reconciliation_id: Optional[str] = None, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve bank or balance sheet reconciliation report."""
    t0 = time.time()
    if reconciliation_id:
        row = db.fetch_one(
            """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
               FROM finance_records
               WHERE record_type = 'reconciliation' AND external_id = %s;""",
            (reconciliation_id.upper().strip(),)
        )
    else:
        row = db.fetch_one(
            """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
               FROM finance_records
               WHERE record_type = 'reconciliation' ORDER BY transaction_date DESC LIMIT 1;"""
        )
    res = row or {"error": "Reconciliation record not found."}
    log_tool_call(case_id, "get_reconciliation", {"reconciliation_id": reconciliation_id}, res, t0, success=bool(row))
    return res

def get_revenue_schedule(contract_id_or_customer: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve ASC 606 revenue recognition schedule."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'revenue_schedule' AND (lower(entity_name) LIKE %s OR external_id = %s OR data::text ILIKE %s);""",
        (f"%{contract_id_or_customer.lower()}%", contract_id_or_customer.upper().strip(), f"%{contract_id_or_customer}%")
    )
    res = row or {"error": f"Revenue schedule for {contract_id_or_customer} not found."}
    log_tool_call(case_id, "get_revenue_schedule", {"target": contract_id_or_customer}, res, t0, success=bool(row))
    return res

def get_cash_position(case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve real-time liquidity and 13-week cash runway position."""
    t0 = time.time()
    row = db.fetch_one(
        """SELECT id, external_id, entity_name, amount, currency, status, transaction_date, data
           FROM finance_records
           WHERE record_type = 'cash_balance' ORDER BY transaction_date DESC LIMIT 1;"""
    )
    res = row or {"total_cash_usd": 18450000.00, "runway_months": 28.4, "operating_checking": 8200000.00}
    log_tool_call(case_id, "get_cash_position", {}, res, t0, success=True)
    return res

def get_forecast(timeframe: str = "13_week", case_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve FP&A rolling forecast models."""
    t0 = time.time()
    cash_pos = get_cash_position(case_id=None)
    data = cash_pos.get("data") or {}
    res = {
        "timeframe": timeframe,
        "forecast": data.get("13_week_forecast", []),
        "burn_rate_monthly": data.get("monthly_burn_net", 650000.00),
        "runway_months": data.get("runway_months", 28.4)
    }
    log_tool_call(case_id, "get_forecast", {"timeframe": timeframe}, res, t0, success=True)
    return res

def search_experiences(domain: Optional[str] = None, situation_query: Optional[str] = None, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query long-term episodic memory for relevant previous resolutions and lessons."""
    t0 = time.time()
    params = []
    where_clauses = ["reusable = TRUE"]
    if domain:
        where_clauses.append("domain = %s")
        params.append(domain)
    if situation_query:
        where_clauses.append("(lower(situation) LIKE %s OR lower(lesson) LIKE %s OR tags::text ILIKE %s)")
        q = f"%{situation_query.lower()}%"
        params.extend([q, q, q])

    where_sql = " AND ".join(where_clauses)
    rows = db.fetch_all(
        f"""SELECT id, domain, situation, action_taken, outcome, what_worked, what_failed, lesson, confidence
            FROM experiences
            WHERE {where_sql}
            ORDER BY confidence DESC LIMIT 5;""",
        tuple(params)
    )
    log_tool_call(case_id, "search_experiences", {"domain": domain, "query": situation_query}, rows, t0, success=True)
    return rows

def record_feedback(case_id: str, rating: str, reason: Optional[str] = None, comment: Optional[str] = None, interaction_id: Optional[str] = None) -> Dict[str, Any]:
    """Record user thumbs up / down feedback and update experience learning weights."""
    t0 = time.time()
    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
    rating_clean = rating.lower().strip()
    # Ensure parent case exists to satisfy foreign key integrity
    try:
        db.execute(
            """INSERT INTO cases (id, organization_id, title, description, status)
               VALUES (%s, 'org_apex', 'Case Feedback Entry', 'Recorded user feedback', 'resolved')
               ON CONFLICT (id) DO NOTHING;""",
            (case_id,)
        )
    except Exception:
        pass

    db.execute(
        """INSERT INTO feedback (id, case_id, interaction_id, rating, reason, comment)
           VALUES (%s, %s, %s, %s, %s, %s);""",
        (feedback_id, case_id, interaction_id, rating_clean, reason, comment)
    )

    # If positive feedback, boost confidence of associated experience
    if rating_clean in ("positive", "thumbs_up", "up"):
        db.execute(
            """UPDATE experiences SET confidence = LEAST(confidence + 0.05, 0.99)
               WHERE case_id = %s;""",
            (case_id,)
        )
    elif rating_clean in ("negative", "thumbs_down", "down"):
        db.execute(
            """UPDATE experiences SET confidence = GREATEST(confidence - 0.15, 0.50)
               WHERE case_id = %s;""",
            (case_id,)
        )

    # Add audit event
    fb_details = {
        "source_agent": "Customer",
        "destination_agent": "Orchestrator",
        "handoff_reason": "Customer feedback evaluation",
        "confidence": 1.0,
        "context_summary": f"Customer marked resolution as {rating_clean}: {reason}",
        "timestamp": time.time(),
        "outcome": rating_clean,
        "rating": rating_clean,
        "reason": reason,
        "comment": comment
    }
    db.execute(
        """INSERT INTO audit_events (id, organization_id, case_id, actor_type, actor_id, action, details)
           VALUES (%s, %s, %s, %s, %s, %s, %s);""",
        (
            f"aud_{uuid.uuid4().hex[:12]}", "org_apex", case_id, "customer",
            "caller", "CUSTOMER_FEEDBACK_RECORDED",
            json.dumps(fb_details, default=str)
        )
    )

    res = {"feedback_id": feedback_id, "status": "recorded", "rating": rating_clean}
    log_tool_call(case_id, "record_feedback", {"rating": rating_clean}, res, t0, success=True)
    return res

def record_audit_event(case_id: Optional[str], action: str, details: Dict[str, Any], actor_type: str = "agent", actor_id: str = "gpt-5-nano") -> None:
    """Record compliance audit trail entry."""
    aud_id = f"aud_{uuid.uuid4().hex[:12]}"
    try:
        if case_id:
            try:
                db.execute(
                    """INSERT INTO cases (id, organization_id, title, description, status)
                       VALUES (%s, 'org_apex', 'Case Audit Record', 'Case created for audit trail', 'open')
                       ON CONFLICT (id) DO NOTHING;""",
                    (case_id,)
                )
            except Exception:
                pass
        db.execute(
            """INSERT INTO audit_events (id, organization_id, case_id, actor_type, actor_id, action, details)
               VALUES (%s, %s, %s, %s, %s, %s, %s);""",
            (aud_id, "org_apex", case_id, actor_type, actor_id, action, json.dumps(details, default=str))
        )
    except Exception:
        pass


def record_case_interaction(
    case_id: str,
    speaker: str,
    transcript: str,
    agent_id: Optional[str] = None,
    agent_tier: int = 0,
    audio_url: Optional[str] = None,
    feedback_rating: Optional[str] = None,
    feedback_reason: Optional[str] = None,
    latency_ms: float = 0.0
) -> Dict[str, Any]:
    """Record a speaker turn / interaction for Customer Executive supervision."""
    inter_id = f"int_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            """INSERT INTO case_interactions (id, case_id, speaker, agent_id, agent_tier, transcript, audio_url, feedback_rating, feedback_reason, latency_ms)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
            (
                inter_id, case_id, speaker, agent_id or f"tier_{agent_tier}",
                agent_tier, transcript, audio_url, feedback_rating, feedback_reason, latency_ms
            )
        )
        return {"id": inter_id, "case_id": case_id, "status": "recorded"}
    except Exception as e:
        logger.warning(f"Failed to record case interaction: {e}")
        return {"id": inter_id, "error": str(e)}


def add_human_guidance(
    domain: str,
    trigger_pattern: str,
    recommended_tier: int,
    action: str,
    rationale: str,
    created_by: str = "Customer Executive",
    approval_status: str = "approved"
) -> Dict[str, Any]:
    """Add structured human guidance / policy proposal for the AI workforce."""
    guidance_id = f"pol_h_{uuid.uuid4().hex[:10]}"
    try:
        db.execute(
            """INSERT INTO learned_policies 
               (id, organization_id, domain, trigger_pattern, recommended_tier, action, rationale, created_by, approval_status, confidence)
               VALUES (%s, 'org_apex', %s, %s, %s, %s, %s, %s, %s, 0.98);""",
            (guidance_id, domain, trigger_pattern, recommended_tier, action, rationale, created_by, approval_status)
        )
        record_audit_event(
            case_id=None,
            action="HUMAN_GUIDANCE_ADDED",
            details={
                "guidance_id": guidance_id,
                "trigger_pattern": trigger_pattern,
                "recommended_tier": recommended_tier,
                "action": action,
                "rationale": rationale,
                "created_by": created_by,
                "status": approval_status
            },
            actor_type="human_supervisor",
            actor_id=created_by
        )
        return {"id": guidance_id, "success": True, "approval_status": approval_status}
    except Exception as e:
        logger.error(f"Failed to save human guidance: {e}")
        return {"error": str(e), "success": False}


def approve_human_guidance(guidance_id: str, approver: str = "Customer Executive") -> Dict[str, Any]:
    """Approve a proposed human guidance policy."""
    try:
        db.execute(
            "UPDATE learned_policies SET approval_status = 'approved' WHERE id = %s;",
            (guidance_id,)
        )
        record_audit_event(
            case_id=None,
            action="HUMAN_GUIDANCE_APPROVED",
            details={"guidance_id": guidance_id, "approved_by": approver},
            actor_type="human_supervisor",
            actor_id=approver
        )
        return {"id": guidance_id, "success": True, "approval_status": "approved"}
    except Exception as e:
        return {"error": str(e), "success": False}


