"""Tests for Maximor AI Finance Operations: PostgreSQL tools, short payment resolution, and feedback."""
import unittest
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

    def test_database_records_retrieval(self):
        """Verify synthetic finance records are queried accurately from database."""
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

    def test_short_payment_resolution_and_escalation(self):
        """Verify that short payment query correctly routes and resolves via policy SHORT-PAY-01."""
        engine = ResolveLoopEngine()
        case = Case(
            id="TEST-FIN-01",
            customer_id="cust1",
            description="Why was our payment PMT-8821 short by $250 on invoice INV-4471?",
            priority="medium",
            metadata={"domain": "accounts_receivable"}
        )
        result = engine.run_once(case)
        self.assertTrue(result["solve"]["resolution"]["resolved"])
        self.assertIn("INV-4471", result["solve"]["resolution"]["response_text"])
        self.assertIn("250", result["solve"]["resolution"]["response_text"])

    def test_feedback_system_updates_experience_confidence(self):
        """Verify that recording positive/negative feedback updates experience confidence in DB."""
        case_id = "TEST-FEEDBACK-01"
        fb_pos = record_feedback(case_id=case_id, rating="positive", reason="Accurate calculation")
        self.assertEqual(fb_pos.get("status"), "recorded")

        fb_neg = record_feedback(case_id=case_id, rating="negative", reason="Disputed term")
        self.assertEqual(fb_neg.get("status"), "recorded")

    def test_web_endpoints(self):
        """Verify Flask endpoints for greet, status, and feedback."""
        client = app.test_client()

        # Status
        status_res = client.get("/api/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertIn("PostgreSQL", status_res.get_json()["database_backend"])

        # Greet
        greet_res = client.post("/api/voice/greet", json={"customer_id": "cust1"})
        self.assertEqual(greet_res.status_code, 200)
        self.assertIn("Thanks for calling Maximor AI", greet_res.get_json()["greeting_text"])

        # Feedback
        fb_res = client.post("/api/feedback", json={
            "case_id": "TEST-WEB-01",
            "rating": "positive",
            "reason": "Clear explanation"
        })
        self.assertEqual(fb_res.status_code, 200)
        self.assertTrue(fb_res.get_json()["success"])

    def test_warm_handoff_and_direct_orchestrator(self):
        """Verify warm handoffs vs direct orchestrator responses."""
        engine = ResolveLoopEngine()

        # 1. Direct Conversational Query to Orchestrator (No handoff required)
        case_gen = Case(
            id="TEST-GEN-01",
            customer_id="cust1",
            description="Who are you and what can you help me with?",
            priority="low"
        )
        res_gen = engine.run_once(case_gen)
        solve_gen = res_gen.get("solve", {})
        self.assertFalse(solve_gen.get("handoff_required"))
        self.assertEqual(solve_gen.get("acting_agent"), "Orchestrator (Call Director)")
        self.assertIn("Maximor AI", solve_gen.get("orchestrator_speech", ""))

        # 2. Specialist Finance Query (Warm handoff required)
        case_spec = Case(
            id="TEST-SPEC-01",
            customer_id="cust1",
            description="Why was payment PMT-8821 short by $250 on invoice INV-4471?",
            priority="medium"
        )
        res_spec = engine.run_once(case_spec)
        solve_spec = res_spec.get("solve", {})
        self.assertTrue(solve_spec.get("handoff_required"))
        self.assertIn("Accounts Receivable", solve_spec.get("specialist_role", ""))
        self.assertIsNotNone(solve_spec.get("handoff_context"))
        
        ctx = solve_spec["handoff_context"]
        self.assertEqual(ctx["case_id"], "TEST-SPEC-01")
        rec_ids = [r.get("external_id") for r in ctx.get("relevant_finance_records", []) if isinstance(r, dict)]
        self.assertIn("INV-4471", rec_ids)
        pol_str = str(ctx.get("relevant_policy", ""))
        self.assertIn("SHORT-PAY-01", pol_str)
        self.assertIn("I've received the context", solve_spec.get("specialist_speech", ""))

        # 3. Web Endpoint Verification
        client = app.test_client()
        call_res = client.post("/api/text/call", json={
            "customer_id": "cust1",
            "message": "Who are you?"
        })
        self.assertEqual(call_res.status_code, 200)
        call_json = call_res.get_json()
        self.assertFalse(call_json.get("handoff_required"))
        self.assertEqual(call_json.get("acting_agent"), "Orchestrator (Call Director)")

if __name__ == "__main__":
    unittest.main()
