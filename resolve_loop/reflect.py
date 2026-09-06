"""Reflection module to articulate lessons learned, procedural rules, and policy improvements."""
from typing import Dict, Any, List, Optional
from .llm import request_llm

def reflect(
    case_id: str,
    memory: Dict[str, Any],
    lessons: List[str],
    case_description: str = "",
    route_level: int = 1,
    escalated: bool = False,
    actions: Optional[List[str]] = None,
    resolved: bool = True,
    score_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Analyze execution trajectory and extract actionable lessons for future cases."""
    actions = actions or []
    extracted_lessons = list(lessons)
    recommended_route = route_level
    procedural_rule = None

    # Determine recommended route based on experience
    if escalated:
        recommended_route = min(4, route_level + 1)
        extracted_lessons.append(
            f"Case required escalation from L{route_level}. Similar future cases should route directly to L{recommended_route}."
        )
    elif not resolved:
        recommended_route = min(4, route_level + 1)
        extracted_lessons.append(
            f"Case was unresolved at L{route_level}. Escalate routing level to L{recommended_route} for higher authority."
        )
    else:
        extracted_lessons.append(f"Successful resolution confirmed at L{route_level}.")

    # Synthesize procedural rules for high-frequency patterns
    desc_lower = case_description.lower()
    if any(k in desc_lower for k in ["refund", "billing", "charge", "dispute"]):
        procedural_rule = {"pattern": "billing_or_refund", "target_level": 3, "required_tools": ["lookup_order", "verify_payment", "issue_refund"]}
        recommended_route = max(recommended_route, 3)
    elif any(k in desc_lower for k in ["cancel", "tracking", "status", "shipment"]):
        procedural_rule = {"pattern": "order_management", "target_level": 2, "required_tools": ["lookup_order", "cancel_order"]}
        recommended_route = max(recommended_route, 2)
    elif any(k in desc_lower for k in ["legal", "risk", "policy", "fraud", "lockout"]):
        procedural_rule = {"pattern": "executive_risk", "target_level": 4, "required_tools": ["policy_override"]}
        recommended_route = 4

    # Determine targeted tools (pruning redundant actions)
    recommended_tools = actions if resolved else list(set(actions + (procedural_rule["required_tools"] if procedural_rule else [])))

    # Optional LLM reflection if enabled
    llm_reflection = None
    llm_prompt = (
        f"Case: '{case_description}'. Route: L{route_level}. Escalated: {escalated}. Resolved: {resolved}. "
        f"Actions taken: {actions}. Score details: {score_details}. "
        "Provide a 1-sentence strategic reflection on how routing or tool selection should adapt for similar cases."
    )
    llm_out = request_llm(llm_prompt, system_prompt="You are the ResolveLoop Reflection Engine.")
    if llm_out:
        llm_reflection = llm_out.strip()
        extracted_lessons.append(f"LLM Reflection: {llm_reflection}")

    return {
        "case_id": case_id,
        "lessons": extracted_lessons,
        "recommended_route": recommended_route,
        "recommended_tools": recommended_tools,
        "procedural_rule": procedural_rule,
        "memory_snapshot": memory,
    }
