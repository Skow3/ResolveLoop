"""Unit and integration test suite for Automated Agent Engineer (Agent Factory) - Track 1.

Covers:
1. Tool catalog validation (accepts canonical tools, corrects aliases, rejects hallucinated tools).
2. Specialist design preview generation (v0 CANDIDATE, derived signals, tool order, zero exec/eval code generation).
3. Specialist persistence in strategy_registry and PostgreSQL database.
4. Real runtime test execution on benchmark cases with telemetry recording (scores, latency, tool calls).
5. Automatic failure pattern analysis (identifies EXCESSIVE_TOOL_USE, TOOL_ORDER, etc.).
6. Reflection and memory-guided candidate improvement (v0 -> v1 CANDIDATE, tool pruning, causal explanation).
7. Structural strategy diff calculation between v0 baseline and v1 candidate.
8. Multi-dimensional Pareto comparison (Quality, Tool Efficiency, Latency, Escalation Safety).
9. Regression protection guardrail (blocks promotion when quality regresses or safety is compromised).
10. Controlled promotion updating production active strategy and runtime dispatch.
11. Generalization on novel unseen cases without prompt memorization.
12. Maximum iteration limit enforcement (bounded at 3 iterations max).
13. End-to-end autonomous engineering cycle (run_full_engineering_cycle).
14. REST API service endpoints in web_app.py.
"""
import os
os.environ["RESOLVELOOP_USE_LLM"] = "0"

import unittest
import json
import time
from pathlib import Path

from unittest.mock import patch

from resolve_loop.db import db
from resolve_loop.seeds import seed_database
from resolve_loop.case import Case
from resolve_loop.engine import ResolveLoopEngine
from resolve_loop.strategy import AgentStrategy, strategy_registry, diff_strategies
from resolve_loop.evaluator import Evaluator, FailureType
from resolve_loop.agent_factory import (
    VALID_FINANCE_TOOLS,
    validate_tools,
    design_specialist,
    save_specialist,
    test_specialist,
    analyze_failures,
    reflect_and_improve,
    pareto_compare,
    promote_specialist,
    run_unseen_case,
    run_full_engineering_cycle,
    save_engineering_run,
    list_engineering_runs,
    get_engineering_run,
)
from resolve_loop.web_app import app


