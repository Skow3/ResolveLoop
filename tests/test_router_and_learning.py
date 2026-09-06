from resolve_loop.engine import ResolveLoopEngine
from resolve_loop.case import Case


def test_router_level_generation_without_llm():
    engine = ResolveLoopEngine()
    c = Case(id="TEST1", customer_id="cust1", description="Where is my order?", priority="low", metadata={})
    route = engine.route_case(c)
    # Should return a route level between 1 and 4
    assert 1 <= route.get("route_level", 0) <= 4
