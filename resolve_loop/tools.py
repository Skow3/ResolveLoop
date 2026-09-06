"""Tool wrappers to simulate actions against external systems."""
from typing import Dict, Any, List
from .case import Case
from .mock_services import (
    get_customer_history,
    search_knowledge_base,
    create_ticket,
)

def fetch_customer_history(customer_id: str) -> Dict[str, Any]:
    return get_customer_history(customer_id)

def kb_search(query: str) -> List[Dict[str, Any]]:
    return search_knowledge_base(query)

def open_ticket_for_case(case: Case, resolution_summary: str) -> str:
    return create_ticket(case, resolution_summary)
