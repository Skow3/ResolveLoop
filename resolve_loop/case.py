"""Data model for a support Case."""
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional

@dataclass
class Case:
    id: str
    customer_id: str
    description: str
    priority: str = "medium"  # e.g., low, medium, high, critical
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        return cls(
            id=str(data.get("id", "UNKNOWN")),
            customer_id=str(data.get("customer_id", "cust_unknown")),
            description=str(data.get("description", "")),
            priority=str(data.get("priority", "medium")),
            metadata=data.get("metadata") or {},
        )
