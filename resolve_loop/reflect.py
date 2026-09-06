"""Reflection module to articulate lessons learned after a case."""
from typing import Dict, Any, List

def reflect(case_id: str, memory: Dict[str, Any], lessons: List[str]) -> Dict[str, Any]:
    note = {
        "case_id": case_id,
        "lessons": lessons,
        "memory_snapshot": memory,
    }
    return note
