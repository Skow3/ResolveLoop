"""Tool wrappers to simulate actions against external systems with permission tiers."""
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

# Agent Level Permissions
LEVEL_PERMISSIONS = {
    1: ["kb_lookup", "fetch_profile"],
    2: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order"],
    3: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order", "cancel_order", "verify_payment", "issue_refund"],
    4: ["kb_lookup", "fetch_profile", "fetch_history", "lookup_order", "cancel_order", "verify_payment", "issue_refund", "policy_override"],
}

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
