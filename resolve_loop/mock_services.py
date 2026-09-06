"""Mock external services: customer history, knowledge base, ticketing."""
from typing import Dict, Any, List
from .case import Case

def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    # Simple deterministic profile
    profiles = {
        "cust1": {"name": "Alice", "segment": "premium"},
        "cust2": {"name": "Bob", "segment": "standard"},
    }
    return profiles.get(customer_id, {"name": "Unknown", "segment": "unknown"})

def get_customer_history(customer_id: str) -> Dict[str, Any]:
    histories = {
        "cust1": {"tickets": ["T1001", "T1010"], "issues": ["login", "billing"]},
        "cust2": {"tickets": ["T2001"], "issues": ["setup"]},
    }
    return histories.get(customer_id, {"tickets": [], "issues": []})

def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    # Very small KB
    kb = [
        {"id": "KB001", "title": "Password reset", "snippet": "How to reset password"},
        {"id": "KB002", "title": "Billing dispute", "snippet": "Chargeback and refunds"},
        {"id": "KB003", "title": "Account lockout", "snippet": "Temporary lock"},
    ]
    # naive hint: return items whose title or snippet contains a word in query
    q = query.lower()
    return [item for item in kb if any(w in (item["title"] + item["snippet"]).lower() for w in q.split())]

def create_ticket(case: Case, resolution: str) -> str:
    # simple ticket id generator
    return f"T-{case.customer_id.upper()}-{case.id}"