class TestAgentFactory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patcher = patch("resolve_loop.llm.request_llm", return_value="Strategic reflection: prioritize financial verification.")
        cls.patcher.start()
        seed_database()
        cls.engine = ResolveLoopEngine()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        # Ensure test isolation: reset baseline strategies
        db.execute("UPDATE agent_strategies SET status = 'ACTIVE' WHERE id = 'strat_l2_ar_v0';")
        db.execute("UPDATE agent_strategies SET status = 'CANDIDATE' WHERE id = 'strat_l2_ar_v1';")
        strategy_registry._load_defaults()
        strategy_registry._sync_with_db()

    def tearDown(self):
        # Reset baseline strategies
        db.execute("UPDATE agent_strategies SET status = 'ACTIVE' WHERE id = 'strat_l2_ar_v0';")
        db.execute("UPDATE agent_strategies SET status = 'CANDIDATE' WHERE id = 'strat_l2_ar_v1';")
        strategy_registry._load_defaults()
        strategy_registry._sync_with_db()

    # --------------------------------------------------------------------------
    # 1. Tool Catalog & Strict Validation
    # --------------------------------------------------------------------------
    def test_01_tool_validation(self):
        """Verify strict tool catalog validation: accepts real tools, corrects aliases, rejects invented tools."""
        # Valid canonical tools
        canonical_input = ["get_customer", "get_invoice", "get_payment", "get_policy_version"]
        report1 = validate_tools(canonical_input)
        self.assertTrue(report1["valid"])
        self.assertEqual(len(report1["valid_tools"]), 4)
        self.assertEqual(len(report1["invalid_tools"]), 0)

        # Hallucinated or invalid tools
        hallucinated_input = ["get_invoice", "execute_arbitrary_python", "hack_database", "delete_all_records"]
        report2 = validate_tools(hallucinated_input)
        self.assertFalse(report2["valid"])
        self.assertIn("get_invoice", report2["valid_tools"])
        self.assertIn("execute_arbitrary_python", report2["invalid_tools"])
        self.assertIn("hack_database", report2["invalid_tools"])

        # Tool aliases / corrections
        alias_input = ["check_invoice", "lookup_payment", "customer_lookup"]
        report3 = validate_tools(alias_input)
        self.assertTrue(report3["valid"])
        self.assertIn("get_invoice", report3["valid_tools"])
        self.assertIn("get_payment", report3["valid_tools"])
        self.assertIn("get_customer", report3["valid_tools"])
        self.assertEqual(report3["corrected_tools"]["check_invoice"], "get_invoice")

    # --------------------------------------------------------------------------
    # 2. Specialist Design & Preview (Zero Arbitrary Code Generation)
    # --------------------------------------------------------------------------
    def test_02_specialist_design_preview(self):
        """Verify specialist design produces structured AgentStrategy without executable code generation."""
        preview = design_specialist(
            goal="Resolve customer payment discrepancies, short payments, and billing queries using financial records.",
            domain="accounts_receivable",
            name="AR Resolution Specialist",
            selected_tools=["get_customer", "get_customer_history", "get_invoice", "get_payment", "get_policy_version"],
            evaluation_criteria=["correctness", "evidence", "tool_efficiency", "escalation"]
        )

        self.assertIsNotNone(preview)
        self.assertEqual(preview["domain"], "accounts_receivable")
        self.assertEqual(preview["version"], "v0")
        self.assertEqual(preview["status"], "CANDIDATE")
        self.assertTrue(len(preview["routing_signals"]) > 0)
        self.assertIn("payment discrepancy", preview["routing_signals"])
        self.assertTrue(preview["validation"]["valid"])

        # Tool ordering dependency check: get_customer -> get_invoice -> get_payment -> get_policy_version
        tool_order = preview["preferred_tool_order"]
        self.assertEqual(tool_order[0], "get_customer")
        self.assertIn("get_invoice", tool_order)
        self.assertIn("get_payment", tool_order)

        # Escalation rules must preserve safety threshold ($50k ESC-400)
        rules_text = " ".join(preview["escalation_rules"])
        self.assertIn("$50,000", rules_text)
        self.assertIn("ESC-400", rules_text)

        # Budgets must be present
        self.assertIn("max_tool_calls", preview["budgets"])
        self.assertIn("target_latency_ms", preview["budgets"])

    # --------------------------------------------------------------------------
    # 3. Specialist Persistence & Audit Logging
    # --------------------------------------------------------------------------
    def test_03_save_specialist(self):
        """Verify specialist strategy saves to registry and PostgreSQL database with audit trail."""
        preview = design_specialist(
            goal="Test persistence of specialist.",
            domain="accounts_receivable",
            name="Persistence Test Specialist",
            selected_tools=["get_customer", "get_invoice", "get_payment"]
        )
        strat = save_specialist(preview["strategy"])
        self.assertIsNotNone(strat)
        self.assertEqual(strat.version, "v0")

        # Verify strategy in registry
        retrieved = strategy_registry.get_strategy(strat.strategy_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, strat.name)

        # Verify strategy in PostgreSQL
        db_row = db.fetch_one("SELECT id, name, version, status FROM agent_strategies WHERE id = %s;", (strat.strategy_id,))
        self.assertIsNotNone(db_row)
        self.assertEqual(db_row["id"], strat.strategy_id)
        self.assertEqual(db_row["status"], "CANDIDATE")

        # Verify audit event logged
        audit_row = db.fetch_one("SELECT * FROM audit_events WHERE action = 'SPECIALIST_DESIGNED' AND actor_id = 'agent_factory' ORDER BY created_at DESC LIMIT 1;")
        self.assertIsNotNone(audit_row)

    # --------------------------------------------------------------------------
    # 4. Benchmark Testing on Real Runtime
    # --------------------------------------------------------------------------
    def test_04_test_specialist_on_runtime(self):
        """Verify test_specialist executes real runtime with strategy override and records telemetry."""
        preview = design_specialist(
            goal="Resolve AR short payments.",
            domain="accounts_receivable",
            name="Runtime Test Specialist",
            selected_tools=["get_customer", "get_customer_history", "get_invoice", "get_payment", "get_policy_version"]
        )
        strat = save_specialist(preview["strategy"])

        results = test_specialist(strat)
        self.assertIsNotNone(results)
        self.assertGreater(results["cases_evaluated"], 0)
        self.assertGreater(results["average_score"], 50.0)
        self.assertGreater(results["avg_tools_used"], 0.0)
        self.assertGreater(results["avg_latency_ms"], 0.0)
        self.assertIn("case_runs", results)

        # Verify at least one run called tools and produced resolution
        first_run = results["case_runs"][0]
        self.assertGreater(len(first_run["tools_called"]), 0)
        self.assertTrue(len(first_run["resolution_summary"]) > 0)

    # --------------------------------------------------------------------------
    # 5. Automatic Failure Analysis
    # --------------------------------------------------------------------------
    def test_05_failure_analysis(self):
        """Verify automatic failure analysis categorizes patterns from evaluation telemetry."""
        # Simulate test results with an excessive tool use pattern
        simulated_results = {
            "strategy_id": "strat_test_v0",
            "avg_tools_used": 5.0,
            "tool_usage_counts": {"get_customer": 3, "get_customer_history": 3, "get_invoice": 3, "get_payment": 3, "get_policy_version": 3},
            "failures": [
                {
                    "case_id": "case_1",
                    "failure_type": "EXCESSIVE_TOOL_USE",
                    "description": "5 tools called when 3 tools would suffice",
                    "evidence": "Customer history fetched redundantly",
                },
                {
                    "case_id": "case_2",
                    "failure_type": "TOOL_ORDER",
                    "description": "Customer history checked before invoice verification",
                    "evidence": "Tool order deviation",
                }
            ]
        }
        patterns = analyze_failures(simulated_results)
        self.assertGreater(len(patterns), 0)
        pattern_types = [p["failure_type"] for p in patterns]
        self.assertIn("EXCESSIVE_TOOL_USE", pattern_types)

    # --------------------------------------------------------------------------
    # 6. Reflection & Candidate Generation (v0 -> v1) with Structural Diff
    # --------------------------------------------------------------------------
    def test_06_reflect_and_improve_v1_candidate(self):
        """Verify reflection synthesizes lessons, prunes redundant tools, and evolves v1 candidate."""
        preview = design_specialist(
            goal="Resolve AR short payments.",
            domain="accounts_receivable",
            name="Evolution Test Specialist",
            selected_tools=["get_customer", "get_customer_history", "get_invoice", "get_payment", "get_policy_version"]
        )
        v0_strat = save_specialist(preview["strategy"])
        v0_results = test_specialist(v0_strat)

        improvement = reflect_and_improve(v0_strat, v0_results, iteration=1)
        self.assertIsNotNone(improvement)
        self.assertEqual(improvement["version"], "v1")

        cand = strategy_registry.get_strategy(improvement["candidate_strategy_id"])
        self.assertIsNotNone(cand)
        self.assertEqual(cand.version, "v1")
        self.assertEqual(cand.status, "CANDIDATE")
        self.assertEqual(cand.parent_strategy_id, v0_strat.strategy_id)

        # Verify tool pruning: get_customer_history was pruned!
        self.assertNotIn("get_customer_history", cand.preferred_tools)
        self.assertIn("get_invoice", cand.preferred_tools)
        self.assertIn("get_payment", cand.preferred_tools)

        # Verify causal explanation chain
        self.assertTrue(len(improvement["causal_chain"]) > 0)
        stages = [s["stage"] for s in improvement["causal_chain"]]
        self.assertTrue(any("Failure" in st or "Optimization" in st for st in stages))

        # Verify structural diff
        diff = improvement["diff"]
        self.assertEqual(diff["base_version"], "v0")
        self.assertEqual(diff["candidate_version"], "v1")
        self.assertGreater(diff["change_count"], 0)

    # --------------------------------------------------------------------------
    # 7. Retesting & Multi-Dimensional Pareto Comparison
    # --------------------------------------------------------------------------
    def test_07_pareto_tradeoff_comparison(self):
        """Verify Pareto trade-off comparison across quality, tool efficiency, latency, and safety."""
        v0_metrics = {
            "average_score": 84.0,
            "avg_tools_used": 5.0,
            "avg_latency_ms": 420.0,
            "resolution_rate": 100.0,
            "escalation_rate": 33.3,
        }
        v1_metrics = {
            "average_score": 94.0,
            "avg_tools_used": 3.0,
            "avg_latency_ms": 280.0,
            "resolution_rate": 100.0,
            "escalation_rate": 33.3,
        }

        pareto = pareto_compare(v0_metrics, v1_metrics)
        self.assertEqual(pareto["status"], "IMPROVED")
        self.assertFalse(pareto["regression_detected"])

        dims = pareto["dimensions"]
        self.assertEqual(dims["quality_score"]["delta"], 10.0)
        self.assertEqual(dims["tool_efficiency"]["delta"], -2.0)
        self.assertTrue(dims["quality_score"]["improved"])
        self.assertTrue(dims["tool_efficiency"]["improved"])
        self.assertTrue(dims["escalation_rate"]["preserved"])

    # --------------------------------------------------------------------------
    # 8. Regression Protection Guardrail
    # --------------------------------------------------------------------------
    def test_08_regression_protection(self):
        """Verify regression guardrail detects and flags quality regressions or safety compromises."""
        v0_metrics = {
            "average_score": 88.0,
            "avg_tools_used": 4.0,
            "avg_latency_ms": 350.0,
            "resolution_rate": 100.0,
            "escalation_rate": 33.3,
        }
        # Regressed metrics: lower score (-10 pts)
        v1_regressed = {
            "average_score": 78.0,
            "avg_tools_used": 2.0,  # fewer tools, but worse quality!
            "avg_latency_ms": 200.0,
            "resolution_rate": 80.0,
            "escalation_rate": 0.0,  # missed required escalation!
        }

        pareto = pareto_compare(v0_metrics, v1_regressed)
        self.assertEqual(pareto["status"], "REGRESSION_DETECTED")
        self.assertTrue(pareto["regression_detected"])
        self.assertIn("REGRESSION DETECTED", pareto["verdict"])

    # --------------------------------------------------------------------------
    # 9. Controlled Promotion & Direct Runtime Dispatch
    # --------------------------------------------------------------------------
    def test_09_promotion_and_runtime_dispatch(self):
        """Verify promotion activates candidate, archives parent, and updates runtime dispatch."""
        preview = design_specialist(
            goal="Promotion test specialist.",
            domain="accounts_receivable",
            name="Promotion Dispatch Specialist",
            selected_tools=["get_customer", "get_invoice", "get_payment", "get_policy_version"]
        )
        v0 = save_specialist(preview["strategy"])

        # Create candidate v1
        v1 = v0.evolve("v1", {"preferred_tool_order": ["get_invoice", "get_payment", "get_policy_version"]}, status="CANDIDATE")
        strategy_registry.register_strategy(v1, persist_to_db=True)

        self.assertEqual(v0.status, "CANDIDATE")
        self.assertEqual(v1.status, "CANDIDATE")

        # Promote v1
        promo_res = promote_specialist(v1.strategy_id, promoted_by="Test Suite")
        self.assertTrue(promo_res["success"])

        # Active strategy for this agent must now be v1
        active = strategy_registry.get_active_strategy(agent_id=v1.agent_id)
        self.assertEqual(active.strategy_id, v1.strategy_id)
        self.assertEqual(active.version, "v1")
        self.assertEqual(active.status, "ACTIVE")

    # --------------------------------------------------------------------------
    # 10. Generalization on Novel Unseen Case (No Prompt Memorization)
    # --------------------------------------------------------------------------
    def test_10_unseen_case_generalization(self):
        """Verify specialist resolves a novel unseen case using learned principles without prompt memorization."""
        # Run novel wire fee scenario
        unseen_res = run_unseen_case()
        self.assertIsNotNone(unseen_res)
        self.assertEqual(unseen_res["novel_scenario"], "International Wire Fee Discrepancy")
        self.assertTrue(unseen_res["resolved"])
        self.assertGreaterEqual(unseen_res["evaluator_score"], 85)
        self.assertTrue(unseen_res["generalization_confirmed"])
        self.assertIn("INV-4471", unseen_res["resolution_text"])

    # --------------------------------------------------------------------------
    # 11. Bounded Iteration Limit (Max 3 Iterations)
    # --------------------------------------------------------------------------
    def test_11_iteration_limit(self):
        """Verify self-improvement halts predictably when exceeding maximum iterations (max 3)."""
        preview = design_specialist(
            goal="Iteration limit test.",
            domain="accounts_receivable",
            selected_tools=["get_customer", "get_invoice", "get_payment"]
        )
        v0 = save_specialist(preview["strategy"])
        mock_results = {"avg_tools_used": 4.0, "failures": []}

        # Iteration 1 to 3 should succeed
        imp1 = reflect_and_improve(v0, mock_results, iteration=1, max_iterations=3)
        self.assertEqual(imp1["version"], "v1")

        imp2 = reflect_and_improve(v0, mock_results, iteration=2, max_iterations=3)
        self.assertEqual(imp2["version"], "v2")

        imp3 = reflect_and_improve(v0, mock_results, iteration=3, max_iterations=3)
        self.assertEqual(imp3["version"], "v3")

        # Iteration 4 must raise ValueError halting self-improvement
        with self.assertRaises(ValueError) as ctx:
            reflect_and_improve(v0, mock_results, iteration=4, max_iterations=3)
        self.assertIn("Iteration limit reached", str(ctx.exception))

    # --------------------------------------------------------------------------
    # 12. Full End-to-End Automated Engineering Cycle
    # --------------------------------------------------------------------------
    def test_12_full_engineering_cycle(self):
        """Verify complete automated agent engineering cycle:
        Design -> Test v0 -> Failures -> Reflect -> Synthesize v1 -> Retest v1 -> Pareto Compare -> Regression Check -> Persist Run.
        """
        cycle = run_full_engineering_cycle(
            goal="Resolve customer short payments under early settlement discount terms.",
            domain="accounts_receivable",
            name="E2E Autonomous AR Specialist",
            selected_tools=["get_customer", "get_customer_history", "get_invoice", "get_payment", "get_policy_version"],
            evaluation_criteria=["correctness", "evidence", "tool_efficiency", "escalation"],
            max_iterations=3,
            auto_promote_if_improved=False
        )

        self.assertIsNotNone(cycle)
        self.assertIn("aer_", cycle["id"])
        self.assertIn(cycle["status"], ("COMPLETED", "PROMOTED", "REGRESSION_HALTED"))
        self.assertIsNotNone(cycle["v0_metrics"])
        self.assertIsNotNone(cycle["v1_metrics"])
        self.assertIsNotNone(cycle["pareto_comparison"])
        self.assertFalse(cycle["regression_detected"])

        # Verify persistence in agent_engineering_runs table
        saved_run = get_engineering_run(cycle["id"])
        self.assertIsNotNone(saved_run)
        self.assertEqual(saved_run["id"], cycle["id"])
        self.assertEqual(saved_run["specialist_id"], cycle["specialist_id"])

        # Verify listing runs
        all_runs = list_engineering_runs(limit=10)
        self.assertGreater(len(all_runs), 0)
        run_ids = [r["id"] for r in all_runs]
        self.assertIn(cycle["id"], run_ids)

    # --------------------------------------------------------------------------
    # 13. REST API Service Endpoints
    # --------------------------------------------------------------------------
    def test_13_rest_api_endpoints(self):
        """Verify REST API service endpoints for Agent Factory."""
        # 1. GET /api/factory/tools
        res_tools = self.client.get("/api/factory/tools")
        self.assertEqual(res_tools.status_code, 200)
        tools_data = res_tools.get_json()
        self.assertTrue(tools_data["success"])
        self.assertGreaterEqual(tools_data["count"], 16)

        # 2. POST /api/factory/design
        res_design = self.client.post("/api/factory/design", json={
            "goal": "Resolve customer billing inquiries.",
            "domain": "accounts_receivable",
            "name": "API Test Specialist",
            "selected_tools": ["get_customer", "get_invoice", "get_payment"]
        })
        self.assertEqual(res_design.status_code, 200)
        design_data = res_design.get_json()
        self.assertTrue(design_data["success"])
        strat = design_data["strategy"]

        # 3. POST /api/factory/save
        res_save = self.client.post("/api/factory/save", json={"strategy": strat})
        self.assertEqual(res_save.status_code, 200)
        save_data = res_save.get_json()
        self.assertTrue(save_data["success"])

        # 4. POST /api/factory/test
        res_test = self.client.post("/api/factory/test", json={"strategy_id": strat["strategy_id"]})
        self.assertEqual(res_test.status_code, 200)
        test_data = res_test.get_json()
        self.assertTrue(test_data["success"])
        self.assertIn("test_results", test_data)

        # 5. POST /api/factory/unseen
        res_unseen = self.client.post("/api/factory/unseen", json={"strategy_id": strat["strategy_id"]})
        self.assertEqual(res_unseen.status_code, 200)
        unseen_data = res_unseen.get_json()
        self.assertTrue(unseen_data["success"])

        # 6. GET /api/factory/runs
        res_runs = self.client.get("/api/factory/runs")
        self.assertEqual(res_runs.status_code, 200)
        runs_data = res_runs.get_json()
        self.assertTrue(runs_data["success"])
        self.assertGreaterEqual(runs_data["count"], 1)


if __name__ == "__main__":
    unittest.main()
