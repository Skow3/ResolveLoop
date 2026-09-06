"""In-memory and on-disk memories for customers, cases, procedures, and failures."""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .config import MEMORY_PATH

class MemoryStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or MEMORY_PATH
        self.customer_memory: Dict[str, Any] = {}
        self.case_memory: Dict[str, Any] = {}
        self.procedural_memory: Dict[str, Any] = {}
        self.failure_memory: list = []
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text())
                self.customer_memory = data.get("customer_memory", {})
                self.case_memory = data.get("case_memory", {})
                self.procedural_memory = data.get("procedural_memory", {})
                self.failure_memory = data.get("failure_memory", [])
        except Exception:
            # If file corrupted, start fresh
            self.customer_memory = {}
            self.case_memory = {}
            self.procedural_memory = {}
            self.failure_memory = []

    def _save(self):
        data = {
            "customer_memory": self.customer_memory,
            "case_memory": self.case_memory,
            "procedural_memory": self.procedural_memory,
            "failure_memory": self.failure_memory,
        }
        self.path.write_text(json.dumps(data, indent=2, default=str))

    # Customer memory
    def get_customer_history(self, customer_id: str) -> Dict[str, Any]:
        return self.customer_memory.get(customer_id, {})

    def update_customer_history(self, customer_id: str, history: Dict[str, Any]):
        self.customer_memory[customer_id] = history
        self._save()

    # Case memory
    def get_case_memory(self, case_id: str) -> Dict[str, Any]:
        return self.case_memory.get(case_id, {})

    def update_case_memory(self, case_id: str, memory: Dict[str, Any]):
        self.case_memory[case_id] = memory
        self._save()

    # Procedural memory
    def get_procedural_memory(self, key: str) -> Any:
        return self.procedural_memory.get(key)

    def update_procedural_memory(self, key: str, value: Any):
        self.procedural_memory[key] = value
        self._save()

    # Failure memory
    def log_failure(self, entry: Dict[str, Any]):
        self.failure_memory.append(entry)
        self._save()
