"""Structured Handoff Context and Multi-Agent Warm Transfer Architecture for Maximor AI.

Maintains continuous case state, structured context passing, and multi-hop escalations:
Orchestrator (Call Director) -> L1 Triage -> L2 Investigation -> L3 Authority -> L4 Executive / Human Review.
"""
import time
import uuid
import decimal
import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

def make_json_serializable(val: Any) -> Any:
    if isinstance(val, decimal.Decimal):
        return float(val)
    elif isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    elif isinstance(val, uuid.UUID):
        return str(val)
    elif isinstance(val, dict):
        return {str(k): make_json_serializable(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple, set)):
        return [make_json_serializable(v) for v in val]
    return val

@dataclass
class AgentDescriptor:
    id: str
    name: str
    tier: int # 0=Orchestrator, 1=L1, 2=L2, 3=L3, 4=L4
    role: str
    authority_scope: str

# Standard Agent Personas
AGENT_ORCHESTRATOR = AgentDescriptor(
    id="agent_orchestrator",
    name="Orchestrator (Call Director)",
    tier=0,
    role="Call Director & Front Door",
    authority_scope="Greeting, intent classification, conversational FAQs, initial routing"
)

AGENT_L1_TRIAGE = AgentDescriptor(
    id="agent_l1_triage",
    name="Finance Triage Specialist",
    tier=1,
    role="Basic Finance Triage Specialist",
    authority_scope="Simple invoice status, payment verification, customer lookup, standard policy search"
)

AGENT_L2_AR = AgentDescriptor(
    id="agent_l2_ar",
    name="Accounts Receivable Specialist",
    tier=2,
    role="Accounts Receivable Specialist",
    authority_scope="Short-payment resolution, terms matching (2/10 Net 30), credit discounts, policy SHORT-PAY-01"
)

AGENT_L2_ORDER = AgentDescriptor(
    id="agent_l2_order",
    name="Order & Fulfillment Specialist",
    tier=2,
    role="Order & Fulfillment Specialist",
    authority_scope="Order tracking, shipment verification, standard order cancellations"
)

AGENT_L3_ACCOUNTING = AgentDescriptor(
    id="agent_l3_accounting",
    name="Accounting Authority Specialist",
    tier=3,
    role="Accounting Authority Specialist",
    authority_scope="Multi-system variance, ASC 606 revenue recognition, journal accruals, reconciliation"
)

AGENT_L3_TREASURY = AgentDescriptor(
    id="agent_l3_treasury",
    name="Treasury & Liquidity Specialist",
    tier=3,
    role="Treasury & Liquidity Specialist",
    authority_scope="JPMC Treasury balances, cash position, 13-week forecast, liquidity models"
)

AGENT_L4_EXECUTIVE = AgentDescriptor(
    id="agent_l4_executive",
    name="Executive Controller & Risk Authority",
    tier=4,
    role="Executive Controller & Risk Authority",
    authority_scope="Policy overrides, material variances (> $50k), legal exceptions, human review preparation"
)

@dataclass
class HandoffContext:
    """Structured Context passed between agents during warm handoffs."""
    handoff_id: str
    case_id: str
    customer: Dict[str, Any]
    organization: Dict[str, Any]
    original_customer_request: str
    conversation_summary: str
    detected_domain: str
    issue_type: str
    priority: str
    current_agent: Dict[str, Any]
    receiving_agent: Dict[str, Any]
    reason_for_handoff: str
    information_already_collected: List[Dict[str, Any]] = field(default_factory=list)
    entities_already_identified: Dict[str, Any] = field(default_factory=dict)
    tools_already_used: List[str] = field(default_factory=list)
    relevant_finance_records: List[Dict[str, Any]] = field(default_factory=list)
    relevant_policy: Optional[Dict[str, Any]] = None
    relevant_retrieved_experiences: List[str] = field(default_factory=list)
    previous_agent_outcome: str = ""
    unresolved_questions: List[str] = field(default_factory=list)
    recommended_next_action: str = ""
    routing_confidence: float = 0.94
    resolution_confidence: float = 0.95
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return make_json_serializable(asdict(self))

@dataclass
class CallSessionState:
    """Continuous session state across multiple turns and agent handoffs."""
    session_id: str
    case_id: str
    customer: Dict[str, Any]
    active_agent: Dict[str, Any]
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    agent_handoff_history: List[Dict[str, Any]] = field(default_factory=list)
    accumulated_context: Dict[str, Any] = field(default_factory=dict)
    tool_activity: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_experiences: List[Dict[str, Any]] = field(default_factory=list)
    resolved: bool = False
    feedback: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return make_json_serializable(asdict(self))
