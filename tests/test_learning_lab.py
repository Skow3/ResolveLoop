"""Unit and integration tests for Phase 2 ResolveLoop Learning Lab.

Covers:
1. Learning Lab Overview API & Real Database Telemetry (GET /api/learning/overview)
2. Agent Evolution, Candidates, and Strategy Diff (GET /api/learning/agent/<id>)
3. Failure Explorer & Deep Failure Inspection (GET /api/learning/failures & GET /api/learning/failures/<id>)
4. Failure Replay Runner with Empirical Comparison (POST /api/learning/replay)
5. Test Lab Batch Evaluation Suite (POST /api/learning/test_lab/run)
6. Tool Analytics & Invocations Telemetry (GET /api/learning/tools)
7. Learning Runs & Unified Audit Timeline (GET /api/learning/runs & GET /api/learning/history)
8. Unseen Case Live Simulation with Active Strategy Verification (POST /api/learning/unseen_case)
9. Promotion / Rejection of Candidate Strategies
"""
import unittest
import json
import time

from resolve_loop.db import db
from resolve_loop.seeds import seed_database
from resolve_loop.strategy import strategy_registry
from resolve_loop.web_app import app


class TestLearningLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = app.test_client()

    def setUp(self):
        db.execute("UPDATE agent_strategies SET status = 'ACTIVE' WHERE id = 'strat_l2_ar_v0';")
        db.execute("UPDATE agent_strategies SET status = 'CANDIDATE' WHERE id = 'strat_l2_ar_v1';")
        strategy_registry._load_defaults()
        strategy_registry._sync_with_db()

    def tearDown(self):
        db.execute("UPDATE agent_strategies SET status = 'ACTIVE' WHERE id = 'strat_l2_ar_v0';")
        db.execute("UPDATE agent_strategies SET status = 'CANDIDATE' WHERE id = 'strat_l2_ar_v1';")
        strategy_registry._load_defaults()
        strategy_registry._sync_with_db()

    @classmethod
    def tearDownClass(cls):
        db.execute("UPDATE agent_strategies SET status = 'ACTIVE' WHERE id = 'strat_l2_ar_v0';")
        db.execute("UPDATE agent_strategies SET status = 'CANDIDATE' WHERE id = 'strat_l2_ar_v1';")
        strategy_registry._load_defaults()
        strategy_registry._sync_with_db()

    def test_01_learning_overview_metrics(self):
        """GET /api/learning/overview must return real metrics from PostgreSQL without fabricated multipliers."""
        res = self.client.get("/api/learning/overview")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("metrics", data)
        self.assertIn("workforce", data)
        m = data["metrics"]

        # Ensure all required metrics exist and are integer counts
        self.assertIsInstance(m.get("evaluated_cases"), int)
        self.assertGreater(m.get("evaluated_cases"), 0)
        self.assertIsInstance(m.get("learning_experiences"), int)
        self.assertGreater(m.get("learning_experiences"), 0)
        self.assertIsInstance(m.get("agent_strategy_versions"), int)
        self.assertGreaterEqual(m.get("agent_strategy_versions"), 5)
        self.assertIsInstance(m.get("candidate_improvements"), int)
        self.assertIsInstance(m.get("promoted_strategies"), int)
        self.assertIsInstance(m.get("feedback_signals"), int)
        self.assertIsInstance(m.get("failed_cases"), int)
        self.assertIsInstance(m.get("learning_runs"), int)

        # Workforce must include all key agents: Orchestrator, L1, L2 AR, L3 Accounting, L4 Executive
        workforce = data["workforce"]
        agent_ids = [w["agent_id"] for w in workforce]
        self.assertIn("agent_orchestrator", agent_ids)
        self.assertIn("agent_l1_triage", agent_ids)
        self.assertIn("agent_l2_ar", agent_ids)
        self.assertTrue(any("agent_l3" in aid for aid in agent_ids))
        self.assertTrue(any("agent_l4" in aid for aid in agent_ids))

        # Verify agent metadata
        ar_agent = next(w for w in workforce if w["agent_id"] == "agent_l2_ar")
        self.assertEqual(ar_agent["active_version"], "v0")
        self.assertGreater(len(ar_agent["candidates"]), 0)

    def test_02_agent_evolution_and_diff(self):
        """GET /api/learning/agent/<id> must return active strategy, latest candidate, diff, failures, and lessons."""
        res = self.client.get("/api/learning/agent/agent_l2_ar")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["agent_id"], "agent_l2_ar")
        self.assertIsNotNone(data["active_strategy"])
        self.assertEqual(data["active_strategy"]["version"], "v0")

        self.assertIsNotNone(data["latest_candidate"])
        self.assertEqual(data["latest_candidate"]["version"], "v1")

        # Diff must exist and reflect changes in preferred_tools / tool order
        self.assertIsNotNone(data["diff"])
        self.assertGreater(data["diff"]["change_count"], 0)

        # Failures and experiences must be returned
        self.assertIsInstance(data["failures"], list)
        self.assertIsInstance(data["experiences"], list)

    def test_03_failure_explorer_and_detail(self):
        """GET /api/learning/failures and GET /api/learning/failures/<id> must return filterable failures and linked context."""
        # List failures
        res = self.client.get("/api/learning/failures?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        failures = data.get("failures", [])
        self.assertGreater(len(failures), 0)

        first_failure = failures[0]
        failure_id = first_failure["id"]
        self.assertIn("failure_type", first_failure)
        self.assertIn("description", first_failure)

        # Deep inspection
        detail_res = self.client.get(f"/api/learning/failures/{failure_id}")
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.get_json()

        self.assertIn("failure", detail_data)
        self.assertEqual(detail_data["failure"]["id"], failure_id)
        self.assertIn("case", detail_data)
        self.assertIn("reflection", detail_data)

    def test_04_failure_replay_runner(self):
        """POST /api/learning/replay must execute real base vs candidate comparative replay and measure deltas."""
        res = self.client.post(
            "/api/learning/replay",
            data=json.dumps({
                "case_description": "Why was our Acme payment 250 short on invoice INV-4471?",
                "customer_id": "cust1"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data["success"])
        self.assertIn("base", data)
        self.assertIn("candidate", data)
        self.assertIn("comparison", data)

        base = data["base"]
        candidate = data["candidate"]
        cmp = data["comparison"]

        # Base should be v0, candidate v1
        self.assertEqual(base["version"], "v0")
        self.assertEqual(candidate["version"], "v1")

        # Candidate should have pruned get_customer_history, reducing tool count by 1
        self.assertIn("get_customer_history", cmp.get("pruned_tools", []))
        self.assertLess(cmp["tool_count_delta"], 0)

        # Candidate score should be higher or equal to base score
        self.assertGreaterEqual(candidate["score"], base["score"])
        self.assertIn("Pruned", cmp["what_changed"])

    def test_05_test_lab_batch_evaluation(self):
        """POST /api/learning/test_lab/run must evaluate multiple benchmark cases and produce summary metrics."""
        res = self.client.post(
            "/api/learning/test_lab/run",
            data=json.dumps({
                "agent_id": "agent_l2_ar",
                "base_strategy_id": "strat_l2_ar_v0",
                "candidate_strategy_id": "strat_l2_ar_v1"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["agent_id"], "agent_l2_ar")
        self.assertGreaterEqual(data["cases_tested"], 3)
        self.assertIn("avg_evaluator_score", data)
        self.assertIn("avg_tool_calls", data)
        self.assertIn("benchmark_verdict", data)

        # Candidate should average fewer tool calls than base
        self.assertLess(data["avg_tool_calls"]["candidate"], data["avg_tool_calls"]["base"])

    def test_06_tool_analytics_telemetry(self):
        """GET /api/learning/tools must return operational telemetry for financial tools."""
        res = self.client.get("/api/learning/tools")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("tools", data)
        self.assertIn("common_sequences", data)
        self.assertIn("total_calls", data)
        self.assertGreater(data["total_calls"], 0)

        tool_names = [t["tool_name"] for t in data["tools"]]
        self.assertTrue(any(name in tool_names for name in ["get_invoice", "get_payment", "get_policy_version", "verify_customer"]))

    def test_07_learning_runs_and_history(self):
        """GET /api/learning/runs and GET /api/learning/history must return learning progression timeline."""
        res = self.client.get("/api/learning/runs")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("runs", data)

        hist_res = self.client.get("/api/learning/history?limit=20")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.get_json()
        self.assertIn("timeline", hist_data)
        self.assertGreater(len(hist_data["timeline"]), 0)

    def test_08_unseen_case_simulation(self):
        """POST /api/learning/unseen_case must dynamically load the active strategy and return execution trace."""
        res = self.client.post(
            "/api/learning/unseen_case",
            data=json.dumps({
                "description": "Why was payment PMT-8821 short by $250 on invoice INV-4471?",
                "customer_id": "cust1",
                "domain": "accounts_receivable"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data["success"])
        self.assertIn("active_strategy_loaded", data)
        self.assertIn("tools_invoked", data)
        self.assertIn("resolution", data)
        self.assertIn("evaluation", data)
        self.assertGreater(len(data["tools_invoked"]), 0)

    def test_09_candidate_promotion_and_active_runtime_verification(self):
        """Promoting candidate strat_l2_ar_v1 must make it ACTIVE, archiving v0, and updating future case runs."""
        # Promote v1
        prom_res = self.client.post(
            "/api/strategies/strat_l2_ar_v1/promote",
            data=json.dumps({"promoted_by": "supervisor_test", "notes": "Automated verification"}),
            content_type="application/json"
        )
        self.assertEqual(prom_res.status_code, 200)
        self.assertTrue(prom_res.get_json()["success"])

        # Active strategy must now be v1
        active = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertEqual(active.version, "v1")
        self.assertEqual(active.strategy_id, "strat_l2_ar_v1")

        # Running unseen case now executes with v1 as active
        sim_res = self.client.post(
            "/api/learning/unseen_case",
            data=json.dumps({
                "description": "Why was invoice INV-4471 paid short by $250?",
                "customer_id": "cust1",
                "domain": "accounts_receivable"
            }),
            content_type="application/json"
        )
        sim_data = sim_res.get_json()
        self.assertEqual(sim_data["active_strategy_loaded"]["version"], "v1")
        # In v1, get_customer_history is pruned
        self.assertNotIn("get_customer_history", sim_data["tools_invoked"])


if __name__ == "__main__":
    unittest.main()
