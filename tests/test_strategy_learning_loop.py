"""Unit and integration tests for Phase 1 Learning Loop Foundation.

Covers:
1. Strategy versioning, configuration, and structural diff.
2. Controlled candidate generation without premature overwrite.
3. Candidate promotion & rejection mechanisms with audit trails.
4. Mandatory runtime behavior alteration test: v0 ACTIVE -> promote v1 -> runtime uses v1 and changes tool execution.
5. Deterministic End-to-End Learning Loop test:
   CASE -> AGENT v0 -> TOOLS -> EVALUATION -> FAILURE -> REFLECTION -> EXPERIENCE -> CANDIDATE v1 -> PROMOTION -> NEW CASE -> AGENT LOADS v1.
6. Feedback association with case, agent, and strategy version.
7. REST API service endpoints for strategy management and learning telemetry.
"""
import unittest
import json
import time
from pathlib import Path

from resolve_loop.db import db
from resolve_loop.seeds import seed_database
from resolve_loop.case import Case
from resolve_loop.engine import ResolveLoopEngine
from resolve_loop.strategy import (
    AgentStrategy,
    strategy_registry,
    diff_strategies,
    generate_candidate_from_reflection,
    STRATEGY_L2_AR_V0,
)
from resolve_loop.evaluator import Evaluator, FailureType
from resolve_loop.reflect import reflect
from resolve_loop.finance_tools import record_feedback
from resolve_loop.web_app import app


class TestStrategyLearningLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.engine = ResolveLoopEngine()
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

    def test_01_strategy_versioning_and_structural_diff(self):
        """Verify versioned strategy structure and accurate data-driven diff calculation."""
        base_strat = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertIsNotNone(base_strat)
        self.assertEqual(base_strat.version, "v0")
        self.assertEqual(base_strat.status, "ACTIVE")

        # Create candidate v1 with reordered tool sequence & pruned redundant lookup
        candidate_v1 = strategy_registry.create_candidate(
            agent_id="agent_l2_ar",
            changes={
                "preferred_tool_order": ["get_invoice", "get_payment", "get_policy_version"],
                "preferred_tools": ["get_customer", "get_invoice", "get_payment", "get_policy_version"],
                "strategy_instructions": "Accelerated AR path: bypass customer history when invoice is unambiguous."
            },
            rationale="Optimize AR tool latency and eliminate redundant customer history query."
        )

        self.assertEqual(candidate_v1.version, "v1")
        self.assertEqual(candidate_v1.status, "CANDIDATE")
        # Ensure active strategy is still v0!
        active_strat = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertEqual(active_strat.version, "v0")

        # Generate structured diff
        diff = diff_strategies(base_strat, candidate_v1)
        self.assertEqual(diff["base_version"], "v0")
        self.assertEqual(diff["candidate_version"], "v1")
        self.assertGreater(diff["change_count"], 0)

        diff_fields = [d["field"] for d in diff["differences"]]
        self.assertIn("preferred_tool_order", diff_fields)
        self.assertIn("strategy_instructions", diff_fields)
        self.assertTrue(len(diff["summary"]) > 0)

    def test_02_candidate_promotion_and_rejection_lifecycle(self):
        """Verify controlled promotion archives previous version, while rejection keeps candidate preserved."""
        # 1. Create a candidate
        cand = strategy_registry.create_candidate(
            agent_id="agent_l2_ar",
            changes={"strategy_instructions": "Candidate test instructions."},
            rationale="Test candidate lifecycle."
        )
        cand_id = cand.strategy_id

        # 2. Reject candidate
        rejected = strategy_registry.reject_candidate(
            strategy_id=cand_id,
            rejected_by="human_supervisor",
            reason="Insufficient offline benchmark improvement."
        )
        self.assertEqual(rejected.status, "REJECTED")

        # Check rejection audit event
        events = db.fetch_all("SELECT * FROM audit_events WHERE action = 'STRATEGY_REJECTED' ORDER BY created_at DESC LIMIT 1;")
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0]["actor_id"], "human_supervisor")

        # 3. Create another candidate and promote it
        cand2 = strategy_registry.create_candidate(
            agent_id="agent_l2_ar",
            changes={"preferred_tool_order": ["get_invoice", "get_payment", "get_policy_version"]},
            rationale="Approved performance enhancement."
        )
        promoted = strategy_registry.promote_candidate(
            strategy_id=cand2.strategy_id,
            promoted_by="system_auto_benchmark",
            notes="Passed regression suite (+4.2% faster)."
        )
        self.assertEqual(promoted.status, "ACTIVE")

        # Verify active strategy is now cand2 and v0 is ARCHIVED
        active_now = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertEqual(active_now.strategy_id, cand2.strategy_id)
        self.assertEqual(active_now.version, cand2.version)

        v0_archived = strategy_registry.get_strategy("strat_l2_ar_v0")
        self.assertEqual(v0_archived.status, "ARCHIVED")

        # Check promotion audit event
        promo_events = db.fetch_all("SELECT * FROM audit_events WHERE action = 'STRATEGY_PROMOTED' ORDER BY created_at DESC LIMIT 1;")
        self.assertTrue(len(promo_events) > 0)
        det = promo_events[0]["details"] or {}
        self.assertEqual(det.get("version"), cand2.version)

    def test_03_mandatory_runtime_behavior_change(self):
        """MANDATORY TEST:
        1) Load agent strategy v0 (ACTIVE)
        2) Execute case
        3) Confirm v0 used
        4) Create v1 with meaningful behavioral change (pruned customer_history lookup)
        5) Promote v1
        6) Execute another case
        7) Confirm v1 loaded
        8) Confirm runtime behavior reflects v1 (tool calls & strategy_version)
        """
        # Step 1: Ensure v0 is ACTIVE
        v0 = strategy_registry.get_strategy("strat_l2_ar_v0")
        strategy_registry.promote_candidate("strat_l2_ar_v0", promoted_by="test_setup")
        active_init = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertEqual(active_init.version, "v0")

        # Step 2: Execute Case under v0
        case_v0 = Case(
            id=f"CASE_RUNTIME_V0_{int(time.time())}",
            customer_id="cust1",
            description="Why was our Acme payment short by $250 for invoice INV-4471?",
            priority="medium",
            metadata={"domain": "accounts_receivable"}
        )
        result_v0 = self.engine.run_once(case_v0)

        # Step 3: Confirm v0 was used in resolution and recorded in DB
        self.assertEqual(result_v0["solve"]["strategy_version"], "v0")
        self.assertIn("get_customer_history", result_v0["solve"]["actions"])
        self.assertEqual(len(result_v0["solve"]["actions"]), 5)

        # Verify DB records v0
        case_row_v0 = db.fetch_one("SELECT strategy_version FROM cases WHERE id = %s;", (case_v0.id,))
        self.assertEqual(case_row_v0["strategy_version"], "v0")
        run_row_v0 = db.fetch_one("SELECT strategy_version FROM agent_runs WHERE case_id = %s;", (case_v0.id,))
        self.assertEqual(run_row_v0["strategy_version"], "v0")

        # Step 4: Create v1 with meaningful behavioral change: prune get_customer_history
        v1_candidate = strategy_registry.create_candidate(
            agent_id="agent_l2_ar",
            changes={
                "preferred_tool_order": ["get_invoice", "get_payment", "get_policy_version"],
                "preferred_tools": ["get_invoice", "get_payment", "get_policy_version"],
                "strategy_instructions": "Optimized AR workflow: verify payment and invoice directly without customer history overhead."
            },
            rationale="Prune redundant customer history lookup to reduce latency."
        )
        self.assertEqual(v1_candidate.version, "v1")

        # Step 5: Promote v1 to ACTIVE
        strategy_registry.promote_candidate(v1_candidate.strategy_id, promoted_by="benchmark_validator")
        active_after_promo = strategy_registry.get_active_strategy(agent_id="agent_l2_ar")
        self.assertEqual(active_after_promo.version, "v1")
        self.assertEqual(active_after_promo.status, "ACTIVE")

        # Step 6: Execute another case
        case_v1 = Case(
            id=f"CASE_RUNTIME_V1_{int(time.time())}",
            customer_id="cust1",
            description="Why was our Acme payment short by $250 on remittance PMT-8821?",
            priority="medium",
            metadata={"domain": "accounts_receivable"}
        )
        result_v1 = self.engine.run_once(case_v1)

        # Step 7 & 8: Confirm v1 loaded and runtime behavior reflects v1!
        self.assertEqual(result_v1["solve"]["strategy_version"], "v1")
        # Behavior change confirmed: get_customer_history was NOT executed under v1!
        self.assertNotIn("get_customer_history", result_v1["solve"]["actions"])
        self.assertIn("get_invoice", result_v1["solve"]["actions"])
        self.assertIn("get_payment", result_v1["solve"]["actions"])
        self.assertEqual(len(result_v1["solve"]["actions"]), 4)

        # Confirm DB records v1
        case_row_v1 = db.fetch_one("SELECT strategy_version FROM cases WHERE id = %s;", (case_v1.id,))
        self.assertEqual(case_row_v1["strategy_version"], "v1")
        run_row_v1 = db.fetch_one("SELECT strategy_version FROM agent_runs WHERE case_id = %s;", (case_v1.id,))
        self.assertEqual(run_row_v1["strategy_version"], "v1")

        # Reset back to v0 for clean state
        strategy_registry.promote_candidate("strat_l2_ar_v0")

    def test_04_end_to_end_closed_loop_learning(self):
        """DETERMINISTIC END-TO-END LEARNING TEST:
        CASE -> AGENT v0 -> TOOLS -> EVALUATION -> FAILURE -> REFLECTION -> EXPERIENCE -> CANDIDATE v1 -> PROMOTION -> NEW CASE -> AGENT LOADS v1.
        """
        # Ensure clean v0 baseline
        strategy_registry.promote_candidate("strat_l2_ar_v0")

        # 1. Simulate an early-escalation failure case:
        case_fail = Case(
            id=f"CASE_FAIL_{int(time.time())}",
            customer_id="cust1",
            description="Short payment issue on invoice INV-4471. Escalate immediately to executive controller.",
            priority="low",
            metadata={"domain": "accounts_receivable", "force_specialist_failure": False}
        )

        # 2. Evaluate with premature escalation (no payment tool called)
        evaluator = Evaluator()
        eval_res = evaluator.evaluate(
            case=case_fail.to_dict(),
            route_level=1,
            actions=["get_customer"],
            escalated=True,
            resolution_success=True,
            resolution_notes="Escalated before checking payment remittance records.",
            affected_agent="agent_l2_ar",
            strategy_version="v0",
        )

        # 3. Verify FAILURE_DETECTED in structured failures
        failures = eval_res.get("failures", [])
        self.assertTrue(len(failures) > 0)
        fail_types = [f["failure_type"] for f in failures]
        self.assertIn("WRONG_ESCALATION", fail_types)

        # 4. REFLECTION consumes failure and produces actionable strategy change
        refl = reflect(
            case_id=case_fail.id,
            memory={},
            lessons=["Premature escalation occurred."],
            case_description=case_fail.description,
            route_level=1,
            escalated=True,
            actions=["get_customer"],
            resolved=True,
            score_details=eval_res["details"],
        )

        self.assertIn("recommended_strategy_change", refl)
        rec = refl["recommended_strategy_change"]
        self.assertIsNotNone(rec)
        self.assertEqual(rec["change_type"], "TOOL_ORDER")
        self.assertEqual(rec["affected_agent"], "agent_l2_ar")

        # 5. CANDIDATE strategy v1 is synthesized from reflection
        candidate_v1 = generate_candidate_from_reflection(refl)
        self.assertIsNotNone(candidate_v1)
        self.assertEqual(candidate_v1.status, "CANDIDATE")
        self.assertEqual(candidate_v1.version, "v1")

        # Active strategy is still v0 before promotion
        self.assertEqual(strategy_registry.get_active_strategy(agent_id="agent_l2_ar").version, "v0")

        # 6. PROMOTION: Supervisor approves candidate v1
        promoted_v1 = strategy_registry.promote_candidate(
            candidate_v1.strategy_id,
            promoted_by="human_controller",
            notes="Approved after synthetic test validation."
        )
        self.assertEqual(promoted_v1.status, "ACTIVE")

        # 7. NEW CASE arrives -> runtime loads v1 directly!
        new_case = Case(
            id=f"CASE_AFTER_LEARNING_{int(time.time())}",
            customer_id="cust1",
            description="Why was our Acme payment short by $250 for invoice INV-4471?",
            priority="medium",
            metadata={"domain": "accounts_receivable"}
        )
        new_res = self.engine.run_once(new_case)

        # Verify new case used strategy v1
        self.assertEqual(new_res["solve"]["strategy_version"], "v1")
        self.assertEqual(new_res["solve"]["strategy_id"], candidate_v1.strategy_id)

        # Cleanup: restore v0
        strategy_registry.promote_candidate("strat_l2_ar_v0")

    def test_05_feedback_association_with_strategy_version(self):
        """Verify feedback is recorded with case, agent, and strategy version."""
        case_id = f"CASE_FB_{int(time.time())}"
        case = Case(
            id=case_id,
            customer_id="cust1",
            description="Status of invoice INV-4471 inquiry.",
            priority="low",
            metadata={"domain": "general_finance"}
        )
        self.engine.run_once(case)

        # Record thumbs down feedback via function
        fb_res = record_feedback(
            case_id=case_id,
            rating="negative",
            reason="Response could have included payment link",
            comment="Wanted direct link to pay online",
            agent_id="agent_l1_triage",
            strategy_version="v0"
        )
        self.assertEqual(fb_res["status"], "recorded")
        self.assertEqual(fb_res["strategy_version"], "v0")

        # Query database to confirm persisted columns
        fb_row = db.fetch_one(
            "SELECT agent_id, strategy_version, rating, reason FROM feedback WHERE id = %s;",
            (fb_res["feedback_id"],)
        )
        self.assertIsNotNone(fb_row)
        self.assertEqual(fb_row["agent_id"], "agent_l1_triage")
        self.assertEqual(fb_row["strategy_version"], "v0")
        self.assertEqual(fb_row["rating"], "negative")

    def test_06_rest_api_service_endpoints(self):
        """Verify clean REST API service endpoints for strategy management and learning telemetry."""
        # 1. GET /api/strategies
        res = self.client.get("/api/strategies")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("strategies", data)
        self.assertGreater(data["count"], 0)

        # 2. GET /api/strategies/active
        res_active = self.client.get("/api/strategies/active?agent_id=agent_l2_ar")
        self.assertEqual(res_active.status_code, 200)
        data_active = res_active.get_json()
        self.assertTrue(data_active["is_active"])
        self.assertEqual(data_active["strategy"]["agent_id"], "agent_l2_ar")

        # 3. GET /api/strategies/<id>
        res_spec = self.client.get("/api/strategies/strat_l2_ar_v0")
        self.assertEqual(res_spec.status_code, 200)
        self.assertEqual(res_spec.get_json()["strategy"]["strategy_id"], "strat_l2_ar_v0")

        # 4. POST /api/strategies/candidate
        res_cand = self.client.post("/api/strategies/candidate", json={
            "agent_id": "agent_l1_triage",
            "changes": {"strategy_instructions": "API test candidate instructions"},
            "rationale": "API automated test candidate"
        })
        self.assertEqual(res_cand.status_code, 201)
        cand_data = res_cand.get_json()["candidate"]
        cand_id = cand_data["strategy_id"]

        # 5. GET /api/strategies/diff
        res_diff = self.client.get(f"/api/strategies/diff?base=strat_l1_triage_v0&candidate={cand_id}")
        self.assertEqual(res_diff.status_code, 200)
        self.assertIn("differences", res_diff.get_json())

        # 6. POST /api/strategies/<id>/promote
        res_promo = self.client.post(f"/api/strategies/{cand_id}/promote", json={
            "promoted_by": "api_test_suite",
            "notes": "Promoted via automated test"
        })
        self.assertEqual(res_promo.status_code, 200)
        self.assertEqual(res_promo.get_json()["status"], "ACTIVE")

        # 7. POST /api/strategies/<id>/reject
        res_rej = self.client.post(f"/api/strategies/{cand_id}/reject", json={
            "rejected_by": "api_test_suite",
            "reason": "Test rejection"
        })
        self.assertEqual(res_rej.status_code, 200)
        self.assertEqual(res_rej.get_json()["status"], "REJECTED")

        # Restore L1 baseline
        strategy_registry.promote_candidate("strat_l1_triage_v0")

        # 8. GET /api/learning/experiences
        res_exp = self.client.get("/api/learning/experiences?limit=5")
        self.assertEqual(res_exp.status_code, 200)
        self.assertIn("experiences", res_exp.get_json())

        # 9. GET /api/learning/failures
        res_fail = self.client.get("/api/learning/failures?limit=5")
        self.assertEqual(res_fail.status_code, 200)
        self.assertIn("failures", res_fail.get_json())

        # 10. GET /api/learning/history
        res_hist = self.client.get("/api/learning/history?limit=10")
        self.assertEqual(res_hist.status_code, 200)
        self.assertIn("timeline", res_hist.get_json())
        self.assertIn("strategies", res_hist.get_json())


if __name__ == "__main__":
    unittest.main()
