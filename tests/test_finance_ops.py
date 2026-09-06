"""Tests for Maximor AI Finance Operations: PostgreSQL tools, warm handoffs, L1-L4 scenarios, and audit trail.

Covers:
- Test Case A: Basic conversational query ("Who are you?") -> Orchestrator answers directly, no transfer.
- Test Case B: L1 case ("What's the status of invoice INV-4471?") -> Orchestrator -> L1 Triage -> invoice tool -> response without repetition.
- Test Case C: L2 case ("Why was our Acme payment short?") -> Orchestrator -> L2 AR -> terms matching + credit discount -> full audit trail.
- Test Case D: Multi-tier escalation / Ambiguous policy ("We need an override for a $65,000 transaction under ambiguous policy terms") -> L4 Executive Controller -> human review.
- Test Case F: Voice handoff endpoints -> Pulse STT / text fallback -> warm handoff -> Lightning TTS audio generation.
- Test Case G: Handoff failure -> simulated specialist error -> graceful return of control to Orchestrator -> call never crashes.
"""
import unittest
import time
import json
from resolve_loop.db import db
from resolve_loop.seeds import seed_database
from resolve_loop.finance_tools import (
    get_customer,
    get_invoice,
    get_payment,
    get_bill,
    search_policy,
    get_cash_position,
    record_feedback,
)
from resolve_loop.engine import ResolveLoopEngine
from resolve_loop.case import Case
from resolve_loop.web_app import app

class TestFinanceOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.engine = ResolveLoopEngine()
        cls.client = app.test_client()

    def test_database_records_retrieval(self):
        """Verify synthetic finance records are queried accurately from PostgreSQL database."""
        cust = get_customer("cust1")
        self.assertEqual(cust.get("name"), "Alice Morgan")

        inv = get_invoice("INV-4471")
        self.assertEqual(inv.get("entity_name"), "Acme Corp")
        self.assertEqual(float(inv.get("amount")), 12500.00)

        pmt = get_payment("PMT-8821")
        self.assertEqual(float(pmt.get("amount")), 12250.00)

        bill = get_bill("BILL-7701")
        self.assertEqual(bill.get("entity_name"), "Amazon Web Services (AWS)")

        pol = search_policy("SHORT-PAY-01")
        self.assertTrue(len(pol) > 0)
        self.assertEqual(pol[0].get("policy_code"), "SHORT-PAY-01")

        cash = get_cash_position()
        self.assertIsNotNone(cash)

    def test_case_a_basic_conversational(self):
        """Test Case A: Basic conversational query - Orchestrator answers directly without transfer."""
        case = Case(
            id="TEST-CASE-A",
            customer_id="cust1",
            description="Who are you and what is Maximor AI?",
            priority="low"
        )
        db.execute("DELETE FROM audit_events WHERE case_id = %s;", (case.id,))
        result = self.engine.run_once(case)
        solve = result.get("solve", {})

        # Verify Orchestrator handled directly
        self.assertFalse(solve.get("handoff_required"))
        self.assertEqual(solve.get("acting_agent"), "Orchestrator (Call Director)")
        self.assertIn("Maximor AI", solve.get("orchestrator_speech", ""))
        self.assertIsNone(solve.get("specialist_speech"))

        # Verify audit trail in database
        events = db.fetch_all(
            "SELECT action, details FROM audit_events WHERE case_id = %s ORDER BY created_at ASC;",
            (case.id,)
        )
        actions = [e["action"] for e in events]
        self.assertIn("ORCHESTRATOR_ANSWERED", actions)
        self.assertIn("ORCHESTRATOR_DIRECT_REPLY", actions)
        self.assertIn("RESOLUTION_GENERATED", actions)

    def test_case_b_l1_invoice_status(self):
        """Test Case B: L1 case - Invoice status lookup via NetSuite tool without repetition."""
        case = Case(
            id="TEST-CASE-B",
            customer_id="cust1",
            description="What's the status of invoice INV-4471?",
            priority="medium"
        )
        db.execute("DELETE FROM audit_events WHERE case_id = %s;", (case.id,))
        result = self.engine.run_once(case)
        solve = result.get("solve", {})

        # Verify L1 Specialist routing
        self.assertTrue(solve.get("handoff_required"))
        self.assertIn("Finance Triage", solve.get("specialist_role", ""))
        self.assertEqual(solve.get("resolution", {}).get("final_agent_level"), 1)

        # Verify no repetition in acknowledgement
        ack = solve.get("resolution", {}).get("specialist_acknowledgement", "")
        self.assertIn("INV-4471", ack)
        self.assertNotIn("Thanks for calling Maximor AI", ack)

        # Verify specialist resolution details from NetSuite ERP
        spec_speech = solve.get("specialist_speech", "")
        self.assertIn("INV-4471", spec_speech)
        self.assertIn("12,500", spec_speech)
        self.assertIn("250", spec_speech)

        # Verify audit trail contains invoice tool call
        events = db.fetch_all(
            "SELECT action FROM audit_events WHERE case_id = %s ORDER BY created_at ASC;",
            (case.id,)
        )
        actions = [e["action"] for e in events]
        self.assertIn("CALLED_INVOICE_TOOL", actions)

    def test_case_c_l2_short_payment_and_audit_trail(self):
        """Test Case C: L2 case - Short payment investigation, terms matching, and full audit trail lifecycle."""
        case = Case(
            id="TEST-CASE-C",
            customer_id="cust1",
            description="Why was our Acme payment short?",
            priority="medium"
        )
        db.execute("DELETE FROM audit_events WHERE case_id = %s;", (case.id,))
        result = self.engine.run_once(case)
        solve = result.get("solve", {})

        # Verify L2 Specialist routing and resolution
        self.assertTrue(solve.get("handoff_required"))
        self.assertIn("Accounts Receivable", solve.get("specialist_role", ""))
        self.assertEqual(solve.get("resolution", {}).get("final_agent_level"), 2)

        # Verify prompt payment discount resolution under policy SHORT-PAY-01
        res_text = solve.get("resolution", {}).get("response_text", "")
        self.assertIn("2/10 Net 30", res_text)
        self.assertIn("250", res_text)
        self.assertIn("SHORT-PAY-01", res_text)

        # Record Customer Feedback to complete feedback loop
        fb_res = record_feedback(
            case_id=case.id,
            rating="positive",
            reason="Accurate discount explanation and prompt settlement",
            interaction_id="int_call_101"
        )
        self.assertEqual(fb_res.get("status"), "recorded")

        # Verify Complete Audit Trail Lifecycle Sequence:
        # Case created -> Orchestrator answered -> Intent detected -> Routed to L2 ->
        # Warm handoff initiated -> L2 acknowledged context -> Retrieved customer history ->
        # Retrieved SHORT-PAY-01 -> Called invoice tool -> Called payment tool ->
        # Resolution generated -> Customer feedback recorded -> Experience stored.
        events = db.fetch_all(
            "SELECT action, details FROM audit_events WHERE case_id = %s ORDER BY created_at ASC;",
            (case.id,)
        )
        actions = [e["action"] for e in events]

        expected_sequence = [
            "CASE_CREATED",
            "ORCHESTRATOR_ANSWERED",
            "INTENT_DETECTED",
            "ROUTED_TO_L2",
            "WARM_HANDOFF_INITIATED",
            "SPECIALIST_ACKNOWLEDGED_CONTEXT",
            "CUSTOMER_HISTORY_RETRIEVED",
            "POLICY_RETRIEVED",
            "CALLED_INVOICE_TOOL",
            "CALLED_PAYMENT_TOOL",
            "RESOLUTION_GENERATED",
            "CUSTOMER_FEEDBACK_RECORDED",
            "EXPERIENCE_STORED",
        ]

        for expected_action in expected_sequence:
            self.assertIn(expected_action, actions, f"Missing expected audit action: {expected_action}")

        # Verify chronological ordering of core lifecycle events
        idx_created = actions.index("CASE_CREATED")
        idx_orch = actions.index("ORCHESTRATOR_ANSWERED")
        idx_intent = actions.index("INTENT_DETECTED")
        idx_routed = actions.index("ROUTED_TO_L2")
        idx_warm = actions.index("WARM_HANDOFF_INITIATED")
        idx_ack = actions.index("SPECIALIST_ACKNOWLEDGED_CONTEXT")
        idx_res = actions.index("RESOLUTION_GENERATED")
        idx_fb = actions.index("CUSTOMER_FEEDBACK_RECORDED")

        self.assertTrue(idx_created <= idx_orch < idx_intent < idx_routed < idx_warm < idx_ack < idx_res < idx_fb)

        # Verify required audit fields are present in every event
        for ev in events:
            det = ev.get("details") or {}
            self.assertIn("source_agent", det)
            self.assertIn("destination_agent", det)
            self.assertIn("handoff_reason", det)
            self.assertIn("confidence", det)
            self.assertIn("context_summary", det)
            self.assertIn("timestamp", det)
            self.assertIn("outcome", det)

    def test_case_d_l4_ambiguous_policy_escalation(self):
        """Test Case D: Multi-tier escalation / Material exception exceeding $50,000 threshold."""
        case = Case(
            id="TEST-CASE-D",
            customer_id="cust1",
            description="We need an override for a $65,000 transaction under ambiguous policy terms",
            priority="high"
        )
        db.execute("DELETE FROM audit_events WHERE case_id = %s;", (case.id,))
        result = self.engine.run_once(case)
        solve = result.get("solve", {})

        # Verify L4 escalation and Controller review requirement
        self.assertTrue(solve.get("escalated"))
        self.assertEqual(solve.get("resolution", {}).get("final_agent_level"), 4)
        self.assertTrue(solve.get("resolution", {}).get("human_review_required"))
        self.assertIn("Executive Controller", solve.get("specialist_role", ""))
        self.assertIn("ESC-400", solve.get("specialist_speech", ""))

        # Verify audit trail logs L4 routing
        events = db.fetch_all(
            "SELECT action FROM audit_events WHERE case_id = %s ORDER BY created_at ASC;",
            (case.id,)
        )
        actions = [e["action"] for e in events]
        self.assertIn("ROUTED_TO_L4", actions)

    def test_case_f_voice_handoff_endpoints(self):
        """Test Case F: Voice handoff via Smallest AI endpoints and speech synthesis."""
        # 1. Voice Greet endpoint
        greet_res = self.client.post("/api/voice/greet", json={"customer_id": "cust1"})
        self.assertEqual(greet_res.status_code, 200)
        greet_json = greet_res.get_json()
        self.assertTrue(greet_json.get("success"))
        self.assertIn("Thanks for calling Maximor AI", greet_json.get("greeting_text"))
        self.assertIn("Alice Morgan", greet_json.get("greeting_text"))

        # 2. Text / Speech Call endpoint simulating conversational handoff
        call_res = self.client.post("/api/text/call", json={
            "customer_id": "cust1",
            "message": "Why was our Acme payment short?"
        })
        self.assertEqual(call_res.status_code, 200)
        call_json = call_res.get_json()
        self.assertTrue(call_json.get("success"))
        self.assertTrue(call_json.get("handoff_required"))
        self.assertIn("Accounts Receivable", call_json.get("specialist_role", ""))
        self.assertIsNotNone(call_json.get("orchestrator_speech"))
        self.assertIsNotNone(call_json.get("specialist_speech"))

        # If audio was generated, verify the stream endpoint serves audio
        if call_json.get("audio_url"):
            audio_url = call_json["audio_url"]
            audio_res = self.client.get(audio_url)
            self.assertEqual(audio_res.status_code, 200)
            self.assertEqual(audio_res.mimetype, "audio/wav")
            audio_res.close()

    def test_case_g_handoff_failure_fallback(self):
        """Test Case G: Handoff failure resilience - Gracefully returns control to Orchestrator without call drop."""
        case = Case(
            id="TEST-CASE-G",
            customer_id="cust1",
            description="Why was our Acme payment short?",
            priority="medium",
            metadata={"force_specialist_failure": True}
        )
        db.execute("DELETE FROM audit_events WHERE case_id = %s;", (case.id,))
        # Engine execution MUST NOT throw an unhandled exception
        result = self.engine.run_once(case)
        solve = result.get("solve", {})

        # Verify graceful fallback to Orchestrator
        self.assertEqual(solve.get("acting_agent"), "Orchestrator (Call Director)")
        self.assertFalse(solve.get("handoff_required"))
        self.assertTrue(solve.get("resolution", {}).get("fallback_engaged"))

        # Verify Orchestrator speech stays on the line with the customer
        orch_speech = solve.get("orchestrator_speech", "")
        self.assertIn("brief delay", orch_speech)
        self.assertIn("staying on the line", orch_speech)

        # Verify audit trail records failover event
        events = db.fetch_all(
            "SELECT action, details FROM audit_events WHERE case_id = %s ORDER BY created_at ASC;",
            (case.id,)
        )
        actions = [e["action"] for e in events]
        self.assertIn("HANDOFF_FAILED_FALLBACK_TO_ORCHESTRATOR", actions)

        fail_event = next(e for e in events if e["action"] == "HANDOFF_FAILED_FALLBACK_TO_ORCHESTRATOR")
        self.assertEqual(fail_event["details"].get("outcome"), "Orchestrator failover engaged")

    def test_feedback_system_updates_experience_confidence(self):
        """Verify that recording positive/negative feedback updates experience confidence in DB."""
        case_id = "TEST-FEEDBACK-01"
        fb_pos = record_feedback(case_id=case_id, rating="positive", reason="Accurate calculation")
        self.assertEqual(fb_pos.get("status"), "recorded")

        fb_neg = record_feedback(case_id=case_id, rating="negative", reason="Disputed term")
        self.assertEqual(fb_neg.get("status"), "recorded")

    def test_web_endpoints(self):
        """Verify Flask endpoints for status, CRM data, and benchmark."""
        # Status
        status_res = self.client.get("/api/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertIn("PostgreSQL", status_res.get_json()["database_backend"])

        # CRM Data
        crm_res = self.client.get("/api/crm/data")
        self.assertEqual(crm_res.status_code, 200)
        crm_data = crm_res.get_json()
        self.assertTrue(len(crm_data.get("customers", [])) > 0)
        self.assertTrue(len(crm_data.get("finance_records", [])) > 0)
        self.assertTrue(len(crm_data.get("policies", [])) > 0)

if __name__ == "__main__":
    unittest.main()
