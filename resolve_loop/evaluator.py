"""Evaluator that judges resolution quality, routing appropriateness, tool efficiency, and escalation."""
from typing import Dict, Any, List, Optional
from .llm import request_llm

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
    ) -> Dict[str, Any]:
        score = 0
        details = {}

        # 1. Base Resolution Quality (up to 50 points)
        if resolution_success:
            resolution_pts = 50
        else:
            resolution_pts = 10
        score += resolution_pts

        # 2. Tool Efficiency (up to 20 points, rewarding precision over spamming)
        # Optimal number of tools for most customer cases is 1-3.
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
            }
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

        return {"score": score, "details": details}
