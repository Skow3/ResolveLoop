"""Tool wrappers and permission tiers for Maximor AI Finance Operations."""
from typing import Dict, Any, List, Optional
from .case import Case
from .mock_services import (
    get_customer_profile,
    get_customer_history,
    search_knowledge_base,
    lookup_order,
    cancel_order,
    verify_payment,
    issue_refund,
    create_ticket,
)
from .finance_tools import (
    get_customer,
    get_customer_history as get_fin_customer_history,
    get_invoice,
    get_payment,
    get_vendor,
    get_bill,
    get_finance_record,
    search_finance_records,
    search_policy,
    get_policy_version,
    get_journal_entry,
    get_reconciliation,
    get_revenue_schedule,
    get_cash_position,
    get_forecast,
    search_experiences,
    record_feedback,
    record_audit_event,
)

# Legacy / E-commerce Agent Level Permissions (for backward compatibility)
LEVEL_PERMISSIONS = {
    1: ["kb_lookup", "fetch_profile"],
    2: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order"],
    3: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order", "cancel_order", "verify_payment", "issue_refund"],
    4: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order", "cancel_order", "verify_payment", "issue_refund", "policy_override"],
}

# Maximor AI Finance Operations Agent Level Permissions
FINANCE_LEVEL_PERMISSIONS = {
    1: ["get_customer", "search_policy", "get_invoice", "get_payment"],
    2: ["get_customer", "get_customer_history", "get_invoice", "get_payment", "search_policy", "get_policy_version", "get_vendor", "get_bill", "search_finance_records"],
    3: ["get_customer", "get_customer_history", "get_invoice", "get_payment", "search_policy", "get_policy_version", "get_vendor", "get_bill", "search_finance_records", "get_journal_entry", "get_reconciliation", "get_revenue_schedule", "get_cash_position", "get_forecast"],
    4: ["get_customer", "get_customer_history", "get_invoice", "get_payment", "search_policy", "get_policy_version", "get_vendor", "get_bill", "search_finance_records", "get_journal_entry", "get_reconciliation", "get_revenue_schedule", "get_cash_position", "get_forecast", "policy_override", "escalate_to_human"],
}

# Aliases for backward compatibility
def fetch_customer_profile(customer_id: str) -> Dict[str, Any]:
    return get_customer_profile(customer_id)

def fetch_customer_history(customer_id: str) -> Dict[str, Any]:
    return get_customer_history(customer_id)

def kb_search(query: str) -> List[Dict[str, Any]]:
    return search_knowledge_base(query)

def order_lookup(customer_id: str, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return lookup_order(customer_id, order_id)

def order_cancel(order_id: str) -> Dict[str, Any]:
    return cancel_order(order_id)

def payment_verify(customer_id: str, tx_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return verify_payment(customer_id, tx_id)

def payment_refund(customer_id: str, amount: float = 50.0, reason: str = "Customer dispute") -> Dict[str, Any]:
    return issue_refund(customer_id, amount, reason)

def open_ticket_for_case(case: Case, resolution_summary: str) -> str:
    return create_ticket(case, resolution_summary)
