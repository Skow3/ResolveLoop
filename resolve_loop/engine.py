"""Core ResolveLoop engine orchestrating CASE -> ROUTE -> SOLVE -> TOOLS -> EVALUATE -> REFLECT -> STORE EXPERIENCE -> IMPROVE -> NEXT CASE"""
import time
import json
from typing import Dict, Any, List
from pathlib import Path

from .config import CASES_PATH
from .memory import MemoryStore
from .mock_services import get_customer_profile, get_customer_history
from .llm import request_llm
from .tools import fetch_customer_history, kb_search, open_ticket_for_case
from .case import Case
from .evaluator import Evaluator
from .store import ExperienceStore
from .reflect import reflect
from .benchmark import Benchmark

class ResolveLoopEngine:
    def __init__(self):
        self.mem = MemoryStore()
        self.ev = Evaluator()
        self.store = ExperienceStore()
        self.bench = Benchmark()

    def load_cases(self) -> List[Case]:
        if not CASES_PATH.exists():
            return []
        try:
            data = json.loads(CASES_PATH.read_text())
            return [Case(**c) for c in data.get("cases", [])]
        except Exception:
            return []

    def save_case_result(self, case_id: str, result: Dict[str, Any]):
        entry = {
            "case_id": case_id,
            "description": result.get("case", {}).get("description") if isinstance(result, dict) else None,
            "route": result.get("route"),
            "solve": result.get("solve"),
            "eval": result.get("score"),
            "timestamp": time.time(),
        }
        self.store.add_experience(entry)

    def route_case(self, case: Case) -> Dict[str, Any]:
        # Try to use an LLM to plan routing if configured; else fallback to heuristic
        prompt = (
            f"Given a customer case: '{case.description}' with priority {case.priority}, "
            "produce a routing level (1-4) and a suggested plan. Respond with a simple 'level: <n>; plan: <text>'."
        )
        llm_out = request_llm(prompt)
        if llm_out:
            # naive parse
            lvl = 1
            plan = f"Route to L{lvl}"
            try:
                # extract a number after 'level' or 'L'
                import re
                m = re.search(r"level\s*[:=]?\s*(\d)", llm_out, re.IGNORECASE)
                if m:
                    lvl = int(m.group(1))
                m2 = re.search(r"L(\d)", llm_out, re.IGNORECASE)
                if m2:
                    lvl = int(m2.group(1))
                plan = llm_out.strip()
            except Exception:
                lvl = 1
                plan = f"Route to L{lvl}"
        return {"route_level": max(1, min(4, lvl)), "plan": plan}

        # Fallback heuristic if LLm not available
        lvl = 1
        text = case.description.lower()
        if case.priority in ("high", "critical") or any(k in text for k in ["policy", "legal", "risk"]):
            lvl = 4
        elif case.priority == "medium":
            lvl = 2
        elif any(k in text for k in ["complex", "multi"]):
            lvl = 3
        else:
            lvl = 1
        return {"route_level": lvl, "plan": f"Route to L{lvl}"}

    def solve_case(self, case: Case, route: Dict[str, Any]) -> Dict[str, Any]:
        # Perform actions using mock tools
        actions = []
        history = fetch_customer_history(case.customer_id)
        if history:
            actions.append("fetch_history")
        kb = kb_search(case.description)
        if kb:
            actions.append("kb_lookup")
        ticket = open_ticket_for_case(case, "auto_resolved" if case.priority in ("low", "medium") else "pending")
        actions.append("open_ticket")
        resolution = {
            "resolved": case.priority in ("low", "medium"),
            "ticket": ticket,
            "kb_hits": len(kb),
        }
        return {"actions": actions, "resolution": resolution}

    def evaluate_and_reflect(self, case: Case, route: Dict[str, Any], solve_result: Dict[str, Any], escalated: bool) -> Dict[str, Any]:
        # Evaluate
        score_obj = self.ev.evaluate(case.to_dict(), route.get("route_level", 1), solve_result.get("actions", []), escalated, solve_result.get("resolution", {}).get("resolved", False))
        # Reflect
        lessons = [f"Route L{route.get('route_level',1)} used.", f"KB hits: {solve_result.get('resolution',{}).get('kb_hits',0)}"]
        reflection = reflect(case.id, self.mem.get_case_memory(case.id) or {}, lessons)
        return {"score": score_obj, "reflection": reflection}

    def run_once(self, case: Case) -> Dict[str, Any]:
        # Retrieve similar past experiences for this case description (learning signal)
        similar = self.store.find_similar_experiences(case.description, limit=3)
        route = self.route_case(case)
        solve_result = self.solve_case(case, route)
        escalated = route.get("route_level",1) >= 4
        eval_reflect = self.evaluate_and_reflect(case, route, solve_result, escalated)

        # Persist memory and experience
        self.mem.update_case_memory(case.id, {"route": route, "solve": solve_result, "eval": eval_reflect["score"]})
        # Persist a richer experience record including description and retrieval context
        self.save_case_result(case.id, {
            "case": case.to_dict(),
            "route": route,
            "solve": solve_result,
            "eval": eval_reflect["score"],
            "experience_retrieval": [{"case_id": e.get("case_id"), "description": e.get("description")} for e in similar]
        })
        self.bench.record({**case.to_dict(), "route": route, "solve": solve_result, "score": eval_reflect["score"]})
        return {
            "case": case.to_dict(),
            "route": route,
            "solve": solve_result,
            "score": eval_reflect["score"],
            "reflection": eval_reflect["reflection"],
            "experience_retrieval": similar,
        }

def run_demo_loop():
    engine = ResolveLoopEngine()
    cases = engine.load_cases()
    results = []
    if not cases:
        return {"error": "No cases found in data/cases.json"}
    for c in cases:
        res = engine.run_once(c)
        results.append(res)
    return {"results": results, "benchmark": engine.bench.summarize()}
