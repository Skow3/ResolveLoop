import unittest
from pathlib import Path
import tempfile

from resolve_loop.engine import ResolveLoopEngine, run_comparative_benchmark
from resolve_loop.case import Case

class TestRouterAndLearning(unittest.TestCase):
    def test_router_level_generation_without_llm(self):
        engine = ResolveLoopEngine()
        c = Case(id="TEST1", customer_id="cust1", description="Where is my order?", priority="low", metadata={})
        route = engine.route_case(c)
        self.assertTrue(1 <= route.get("route_level", 0) <= 4)
        self.assertIn("plan", route)

    def test_experience_promotes_routing_tier(self):
        """Verify that past experience prevents under-routing and promotes routing level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            engine = ResolveLoopEngine(memory_path=tmp / "memories.json", experience_path=tmp / "experiences.json")
            
            # Simulated past experience where C1 required escalation to L2
            past_exp = [{
                "case_id": "C1",
                "description": "Where is my order?",
                "recommended_route": 2,
                "escalated": True,
            }]
            c = Case(id="TEST2", customer_id="cust1", description="Where is my order?", priority="low")
            route = engine.route_case(c, similar_experiences=past_exp)
            
            self.assertEqual(route.get("route_level"), 2)
            self.assertTrue(route.get("learning_applied"))

    def test_comparative_learning_benchmark(self):
        """Verify that Pass 2 demonstrates improved or equal metrics and confirms learning."""
        summary = run_comparative_benchmark()
        self.assertIn("comparison", summary)
        self.assertTrue(summary["comparison"]["learning_confirmed"])

if __name__ == "__main__":
    unittest.main()
