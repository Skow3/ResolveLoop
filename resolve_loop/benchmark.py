"""Benchmark utilities to evaluate performance and compare behavior pre/post-learning."""
from typing import Dict, Any, List, Optional

class Benchmark:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]):
        self.records.append(entry)

    def _extract_score(self, entry: Dict[str, Any]) -> float:
        score_val = entry.get("score", 0)
        if isinstance(score_val, dict):
            return float(score_val.get("score", 0))
        try:
            return float(score_val)
        except (ValueError, TypeError):
            return 0.0

    def summarize(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        target = records if records is not None else self.records
        total = len(target)
        if total == 0:
            return {
                "total": 0,
                "average_score": 0.0,
                "resolution_rate": 0.0,
                "avg_tools_used": 0.0,
                "escalation_rate": 0.0,
            }

        scores = [self._extract_score(r) for r in target]
        avg_score = sum(scores) / total

        resolved_count = sum(
            1 for r in target
            if r.get("solve", {}).get("resolution", {}).get("resolved", False)
        )
        escalated_count = sum(
            1 for r in target
            if r.get("escalated", False) or r.get("route", {}).get("escalated", False)
        )
        total_actions = sum(
            len(r.get("solve", {}).get("actions", [])) for r in target
        )

        return {
            "total": total,
            "average_score": round(avg_score, 2),
            "resolution_rate": round((resolved_count / total) * 100, 1),
            "avg_tools_used": round(total_actions / total, 2),
            "escalation_rate": round((escalated_count / total) * 100, 1),
        }

    @staticmethod
    def compare(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two benchmark summaries (e.g. cold pass vs warm pass)."""
        score_diff = round(after.get("average_score", 0) - before.get("average_score", 0), 2)
        tool_diff = round(after.get("avg_tools_used", 0) - before.get("avg_tools_used", 0), 2)
        esc_diff = round(after.get("escalation_rate", 0) - before.get("escalation_rate", 0), 1)
        res_diff = round(after.get("resolution_rate", 0) - before.get("resolution_rate", 0), 1)

        return {
            "score_delta": f"{'+' if score_diff >= 0 else ''}{score_diff} pts",
            "tool_usage_delta": f"{'+' if tool_diff >= 0 else ''}{tool_diff} tools/case",
            "escalation_delta": f"{'+' if esc_diff >= 0 else ''}{esc_diff}%",
            "resolution_delta": f"{'+' if res_diff >= 0 else ''}{res_diff}%",
            "learning_confirmed": score_diff >= 0 and esc_diff <= 0,
        }
