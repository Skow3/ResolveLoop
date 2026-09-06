"""Simple benchmark utilities to compare behavior pre/post-learning."""
from typing import Dict, Any, List

class Benchmark:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]):
        self.records.append(entry)

    def summarize(self) -> Dict[str, Any]:
        total = len(self.records)
        if total == 0:
            return {"total": 0}
        avg_score = sum(r.get("score", 0) for r in self.records) / total
        return {"total": total, "average_score": avg_score}
