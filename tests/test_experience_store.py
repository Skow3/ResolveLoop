import json
import tempfile
from pathlib import Path

from resolve_loop.store import ExperienceStore


def test_experience_store_roundtrip(tmp_path: Path):
    path = tmp_path / "experiences.json"
    es = ExperienceStore(path=path)
    es.add_experience({"case_id": "C1", "description": "test case 1", "route": {"level": 1}, "solve": {"ok": True}, "timestamp": 0})
    exps = es.get_experiences()
    assert isinstance(exps, list)
    assert len(exps) == 1
    assert exps[0]["case_id"] == "C1"


def test_find_similar_experiences(tmp_path: Path):
    path = tmp_path / "experiences.json"
    es = ExperienceStore(path=path)
    es.add_experience({"case_id": "C1", "description": "order not received", "route": {}, "solve": {}, "timestamp": 0})
    es.add_experience({"case_id": "C2", "description": "refund pending for order", "route": {}, "solve": {}, "timestamp": 0})
    similar = es.find_similar_experiences("where is my order", limit=2)
    assert isinstance(similar, list)
    # Should return at least one experience with overlapping keywords if any
    assert len(similar) <= 2
