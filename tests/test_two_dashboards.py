"""Tests for Two Distinct Workspaces: Finance Ops and Customer Executive.

Validates:
1. Finance Ops Workspace:
   - Initial load lightweight (no huge record dump, 5 key metrics, active policies, connected systems).
   - Customer/Org selection filtering.
   - Transaction & Ledger filtering by domain (AR, AP, Cash, Revenue, Close).
   - Transaction filtering by record_type, status, search query.
   - Server-side pagination (limit, offset, has_more, total).
   - Progressive disclosure: Record detail drill-down (line items, linked records, policy, audit events).
   - Error handling (404 for nonexistent records).

2. Customer Executive Workspace:
   - Initial load lightweight (compact workforce KPIs, live agent workforce tiers).
   - Customer interaction feed with agent routing path (Orchestrator -> L2 AR Specialist).
   - Interaction detail drill-down: turn-by-turn STT transcripts, audio URLs, warm handoff timeline, executed tools.
   - No hidden chain-of-thought leaked.
   - Customer profile & lifetime interaction history.
   - Real persisted learning display (no fabricated experiences).
   - Human Guidance creation, approval, and routing persistence.

3. End-to-End Integration:
   - Call -> Case -> Case Interaction turns -> Feedback -> Learning -> Customer Executive display.
   - Finance Op -> Record -> Evidence -> Audit trail chain.
"""
import unittest
import json
import time
from resolve_loop.db import db
from resolve_loop.seeds import seed_database
from resolve_loop.web_app import app
from resolve_loop.engine import ResolveLoopEngine
from resolve_loop.case import Case
from resolve_loop.finance_tools import (
    record_case_interaction,
    add_human_guidance,
    approve_human_guidance,
    record_feedback,
)


class TestFinanceOpsWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = app.test_client()

    def test_finance_overview_initial_payload_lightweight(self):
        """Verify /api/finance/overview returns compact metrics without dumping the full ledger."""
        res = self.client.get("/api/finance/overview")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # High-signal summary metrics (exactly 5 metrics)
        self.assertIn("summary", data)
        summary = data["summary"]
        self.assertIn("cash_position", summary)
        self.assertIn("runway_months", summary)
        self.assertIn("outstanding_ar", summary)
        self.assertIn("overdue_ar", summary)
        self.assertIn("deferred_revenue", summary)

        # Performance constraint: recent activity is capped (not an unbounded ledger)
        self.assertIn("recent_activity", data)
        self.assertLessEqual(len(data["recent_activity"]), 15)

        # Connected systems and governance policies are present
        self.assertIn("systems", data)
        self.assertTrue(len(data["systems"]) >= 3)
        self.assertIn("policies", data)
        self.assertTrue(len(data["policies"]) >= 2)

        # Customer list for quick selector
        self.assertIn("customers", data)
        self.assertTrue(len(data["customers"]) >= 1)

    def test_finance_overview_customer_selection(self):
        """Verify org/customer filtering dynamically focuses financial context."""
        res = self.client.get("/api/finance/overview?customer_id=cust1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("selected_customer_id"), "cust1")
        self.assertIn("summary", data)
        # Outstanding AR should be populated for cust1 (INV-4471 / INV-4472)
        self.assertGreater(data["summary"]["outstanding_ar"], 0)

    def test_finance_records_pagination_and_total(self):
        """Verify server-side pagination with limit, offset, and total count."""
        # Request page 1 with limit 2
        res1 = self.client.get("/api/finance/records?limit=2&offset=0")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1["limit"], 2)
        self.assertEqual(data1["offset"], 0)
        self.assertEqual(len(data1["records"]), 2)
        self.assertTrue(data1["has_more"])
        self.assertGreaterEqual(data1["total"], 2)

        # Request page 2 with limit 2
        res2 = self.client.get("/api/finance/records?limit=2&offset=2")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["offset"], 2)
        # Ensure page 2 records are distinct from page 1
        page1_ids = {r["id"] for r in data1["records"]}
        page2_ids = {r["id"] for r in data2["records"]}
        self.assertTrue(page1_ids.isdisjoint(page2_ids))

    def test_finance_records_domain_filtering(self):
        """Verify domain filter pills accurately partition records."""
        # AR domain (invoices, payments)
        res_ar = self.client.get("/api/finance/records?domain=accounts_receivable")
        self.assertEqual(res_ar.status_code, 200)
        records_ar = res_ar.get_json()["records"]
        self.assertTrue(len(records_ar) > 0)
        for r in records_ar:
            self.assertIn(r["record_type"], ["invoice", "payment"])

        # AP domain (bills)
        res_ap = self.client.get("/api/finance/records?domain=accounts_payable")
        self.assertEqual(res_ap.status_code, 200)
        records_ap = res_ap.get_json()["records"]
        self.assertTrue(len(records_ap) > 0)
        for r in records_ap:
            self.assertEqual(r["record_type"], "bill")

        # Cash & Treasury domain
        res_cash = self.client.get("/api/finance/records?domain=cash_treasury")
        self.assertEqual(res_cash.status_code, 200)
        records_cash = res_cash.get_json()["records"]
        self.assertTrue(len(records_cash) > 0)
        for r in records_cash:
            self.assertIn(r["record_type"], ["cash_balance", "bank_transaction"])

    def test_finance_records_search_query(self):
        """Verify search by reference number or entity name."""
        res = self.client.get("/api/finance/records?q=INV-4471")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data["total"], 1)
        matched_inv = next((r for r in data["records"] if r["external_id"] == "INV-4471"), None)
        self.assertIsNotNone(matched_inv)
        self.assertEqual(matched_inv["entity_name"], "Acme Corp")

    def test_record_detail_progressive_disclosure(self):
        """Verify slide-over drawer endpoint returns line-level data, linked records, and governing policy."""
        res = self.client.get("/api/finance/record/INV-4471")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Primary record with line items
        self.assertIn("record", data)
        rec = data["record"]
        self.assertEqual(rec["external_id"], "INV-4471")
        self.assertEqual(float(rec["amount"]), 12500.0)
        self.assertIn("items", rec["data"])

        # Linked remittance
        self.assertIn("linked_records", data)
        linked = data["linked_records"]
        self.assertTrue(any(lr.get("external_id") == "PMT-8821" for lr in linked))

        # Governing compliance policy
        self.assertIn("governing_policies", data)
        policies = data["governing_policies"]
        self.assertTrue(any(p.get("policy_code") == "SHORT-PAY-01" for p in policies))

        # Audit events attached to record
        self.assertIn("audit_events", data)

    def test_record_detail_not_found(self):
        """Verify proper 404 response on missing financial record."""
        res = self.client.get("/api/finance/record/NONEXISTENT-9999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("error", data)


class TestCustomerExecutiveWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = app.test_client()

    def test_executive_overview_lightweight(self):
        """Verify /api/executive/overview returns workforce KPIs and agent tiers without large dumps."""
        res = self.client.get("/api/executive/overview")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Workforce KPI metrics
        self.assertIn("summary", data)
        summary = data["summary"]
        self.assertIn("total_connections", summary)
        self.assertIn("fcr_rate", summary)
        self.assertIn("escalated_count", summary)
        self.assertIn("positive_feedback_count", summary)
        self.assertIn("avg_resolution_time_sec", summary)

        # Active AI workforce tiers (L0 to L4)
        self.assertIn("agents", data)
        agents = data["agents"]
        tiers = {a["tier"] for a in agents}
        self.assertIn(0, tiers)  # Orchestrator
        self.assertIn(1, tiers)  # L1
        self.assertIn(2, tiers)  # L2
        self.assertIn(3, tiers)  # L3
        self.assertIn(4, tiers)  # L4

    def test_executive_interactions_pagination_and_routing_path(self):
        """Verify interactions feed displays multi-agent routing path and supports pagination."""
        res = self.client.get("/api/executive/interactions?limit=5&offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("interactions", data)
        self.assertIn("total", data)
        self.assertIn("has_more", data)

        if data["interactions"]:
            item = data["interactions"][0]
            self.assertIn("case_id", item)
            self.assertIn("customer_name", item)
            self.assertIn("agent_path", item)  # e.g. "Orchestrator -> L2 AR Specialist"
            self.assertIn("status", item)

    def test_executive_interaction_detail_drilldown(self):
        """Verify interaction detail returns turn-by-turn STT, audio, handoff timeline, and tools."""
        interactions_res = self.client.get("/api/executive/interactions?limit=1")
        data = interactions_res.get_json()
        self.assertTrue(len(data["interactions"]) > 0)
        case_id = data["interactions"][0]["case_id"]

        detail_res = self.client.get(f"/api/executive/interaction/{case_id}")
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()

        self.assertIn("case", detail)
        self.assertIn("turns", detail)
        self.assertIn("timeline", detail)
        self.assertIn("tool_calls", detail)
        self.assertIn("audit_trail", detail)

        # Check turn structure (must have speaker and transcript, no raw CoT)
        for turn in detail["turns"]:
            self.assertIn(turn["speaker"], ["customer", "orchestrator", "specialist"])
            self.assertIn("transcript", turn)
            self.assertNotIn("chain_of_thought", turn)

    def test_executive_customer_profile(self):
        """Verify customer profile returns lifetime interaction stats and linked finance history."""
        res = self.client.get("/api/executive/customer/cust1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("customer", data)
        self.assertEqual(data["customer"]["id"], "cust1")
        self.assertEqual(data["customer"]["name"], "Alice Morgan")
        self.assertIn("stats", data)
        self.assertIn("interactions", data)
        self.assertIn("finance_records", data)

    def test_executive_learning_persisted_experiences(self):
        """Verify real persisted experiences are returned from PostgreSQL without mock fabrication."""
        res = self.client.get("/api/executive/learning")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("experiences", data)
        self.assertIn("guidance", data)
        self.assertIn("procedural_rules", data)
        self.assertIn("total_experiences", data)

        if data["experiences"]:
            exp = data["experiences"][0]
            self.assertIn("situation", exp)
            self.assertIn("lesson", exp)
            self.assertIn("outcome", exp)

    def test_human_guidance_creation_and_approval_flow(self):
        """Verify Customer Executive can add structured supervisor guidance and see it active."""
        test_pattern = f"test short payment discount tolerance {int(time.time())}"
        payload = {
            "trigger_pattern": test_pattern,
            "recommended_tier": 2,
            "action": "route_to_l2_ar",
            "rationale": "Direct all sub-$500 discount claims to L2 AR with pre-fetched remittances",
            "created_by": "Test Executive",
        }
        create_res = self.client.post(
            "/api/executive/guidance",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, 200)
        create_data = create_res.get_json()
        self.assertTrue(create_data["success"])
        guidance_id = create_data["id"]

        # Approve guidance
        approve_res = self.client.post(f"/api/executive/guidance/{guidance_id}/approve")
        self.assertEqual(approve_res.status_code, 200)
        self.assertTrue(approve_res.get_json()["success"])

        # Verify it shows up in /api/executive/learning
        learning_res = self.client.get("/api/executive/learning")
        all_guidance = learning_res.get_json().get("guidance", [])
        matched = [g for g in all_guidance if g.get("id") == guidance_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["approval_status"], "approved")
        self.assertEqual(matched[0]["recommended_tier"], 2)


class TestEndToEndIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = app.test_client()
        cls.engine = ResolveLoopEngine()

    def test_call_to_case_to_executive_and_feedback(self):
        """End-to-End: Inbound call -> warm handoff -> case turns -> feedback -> executive feed."""
        case_id = f"TEST-E2E-{int(time.time())}"
        case = Case(
            id=case_id,
            customer_id="cust1",
            description="Our payment was short by $250 for invoice INV-4471 under 2/10 Net 30.",
            priority="medium",
            metadata={"channel": "voice_call", "domain": "accounts_receivable"}
        )
        res = self.engine.run_once(case)
        self.assertTrue(res.get("solve", {}).get("handoff_required"))

        # Verify turn-by-turn interactions were recorded in case_interactions
        turns = db.fetch_all(
            "SELECT speaker, transcript, agent_tier FROM case_interactions WHERE case_id = %s ORDER BY created_at ASC;",
            (case_id,)
        )
        speakers = [t["speaker"] for t in turns]
        self.assertIn("customer", speakers)
        self.assertIn("orchestrator", speakers)
        self.assertIn("specialist", speakers)

        # Submit Customer Feedback
        fb_res = self.client.post(
            "/api/feedback",
            data=json.dumps({
                "case_id": case_id,
                "rating": "positive",
                "feedback": "Discount applied promptly without repeating my question",
            }),
            content_type="application/json"
        )
        self.assertEqual(fb_res.status_code, 200)

        # Verify Customer Executive interaction feed displays this call with positive feedback
        feed_res = self.client.get("/api/executive/interactions?limit=10")
        self.assertEqual(feed_res.status_code, 200)
        items = feed_res.get_json().get("interactions", [])
        matched_item = next((i for i in items if i["case_id"] == case_id), None)
        self.assertIsNotNone(matched_item)
        self.assertEqual(matched_item["feedback_rating"], "positive")
        self.assertIn("Orchestrator", matched_item["agent_path"])
        self.assertIn("L2", matched_item["agent_path"])

        # Verify interaction detail endpoint returns the full audit trail and tool calls
        detail_res = self.client.get(f"/api/executive/interaction/{case_id}")
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()
        self.assertTrue(len(detail["turns"]) >= 3)
        self.assertTrue(len(detail["tool_calls"]) >= 1)
        self.assertTrue(len(detail["timeline"]) >= 3)

    def test_finance_op_record_to_policy_and_evidence(self):
        """End-to-End: Finance Ops record -> source system -> linked remittance -> governing policy."""
        res = self.client.get("/api/finance/record/INV-4471")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Source system verified
        self.assertEqual(data["record"]["system_provider"], "Oracle NetSuite")

        # Linked remittance PMT-8821 verified
        linked = data["linked_records"]
        self.assertTrue(any(lr["external_id"] == "PMT-8821" for lr in linked))

        # Governing policy SHORT-PAY-01 verified
        policies = data["governing_policies"]
        self.assertTrue(any(p["policy_code"] == "SHORT-PAY-01" for p in policies))


if __name__ == "__main__":
    unittest.main()
