"""Mock external services: CRM/Customer, Knowledge Base, Orders, Payments, and Ticketing."""
from typing import Dict, Any, List, Optional
from .case import Case

# Mock Database
_PROFILES = {
    "cust1": {"name": "Alice", "segment": "premium", "email": "alice@example.com"},
    "cust2": {"name": "Bob", "segment": "standard", "email": "bob@example.com"},
    "cust3": {"name": "Charlie", "segment": "enterprise", "email": "charlie@corp.com"},
}

_HISTORIES = {
    "cust1": {"tickets": ["T1001", "T1010"], "issues": ["login", "billing"], "lifetime_value": 1200},
    "cust2": {"tickets": ["T2001"], "issues": ["setup"], "lifetime_value": 150},
    "cust3": {"tickets": ["T3001", "T3005"], "issues": ["contract", "api_limits"], "lifetime_value": 15000},
}

_ORDERS = {
    "ORD-101": {"customer_id": "cust1", "status": "shipped", "tracking": "TRK992123", "items": ["Wireless Headphones"], "amount": 89.99},
    "ORD-102": {"customer_id": "cust2", "status": "processing", "tracking": "PENDING", "items": ["USB-C Dock"], "amount": 45.00},
    "ORD-103": {"customer_id": "cust1", "status": "delivered", "tracking": "TRK881200", "items": ["Ergonomic Keyboard"], "amount": 129.50},
}

_PAYMENTS = {
    "TX-901": {"order_id": "ORD-101", "customer_id": "cust1", "status": "settled", "amount": 89.99, "currency": "USD"},
    "TX-902": {"order_id": "ORD-102", "customer_id": "cust2", "status": "authorized", "amount": 45.00, "currency": "USD"},
    "TX-903": {"order_id": "ORD-103", "customer_id": "cust1", "status": "settled", "amount": 129.50, "currency": "USD"},
}

_KB = [
    {"id": "KB001", "title": "Password reset and recovery", "snippet": "Users can reset passwords via profile security tab or email link."},
    {"id": "KB002", "title": "Order tracking and delivery updates", "snippet": "Track shipment status using the tracking code provided in shipping confirmation email."},
    {"id": "KB003", "title": "Cancellation policy", "snippet": "Orders in 'processing' status can be cancelled immediately. Shipped orders must be returned."},
    {"id": "KB004", "title": "Refund policy and dispute resolution", "snippet": "Refunds take 3-5 business days to post to original payment method after approval."},
    {"id": "KB005", "title": "Account lockout and security breach", "snippet": "Locked accounts require L3/L4 identity verification and manual unlock procedure."},
]

def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    return _PROFILES.get(customer_id, {"name": "Unknown", "segment": "standard", "email": "unknown@example.com"})

def get_customer_history(customer_id: str) -> Dict[str, Any]:
    return _HISTORIES.get(customer_id, {"tickets": [], "issues": [], "lifetime_value": 0})

def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    q = query.lower()
    q_words = set(q.split())
    hits = []
    for item in _KB:
        haystack = f"{item['title']} {item['snippet']}".lower()
        if any(w in haystack for w in q_words if len(w) > 2):
            hits.append(item)
    return hits

def lookup_order(customer_id: str, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
    results = []
    for oid, details in _ORDERS.items():
        if order_id and oid.lower() == order_id.lower():
            results.append({"order_id": oid, **details})
        elif not order_id and details["customer_id"] == customer_id:
            results.append({"order_id": oid, **details})
    return results

def cancel_order(order_id: str) -> Dict[str, Any]:
    if order_id in _ORDERS:
        order = _ORDERS[order_id]
        if order["status"] in ("processing", "pending"):
            order["status"] = "cancelled"
            return {"success": True, "order_id": order_id, "status": "cancelled", "message": "Order successfully cancelled."}
        return {"success": False, "order_id": order_id, "status": order["status"], "message": f"Cannot cancel order in '{order['status']}' status. Please initiate a return."}
    return {"success": False, "order_id": order_id, "message": "Order ID not found."}

def verify_payment(customer_id: str, tx_id: Optional[str] = None) -> List[Dict[str, Any]]:
    results = []
    for tid, details in _PAYMENTS.items():
        if tx_id and tid.lower() == tx_id.lower():
            results.append({"tx_id": tid, **details})
        elif not tx_id and details["customer_id"] == customer_id:
            results.append({"tx_id": tid, **details})
    return results

def issue_refund(customer_id: str, amount: float, reason: str) -> Dict[str, Any]:
    refund_id = f"REF-{customer_id.upper()}-{int(amount)}"
    return {
        "success": True,
        "refund_id": refund_id,
        "amount": amount,
        "customer_id": customer_id,
        "status": "refund_approved",
        "reason": reason,
        "eta": "3-5 business days",
    }

def create_ticket(case: Case, resolution: str) -> str:
    return f"T-{case.customer_id.upper()}-{case.id}"
