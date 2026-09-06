"""Evaluator that judges resolution quality, routing, tool usage, and escalation."""
from typing import Dict, Any, List

class Evaluator:
    def __init__(self):
        pass

    def evaluate(self, case: Dict[str, Any], route_level: int, actions: List[str], escalated: bool, resolution_success: bool) -> Dict[str, Any]:
        score = 0
        details = {}
        # Basic scoring heuristics
        if resolution_success:
            score += 40
        else:
            score += 10

        score += max(0, 20 - len(actions) * 2)  # prefer fewer, targeted tool calls

        if route_level >= 3:
            score += 5  # cautious routing may help complex cases
        if escalated:
            score -= 5  # escalation may reduce immediacy
        # Cap
        score = max(0, min(100, score))
        details.update({"score_breakdown": {
            "base": 40 if resolution_success else 10,
            "tool_efficiency": max(0, 20 - len(actions)*2),
            "route_safety": 5 if route_level >= 3 else 0,
            "escalation_penalty": -5 if escalated else 0,
        }})
        return {"score": score, "details": details}
