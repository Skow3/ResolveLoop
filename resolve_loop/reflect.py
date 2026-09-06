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

    # Ingest structured failures detected by Evaluator and synthesize strategy changes
    failures = (score_details or {}).get("failures", [])
    recommended_strategy_changes = []

    for f in failures:
        ftype = f.get("failure_type", "FAILURE")
        fdesc = f.get("description", "")
        fev = f.get("evidence", "")
        aff_agent = f.get("affected_agent", "agent_l2_ar")

        if ftype == "WRONG_ESCALATION":
            lesson_text = f"Payment disputes should verify payment and invoice evidence before escalation. (Evidence: {fev})"
            extracted_lessons.append(lesson_text)
            recommended_strategy_changes.append({
                "change_type": "TOOL_ORDER",
                "field": "preferred_tool_order",
                "suggested_value": ["get_invoice", "get_payment", "get_policy_version"],
                "change": "Prioritize payment and invoice verification before escalation",
                "rationale": f"Avoid premature escalation: {fdesc}",
                "affected_agent": aff_agent,
            })
        elif ftype == "TOOL_ORDER":
            lesson_text = f"Tool ordering must follow the verification audit sequence: {fdesc}"
            extracted_lessons.append(lesson_text)
            recommended_strategy_changes.append({
                "change_type": "TOOL_ORDER",
                "field": "preferred_tool_order",
                "suggested_value": ["get_invoice", "get_payment", "get_customer_history", "get_policy_version"],
                "change": "Reorder tools to match standard financial verification sequence",
                "rationale": f"Correct tool order deviation: {fdesc}",
                "affected_agent": aff_agent,
            })
        elif ftype == "MISSING_EVIDENCE":
            lesson_text = f"Required financial documents must be retrieved before resolution: {fdesc}"
            extracted_lessons.append(lesson_text)
            recommended_strategy_changes.append({
                "change_type": "PREFERRED_TOOLS",
                "field": "preferred_tools",
                "suggested_value": ["get_invoice", "get_payment", "get_policy_version"],
                "change": "Mandate retrieval of invoice and payment evidence",
                "rationale": f"Provide complete audit evidence: {fdesc}",
                "affected_agent": aff_agent,
            })
        elif ftype in ("UNNECESSARY_TOOL", "EXCESSIVE_TOOL_USE"):
            lesson_text = f"Optimize tool calls to reduce latency and redundant queries: {fdesc}"
            extracted_lessons.append(lesson_text)
            recommended_strategy_changes.append({
                "change_type": "TOOL_PRUNING",
                "field": "preferred_tools",
                "suggested_value": [t for t in actions if t not in ("fetch_profile", "search_finance_records")][:3],
                "change": "Prune redundant lookup tools to improve execution speed",
                "rationale": f"Reduce excessive tool overhead: {fdesc}",
                "affected_agent": aff_agent,
            })
        elif ftype == "WRONG_ROUTING":
            lesson_text = f"Under-routing detected from initial route L{route_level}: {fdesc}"
            extracted_lessons.append(lesson_text)
            kw = [w for w in case_description.lower().split() if len(w) > 3][:3]
            recommended_strategy_changes.append({
                "change_type": "ROUTING_SIGNALS",
                "field": "routing_signals",
                "suggested_value": kw,
                "change": f"Add routing signals {kw} for direct specialist dispatch",
                "rationale": f"Prevent cold under-routing: {fdesc}",
                "affected_agent": aff_agent,
            })
        elif ftype in ("WRONG_ANSWER", "LOW_CONFIDENCE"):
            lesson_text = f"Strengthen validation checks and policy compliance: {fdesc}"
            extracted_lessons.append(lesson_text)
            recommended_strategy_changes.append({
                "change_type": "INSTRUCTIONS",
                "field": "strategy_instructions",
                "suggested_value": "Cross-reference terms against policy and confirm numbers before answering.",
                "change": "Require strict policy compliance before concluding resolution",
                "rationale": f"Improve answer accuracy: {fdesc}",
                "affected_agent": aff_agent,
            })
        else:
            extracted_lessons.append(f"Structured Failure [{ftype}]: {fdesc} (Evidence: {fev})")

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

    primary_strat_change = recommended_strategy_changes[0] if recommended_strategy_changes else None

    # Record REFLECTION_CREATED audit event
    try:
        from .finance_tools import record_audit_event
        import time as _t
        record_audit_event(
            case_id=case_id,
            action="REFLECTION_CREATED",
            details={
                "source_agent": "Eval Reflection Engine",
                "destination_agent": "Experience Store",
                "handoff_reason": "Reflection synthesis from case execution",
                "confidence": 0.95,
                "context_summary": extracted_lessons[0] if extracted_lessons else "Reflection completed",
                "timestamp": _t.time(),
                "outcome": "Reflection indexed",
                "lessons": extracted_lessons[:3],
                "recommended_route": recommended_route,
                "recommended_strategy_change": primary_strat_change,
            },
            actor_type="system",
            actor_id="reflection_engine"
        )
    except Exception:
        pass

    return {
        "case_id": case_id,
        "lessons": extracted_lessons,
        "recommended_route": recommended_route,
        "recommended_tools": recommended_tools,
        "procedural_rule": procedural_rule,
        "failures_analyzed": failures,
        "recommended_strategy_change": primary_strat_change,
        "recommended_strategy_changes": recommended_strategy_changes,
        "memory_snapshot": memory,
    }
