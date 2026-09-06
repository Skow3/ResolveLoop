import unittest
import tempfile
from pathlib import Path

from resolve_loop.store import ExperienceStore

class TestExperienceStore(unittest.TestCase):
    def test_experience_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "experiences.json"
            es = ExperienceStore(path=path)
            es.add_experience({
                "case_id": "C1",
                "description": "test case 1",
                "route": {"level": 1},
                "solve": {"ok": True},
                "timestamp": 0
            })
            exps = es.get_experiences()
            self.assertIsInstance(exps, list)
            self.assertEqual(len(exps), 1)
            self.assertEqual(exps[0]["case_id"], "C1")

    def test_find_similar_experiences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "experiences.json"
            es = ExperienceStore(path=path)
            es.add_experience({
                "case_id": "C1",
                "description": "order not received tracking",
                "route": {},
                "solve": {},
                "timestamp": 0
            })
            es.add_experience({
                "case_id": "C2",
                "description": "refund pending for order",
                "route": {},
                "solve": {},
                "timestamp": 0
            })
            similar = es.find_similar_experiences("where is my order tracking", limit=2)
            self.assertIsInstance(similar, list)
            self.assertTrue(len(similar) >= 1)
            self.assertEqual(similar[0]["case_id"], "C1")

if __name__ == "__main__":
    unittest.main()
