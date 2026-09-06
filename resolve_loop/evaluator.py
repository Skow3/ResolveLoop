"""Evaluator that judges resolution quality, routing appropriateness, tool efficiency, escalation, and structured failures."""
import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from .llm import request_llm
from .db import db

logger = logging.getLogger("maximor.evaluator")

class FailureType:
    WRONG_ROUTING = "WRONG_ROUTING"
    WRONG_ANSWER = "WRONG_ANSWER"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    WRONG_TOOL = "WRONG_TOOL"
    UNNECESSARY_TOOL = "UNNECESSARY_TOOL"
    TOOL_ORDER = "TOOL_ORDER"
    EXCESSIVE_TOOL_USE = "EXCESSIVE_TOOL_USE"
    WRONG_ESCALATION = "WRONG_ESCALATION"
    MISSED_ESCALATION = "MISSED_ESCALATION"
    POLICY_ERROR = "POLICY_ERROR"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    OTHER = "OTHER"

@dataclass
class StructuredFailure:
    failure_type: str
    description: str
    evidence: str
    affected_agent: str
    strategy_version: str
    case_id: str
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Evaluator:
    def __init__(self):
        pass

    def evaluate(
        self,
        case: Dict[str, Any],
        route_level: int,
        actions: List[str],
        escalated: bool,
        resolution_success: bool,
        resolution_notes: str = "",
        strategy: Optional[Any] = None,
        affected_agent: str = "agent_unknown",
        strategy_version: str = "v0",
        confidence: float = 0.90,
    ) -> Dict[str, Any]:
        score = 0
        details = {}
        case_id = case.get("id", "case_unknown")
        desc_lower = (case.get("description") or "").lower()

        # 1. Base Resolution Quality (up to 50 points)
        if resolution_success:
            resolution_pts = 50
        else:
            resolution_pts = 10
        score += resolution_pts

        # 2. Tool Efficiency (up to 20 points, rewarding precision over spamming)
        num_tools = len(actions)
        if 1 <= num_tools <= 3:
            tool_efficiency_pts = 20
        elif num_tools == 0:
            tool_efficiency_pts = 5  # No tools called when resolution was needed
        else:
            tool_efficiency_pts = max(0, 20 - (num_tools - 3) * 5)
        score += tool_efficiency_pts

        # 3. Escalation Penalty / First-Contact Resolution (up to 15 points)
        if not escalated:
            fcr_pts = 15  # Solved directly at the routed level!
        else:
            fcr_pts = -5  # Required runtime escalation due to under-routing
        score += fcr_pts

        # 4. Route Appropriateness (up to 15 points)
        priority = str(case.get("priority", "medium")).lower()
        if priority in ("high", "critical") and route_level >= 3:
            route_pts = 15
        elif priority == "low" and route_level == 1:
            route_pts = 15
        elif priority == "medium" and route_level in (2, 3):
            route_pts = 15
        else:
            route_pts = 5
        score += route_pts

        # Score Capping
        score = max(0, min(100, score))

        # =========================================================================
        # 5. STRUCTURED FAILURE DETECTION
        # =========================================================================
        failures: List[StructuredFailure] = []

        # Check: Unresolved Answer
        if not resolution_success:
            failures.append(StructuredFailure(
                failure_type=FailureType.WRONG_ANSWER,
                description="Agent failed to produce a valid, verified financial resolution.",
                evidence=resolution_notes[:150] if resolution_notes else "Resolution marked unverified",
                affected_agent=affected_agent,
                strategy_version=strategy_version,
                case_id=case_id,
            ))

        # Check: Escalation failures (WRONG_ESCALATION vs WRONG_ROUTING)
        if escalated:
            # Did it escalate before checking required evidence?
            required_evidence_tools = ["get_invoice", "get_payment", "get_customer"]
            has_evidence = any(t in actions for t in ["get_invoice", "get_payment", "order_lookup", "verify_payment"])
            if not has_evidence and any(k in desc_lower for k in ["invoice", "payment", "short", "bill"]):
                failures.append(StructuredFailure(
                    failure_type=FailureType.WRONG_ESCALATION,
                    description="Agent escalated before verifying required payment and invoice status.",
                    evidence=f"Escalated with tools called: {actions}. Missing primary evidence tools.",
                    affected_agent=affected_agent,
                    strategy_version=strategy_version,
                    case_id=case_id,
                ))
            else:
                failures.append(StructuredFailure(
                    failure_type=FailureType.WRONG_ROUTING,
                    description=f"Case initially routed to L{route_level} requiring runtime escalation.",
                    evidence=f"Initial route L{route_level} lacked tool authority for domain request.",
                    affected_agent=affected_agent,
                    strategy_version=strategy_version,
                    case_id=case_id,
                ))

        # Check: Missing Evidence
        if any(k in desc_lower for k in ["short payment", "short-pay", "pmt-8821", "inv-4471"]):
            if "get_invoice" not in actions or "get_payment" not in actions:
                missing = [t for t in ["get_invoice", "get_payment"] if t not in actions]
                failures.append(StructuredFailure(
                    failure_type=FailureType.MISSING_EVIDENCE,
                    description=f"Short payment investigation missing required financial documents: {', '.join(missing)}.",
                    evidence=f"Actions executed: {actions}",
                    affected_agent=affected_agent,
                    strategy_version=strategy_version,
                    case_id=case_id,
                ))

        # Check: Tool Ordering deviation
        if strategy and getattr(strategy, "preferred_tool_order", None):
            expected_order = [t for t in strategy.preferred_tool_order if t in actions]
            actual_order = [t for t in actions if t in expected_order]
            if actual_order != expected_order:
                failures.append(StructuredFailure(
                    failure_type=FailureType.TOOL_ORDER,
                    description="Tool execution sequence deviated from strategy preferred order.",
                    evidence=f"Actual sequence: {actual_order} vs Preferred sequence: {expected_order}",
                    affected_agent=affected_agent,
                    strategy_version=strategy_version,
                    case_id=case_id,
                ))

        # Check: Excessive Tool Use
        if num_tools > 4:
            failures.append(StructuredFailure(
                failure_type=FailureType.EXCESSIVE_TOOL_USE,
                description=f"Agent invoked {num_tools} tools, exceeding standard operational efficiency threshold (1-3 tools).",
                evidence=f"Executed tool list: {actions}",
                affected_agent=affected_agent,
                strategy_version=strategy_version,
                case_id=case_id,
            ))

        # Check: Low Confidence
        if confidence < 0.70:
            failures.append(StructuredFailure(
                failure_type=FailureType.LOW_CONFIDENCE,
                description=f"Resolution confidence ({confidence:.2f}) below acceptable enterprise threshold (0.70).",
                evidence=f"Assigned confidence score: {confidence}",
                affected_agent=affected_agent,
                strategy_version=strategy_version,
                case_id=case_id,
            ))

        # Persist structured failures into PostgreSQL if DB is available
        for f in failures:
            try:
                db.execute(
                    """INSERT INTO structured_failures (id, case_id, failure_type, description, evidence, affected_agent, strategy_version, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        f"fail_{uuid.uuid4().hex[:12]}", f.case_id, f.failure_type,
                        f.description, f.evidence, f.affected_agent, f.strategy_version,
                        json.dumps(f.metadata)
                    )
                )
            except Exception:
                pass

        details = {
            "score_breakdown": {
                "resolution_quality": resolution_pts,
                "tool_efficiency": tool_efficiency_pts,
                "first_contact_resolution": fcr_pts,
                "route_appropriateness": route_pts,
            },
            "metrics": {
                "route_level": route_level,
                "tools_used": num_tools,
                "escalated": escalated,
                "resolved": resolution_success,
                "strategy_version": strategy_version,
                "failure_count": len(failures),
            },
            "failures": [f.to_dict() for f in failures],
        }

        # Optional LLM evaluation when configured
        llm_feedback = None
        prompt = (
            f"Evaluate customer support outcome: Case: '{case.get('description')}'. "
            f"Priority: {case.get('priority')}. Assigned Route: L{route_level}. "
            f"Tools Used: {actions}. Escalated: {escalated}. Resolved: {resolution_success}. "
            "Give a brief 1-sentence evaluation verdict."
        )
        llm_out = request_llm(prompt, system_prompt="You are the ResolveLoop Support Quality Evaluator.")
        if llm_out:
            details["llm_verdict"] = llm_out.strip()

        return {"score": score, "details": details, "failures": [f.to_dict() for f in failures]}
