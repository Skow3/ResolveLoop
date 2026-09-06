"""Experience store to persist useful experiences."""
import json
from pathlib import Path
from typing import Dict, Any, List
from .config import EXPERIENCES_PATH

class ExperienceStore:
    def __init__(self, path: Path = EXPERIENCES_PATH):
        self.path = path
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except Exception:
                self.data = {"experiences": []}
        else:
            self.data = {"experiences": []}

    def add_experience(self, exp: Dict[str, Any]):
        self.data.setdefault("experiences", []).append(exp)
        self.path.write_text(json.dumps(self.data, indent=2))

    def get_experiences(self) -> List[Dict[str, Any]]:
        return self.data.get("experiences", [])

    def find_similar_experiences(self, description: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Return up to 'limit' most similar experiences based on simple keyword overlap.

        This is a lightweight, server-side memory lookup to demonstrate retrieval
        and learning signals for the MVP. It relies on experiences having a
        'description' field captured at storage time.
        """
        exps = self.get_experiences()
        if not exps:
            return []
        qwords = set(str(description).lower().split())
        def score(exp: Dict[str, Any]) -> int:
            d = exp.get("description", "")
            words = set(str(d).lower().split())
            return len(qwords & words)
        scored = sorted(exps, key=lambda e: score(e), reverse=True)
        return scored[:max(0, int(limit))]
