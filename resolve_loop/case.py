"""Data model for a support Case."""
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Case:
    id: str
    customer_id: str
    description: str
    priority: str  # e.g., low, medium, high, critical
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return asdict(self)
