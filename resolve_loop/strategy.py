"""Agent Strategy abstraction for ResolveLoop's closed-loop learning workforce.

A Strategy is a structured, versioned representation of HOW a specialist should
approach a class of cases — not just a free-form prompt.

Statuses:
- ACTIVE: Currently deployed in production runtime.
- CANDIDATE: Synthesized by reflection or evaluation; pending benchmark/verification.
- REJECTED: Failed evaluation or manual rejection.
- ARCHIVED: Previously active, superseded by newer version.
"""
import time
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger("maximor.strategy")

@dataclass
class AgentStrategy:
    strategy_id: str                      # e.g. "strat_l2_ar_v0"
    agent_id: str                         # e.g. "agent_l2_ar"
    agent_tier: int                       # 1=L1, 2=L2, 3=L3, 4=L4
    domain: str                           # accounts_receivable, accounts_payable, cash, etc.
    version: str = "v0"                   # "v0", "v1", "v2"
    name: str = "Strategy"
    status: str = "ACTIVE"                # ACTIVE, CANDIDATE, REJECTED, ARCHIVED
    source_or_reason: str = "baseline_specification"
    parent_strategy_id: Optional[str] = None
    goal: str = ""
    routing_signals: List[str] = field(default_factory=list)
    preferred_tools: List[str] = field(default_factory=list)
    preferred_tool_order: List[str] = field(default_factory=list)
    escalation_rules: List[str] = field(default_factory=list)
    memory_retrieval_preferences: Dict[str, Any] = field(default_factory=dict)
    evaluation_priorities: List[str] = field(default_factory=list)
    strategy_instructions: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def configuration(self) -> Dict[str, Any]:
        """Bundle operational parameters into a structured configuration dictionary."""
        return {
            "goal": self.goal,
            "routing_signals": self.routing_signals,
            "preferred_tools": self.preferred_tools,
            "preferred_tool_order": self.preferred_tool_order,
            "escalation_rules": self.escalation_rules,
            "memory_retrieval_preferences": self.memory_retrieval_preferences,
            "evaluation_priorities": self.evaluation_priorities,
            "strategy_instructions": self.strategy_instructions,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["configuration"] = self.configuration
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentStrategy":
        cfg = data.get("configuration", {})
        if not isinstance(cfg, dict):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}

        return cls(
            strategy_id=data.get("strategy_id") or data.get("id", "strat_unknown"),
            agent_id=data.get("agent_id", "agent_unknown"),
            agent_tier=int(data.get("agent_tier", 1)),
            domain=data.get("domain", "general_finance"),
            version=data.get("version", "v0"),
            name=data.get("name", "Unknown Strategy"),
            status=data.get("status", "ACTIVE"),
            source_or_reason=data.get("source_or_reason", "baseline_specification"),
            parent_strategy_id=data.get("parent_strategy_id"),
            goal=data.get("goal") or cfg.get("goal", ""),
            routing_signals=list(data.get("routing_signals") or cfg.get("routing_signals", [])),
            preferred_tools=list(data.get("preferred_tools") or cfg.get("preferred_tools", [])),
            preferred_tool_order=list(data.get("preferred_tool_order") or cfg.get("preferred_tool_order", [])),
            escalation_rules=list(data.get("escalation_rules") or cfg.get("escalation_rules", [])),
            memory_retrieval_preferences=dict(data.get("memory_retrieval_preferences") or cfg.get("memory_retrieval_preferences", {})),
            evaluation_priorities=list(data.get("evaluation_priorities") or cfg.get("evaluation_priorities", [])),
            strategy_instructions=data.get("strategy_instructions") or cfg.get("strategy_instructions", ""),
            created_at=float(data.get("created_at") if isinstance(data.get("created_at"), (int, float)) else time.time()),
            metadata=dict(data.get("metadata", {})),
        )

    def evolve(
        self,
        new_version: str,
        changes: Dict[str, Any],
        rationale: str = "",
        status: str = "CANDIDATE"
    ) -> "AgentStrategy":
        """Create an evolved child strategy version (e.g. v0 -> v1 CANDIDATE)."""
        evolved_data = self.to_dict()
        evolved_data["parent_strategy_id"] = self.strategy_id
        clean_prefix = self.strategy_id.rsplit("_v", 1)[0]
        evolved_data["strategy_id"] = f"{clean_prefix}_{new_version}"
        evolved_data["version"] = new_version
        evolved_data["status"] = status
        evolved_data["source_or_reason"] = rationale
        evolved_data["created_at"] = time.time()

        for k, v in changes.items():
            if k in evolved_data:
                evolved_data[k] = v

        evolved_data["metadata"]["evolution_rationale"] = rationale
        evolved_data["metadata"]["evolved_from"] = self.version
        return AgentStrategy.from_dict(evolved_data)


# ==============================================================================
# BASELINE ENTERPRISE FINANCE STRATEGIES (v0)
# ==============================================================================

STRATEGY_ORCHESTRATOR_V0 = AgentStrategy(
    strategy_id="strat_orchestrator_v0",
    agent_id="agent_orchestrator",
    agent_tier=0,
    domain="general_finance",
    version="v0",
    name="Call Director Orchestrator Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="Front-door intent detection, natural greeting, customer recognition, conversational FAQs, and warm handoff dispatch.",
    routing_signals=["who are you", "what is maximor", "what can you help", "hello", "hi"],
    preferred_tools=["get_customer", "search_policy"],
    preferred_tool_order=["get_customer", "search_policy"],
    escalation_rules=[
        "Transfer immediately to L1 for standard invoice status queries.",
        "Transfer immediately to L2 for short payments, early discounts, and AR disputes.",
        "Transfer to L3 for vendor billing variances, GL journal entries, and treasury runways.",
        "Transfer to L4 for overrides, ambiguous policies, or amounts > $50,000."
    ],
    memory_retrieval_preferences={"domains": ["general_finance"], "tags": ["intent", "triage"]},
    evaluation_priorities=["routing_accuracy", "greeting_quality", "zero_repetition"],
    strategy_instructions=(
        "Welcome caller warmly. Accurately detect domain and entity identifiers. "
        "Package structured handoff context and perform seamless warm transfer without repeating questions."
    ),
)

STRATEGY_L1_TRIAGE_V0 = AgentStrategy(
    strategy_id="strat_l1_triage_v0",
    agent_id="agent_l1_triage",
    agent_tier=1,
    domain="general_finance",
    version="v0",
    name="Finance Triage Baseline Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="First-contact factual verification, open invoice status lookup, and FAQ answering.",
    routing_signals=["status of invoice", "invoice status", "where is invoice", "overdue", "inv-4472"],
    preferred_tools=["get_customer", "get_invoice", "search_policy", "search_finance_records"],
    preferred_tool_order=["get_customer", "get_invoice", "search_policy"],
    escalation_rules=[
        "Escalate to L2 if customer mentions payment discrepancies, discounts, or short payments.",
        "Escalate to L3 if query involves cloud hosting bills (BILL-7701) or GL journal entries.",
        "Escalate to L4 if transaction exceeds $50,000 or policy interpretation is ambiguous (ESC-400)."
    ],
    memory_retrieval_preferences={"domains": ["general_finance", "accounts_receivable"], "tags": ["status", "lookup"]},
    evaluation_priorities=["first_contact_resolution", "tool_efficiency", "factual_accuracy"],
    strategy_instructions=(
        "Query NetSuite ERP for the requested invoice. Provide balance, status (e.g. Overdue, Partially Paid), "
        "and due date directly to caller. Do not attempt to authorize credits or discounts."
    ),
)

STRATEGY_L2_AR_V0 = AgentStrategy(
    strategy_id="strat_l2_ar_v0",
    agent_id="agent_l2_ar",
    agent_tier=2,
    domain="accounts_receivable",
    version="v0",
    name="Accounts Receivable Specialist Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="Resolve invoice payment discrepancies, short payments, and 2/10 Net 30 prompt payment discount credits.",
    routing_signals=["short payment", "short-pay", "discount", "2/10", "net 30", "difference", "pmt-8821"],
    preferred_tools=["get_customer", "get_invoice", "get_payment", "get_customer_history", "get_policy_version"],
    preferred_tool_order=["get_customer", "get_invoice", "get_payment", "get_customer_history", "get_policy_version"],
    escalation_rules=[
        "Escalate to L4 Executive Controller if short payment variance exceeds $50,000.",
        "Escalate to L4 if customer claims discount outside of the 10-calendar-day settlement window.",
        "Escalate only after required financial evidence (invoice + payment + policy) has been verified."
    ],
    memory_retrieval_preferences={"domains": ["accounts_receivable"], "tags": ["short_payment", "terms", "2_10_net_30"]},
    evaluation_priorities=["policy_compliance", "resolution_quality", "calculation_accuracy"],
    strategy_instructions=(
        "1. Retrieve invoice and payment remittance to establish exact dollar variance. "
        "2. Calculate calendar days between invoice date and payment date. "
        "3. Cross-reference corporate policy SHORT-PAY-01 for prompt payment discount window (2/10 Net 30). "
        "4. If settled within 10 days, approve 2% discount credit ($250) and mark balance $0. Otherwise explain overdue terms."
    ),
)

STRATEGY_L3_ACCOUNTING_V0 = AgentStrategy(
    strategy_id="strat_l3_accounting_v0",
    agent_id="agent_l3_accounting",
    agent_tier=3,
    domain="accounts_payable",
    version="v0",
    name="Accounting Authority Specialist Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="Reconcile multi-system GL variances, cloud hosting budget flux, and general ledger accrual entries.",
    routing_signals=["bill", "aws", "hosting", "variance", "flux", "journal entry", "je-2026-03", "bill-7701"],
    preferred_tools=["get_bill", "get_journal_entry", "get_finance_record", "search_policy"],
    preferred_tool_order=["get_bill", "get_journal_entry", "get_finance_record"],
    escalation_rules=[
        "Escalate to L4 if total variance exceeds $50,000 without corresponding unposted accrual.",
        "Escalate if vendor dispute requires legal or contractual renegotiation."
    ],
    memory_retrieval_preferences={"domains": ["accounts_payable", "close"], "tags": ["variance", "accrual", "gl"]},
    evaluation_priorities=["variance_accuracy", "journal_reconciliation", "auditability"],
    strategy_instructions=(
        "1. Retrieve vendor bill from accounts payable. "
        "2. Query month-end general ledger for corresponding accrual journal entries. "
        "3. Cross-reference operational usage drivers (e.g. Datadog GPU inference compute) to substantiate variance."
    ),
)

STRATEGY_L3_TREASURY_V0 = AgentStrategy(
    strategy_id="strat_l3_treasury_v0",
    agent_id="agent_l3_treasury",
    agent_tier=3,
    domain="cash",
    version="v0",
    name="Treasury Operations Specialist Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="Extract real-time treasury balances, cash positions, and 13-week operating runway forecasts.",
    routing_signals=["cash", "runway", "treasury", "position", "jpmc", "forecast", "liquidity"],
    preferred_tools=["get_cash_position", "get_forecast", "get_finance_record"],
    preferred_tool_order=["get_cash_position", "get_forecast"],
    escalation_rules=[
        "Escalate immediately to CFO / L4 if runway drops below 6 months.",
        "Escalate if unhedged FX exposure exceeds $1,000,000."
    ],
    memory_retrieval_preferences={"domains": ["cash"], "tags": ["runway", "liquidity", "forecast"]},
    evaluation_priorities=["factual_accuracy", "speed", "clarity"],
    strategy_instructions=(
        "Query live JPMorgan Chase treasury feed for operating checking and treasury money market balances. "
        "Report aggregate liquidity and 13-week runway model."
    ),
)

STRATEGY_L4_EXECUTIVE_V0 = AgentStrategy(
    strategy_id="strat_l4_executive_v0",
    agent_id="agent_l4_executive",
    agent_tier=4,
    domain="governance",
    version="v0",
    name="Executive Controller & Risk Strategy",
    status="ACTIVE",
    source_or_reason="Initial production baseline specification",
    goal="Prepare comprehensive audit dossiers for human CFO signoff under policy ESC-400 and handle material overrides.",
    routing_signals=["override", "ambiguous", "material", "50k", "$50,000", "cfo", "human review", "controller", "esc-400"],
    preferred_tools=["get_policy_version", "search_policy", "record_case_evidence", "get_customer_credit_profile"],
    preferred_tool_order=["get_policy_version", "search_policy", "record_case_evidence"],
    escalation_rules=[
        "Always package structured audit dossier for human Controller / CFO authorization.",
        "Do not auto-settle any transaction > $50,000 without signed escrow release."
    ],
    memory_retrieval_preferences={"domains": ["governance", "accounts_receivable"], "tags": ["esc-400", "override", "material"]},
    evaluation_priorities=["risk_containment", "audit_completeness", "regulatory_compliance"],
    strategy_instructions=(
        "Review high-impact transaction against governance policy ESC-400. Assemble structured audit dossier "
        "including customer history, exposure amount, and risk indicators. Dispatch case to Human Review Escrow."
    ),
)

BASELINE_STRATEGIES = [
    STRATEGY_ORCHESTRATOR_V0,
    STRATEGY_L1_TRIAGE_V0,
    STRATEGY_L2_AR_V0,
    STRATEGY_L3_ACCOUNTING_V0,
    STRATEGY_L3_TREASURY_V0,
    STRATEGY_L4_EXECUTIVE_V0,
]


class StrategyRegistry:
    """Registry and repository for versioned Agent Strategies with PostgreSQL backing."""
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/strategies.json")
        self._strategies: Dict[str, AgentStrategy] = {}
        self._load_defaults()
        self._sync_with_db()

    def _load_defaults(self):
        for s in BASELINE_STRATEGIES:
            self._strategies[s.strategy_id] = s

    def _sync_with_db(self):
        """Read from PostgreSQL agent_strategies table or seed defaults if empty."""
        try:
            from .db import db
            # Seed defaults if not present
            for s in BASELINE_STRATEGIES:
                db.execute(
                    """INSERT INTO agent_strategies (id, organization_id, agent_id, agent_tier, domain, version, name, status, configuration, source_or_reason, parent_strategy_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO NOTHING;""",
                    (
                        s.strategy_id, "org_apex", s.agent_id, s.agent_tier, s.domain,
                        s.version, s.name, s.status, json.dumps(s.configuration),
                        s.source_or_reason, s.parent_strategy_id
                    )
                )

            # Fetch all from DB
            rows = db.fetch_all("SELECT * FROM agent_strategies ORDER BY created_at ASC;")
            for r in rows:
                strat = AgentStrategy.from_dict(r)
                self._strategies[strat.strategy_id] = strat
        except Exception:
            # Fallback to local disk
            self._load_from_disk()

    def _load_from_disk(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for item in data.get("strategies", []):
                    strat = AgentStrategy.from_dict(item)
                    self._strategies[strat.strategy_id] = strat
            except Exception:
                pass

    def save_to_disk(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "strategies": [s.to_dict() for s in self._strategies.values()]
            }
            self.storage_path.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

    def get_strategy(self, strategy_id: str) -> Optional[AgentStrategy]:
        return self._strategies.get(strategy_id)

    def get_active_strategy(
        self,
        agent_id: Optional[str] = None,
        tier: Optional[int] = None,
        domain: str = ""
    ) -> AgentStrategy:
        """Find the ACTIVE strategy for the specified agent, tier, or domain."""
        # 1. Exact match on agent_id and ACTIVE status
        if agent_id:
            for s in self._strategies.values():
                if s.agent_id == agent_id and s.status == "ACTIVE":
                    return s

        # 2. Match on tier and domain and ACTIVE status
        if tier is not None:
            candidates = [
                s for s in self._strategies.values()
                if s.agent_tier == tier and s.status == "ACTIVE"
            ]
            if domain:
                for s in candidates:
                    if s.domain == domain:
                        return s
            if candidates:
                return candidates[0]

        # 3. Fallback default
        return STRATEGY_L1_TRIAGE_V0

    def register_strategy(self, strategy: AgentStrategy, persist_to_db: bool = True):
        self._strategies[strategy.strategy_id] = strategy
        self.save_to_disk()

        if persist_to_db:
            try:
                from .db import db
                db.execute(
                    """INSERT INTO agent_strategies (id, organization_id, agent_id, agent_tier, domain, version, name, status, configuration, source_or_reason, parent_strategy_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                           status = EXCLUDED.status,
                           configuration = EXCLUDED.configuration,
                           source_or_reason = EXCLUDED.source_or_reason,
                           updated_at = CURRENT_TIMESTAMP;""",
                    (
                        strategy.strategy_id, "org_apex", strategy.agent_id, strategy.agent_tier,
                        strategy.domain, strategy.version, strategy.name, strategy.status,
                        json.dumps(strategy.configuration), strategy.source_or_reason,
                        strategy.parent_strategy_id
                    )
                )
            except Exception as e:
                logger.warning("Failed to persist strategy to DB: %s", e)

    def create_candidate(
        self,
        agent_id: str,
        changes: Dict[str, Any],
        rationale: str,
        parent_strategy_id: Optional[str] = None
    ) -> AgentStrategy:
        """Explicitly create a new CANDIDATE strategy version for an agent."""
        base_strat = None
        if parent_strategy_id:
            base_strat = self.get_strategy(parent_strategy_id)
        if not base_strat:
            base_strat = self.get_active_strategy(agent_id=agent_id)

        # Determine next version
        cur_ver = base_strat.version
        try:
            next_num = int(cur_ver.lstrip("v")) + 1
            new_version = f"v{next_num}"
        except Exception:
            new_version = f"{cur_ver}_cand"

        candidate = base_strat.evolve(
            new_version=new_version,
            changes=changes,
            rationale=rationale,
            status="CANDIDATE"
        )
        self.register_strategy(candidate, persist_to_db=True)

        try:
            from .finance_tools import record_audit_event
            record_audit_event(
                case_id=None,
                action="CANDIDATE_STRATEGY_CREATED",
                details={
                    "source_agent": "Strategy Manager",
                    "destination_agent": "Strategy Registry",
                    "handoff_reason": "Candidate strategy version generated",
                    "confidence": 1.0,
                    "context_summary": f"Generated candidate {candidate.version} for {candidate.agent_id}: {rationale}",
                    "timestamp": time.time(),
                    "outcome": "created",
                    "strategy_id": candidate.strategy_id,
                    "agent_id": candidate.agent_id,
                    "from_version": base_strat.version,
                    "to_version": candidate.version,
                    "status": "CANDIDATE",
                    "reason": rationale,
                    "changes": changes,
                },
                actor_type="system",
                actor_id="strategy_manager"
            )
        except Exception:
            pass

        return candidate

    def promote_candidate(
        self,
        strategy_id: str,
        promoted_by: str = "supervisor",
        notes: str = ""
    ) -> AgentStrategy:
        """Promote a CANDIDATE strategy to ACTIVE, archiving the previous active version."""
        candidate = self.get_strategy(strategy_id)
        if not candidate:
            raise ValueError(f"Strategy {strategy_id} not found")

        # 1. Archive current active version for same agent
        previous_active = None
        for s in list(self._strategies.values()):
            if s.agent_id == candidate.agent_id and s.status == "ACTIVE" and s.strategy_id != strategy_id:
                s.status = "ARCHIVED"
                previous_active = s
                self.register_strategy(s, persist_to_db=True)

        # 2. Mark candidate active
        candidate.status = "ACTIVE"
        candidate.metadata["promoted_by"] = promoted_by
        candidate.metadata["promoted_at"] = time.time()
        candidate.metadata["promotion_notes"] = notes
        self.register_strategy(candidate, persist_to_db=True)

        # 3. Update PostgreSQL columns
        try:
            from .db import db
            db.execute(
                """UPDATE agent_strategies
                   SET status = 'ACTIVE', promoted_by = %s, promoted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s;""",
                (promoted_by, candidate.strategy_id)
            )
            if previous_active:
                db.execute(
                    """UPDATE agent_strategies
                       SET status = 'ARCHIVED', updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s;""",
                    (previous_active.strategy_id,)
                )
        except Exception as e:
            logger.warning("DB update on strategy promotion failed: %s", e)

        # 4. Audit event
        try:
            from .finance_tools import record_audit_event
            record_audit_event(
                case_id=None,
                action="STRATEGY_PROMOTED",
                details={
                    "source_agent": "Strategy Manager",
                    "destination_agent": "Production Runtime",
                    "handoff_reason": "Strategy promotion to active",
                    "confidence": 1.0,
                    "context_summary": f"Promoted strategy {candidate.strategy_id} to ACTIVE: {notes or candidate.source_or_reason}",
                    "timestamp": time.time(),
                    "outcome": "promoted",
                    "strategy_id": candidate.strategy_id,
                    "agent_id": candidate.agent_id,
                    "version": candidate.version,
                    "previous_version": previous_active.version if previous_active else None,
                    "promoted_by": promoted_by,
                    "reason": notes or candidate.source_or_reason,
                },
                actor_type="human_reviewer" if "human" in promoted_by.lower() else "system",
                actor_id=promoted_by
            )
        except Exception:
            pass

        logger.info("Promoted strategy %s to ACTIVE (archived previous active version)", strategy_id)
        return candidate

    def reject_candidate(
        self,
        strategy_id: str,
        rejected_by: str = "supervisor",
        reason: str = ""
    ) -> AgentStrategy:
        """Mark a CANDIDATE strategy as REJECTED for audit tracking."""
        candidate = self.get_strategy(strategy_id)
        if not candidate:
            raise ValueError(f"Strategy {strategy_id} not found")

        candidate.status = "REJECTED"
        candidate.metadata["rejected_by"] = rejected_by
        candidate.metadata["rejected_at"] = time.time()
        candidate.metadata["rejection_reason"] = reason
        self.register_strategy(candidate, persist_to_db=True)

        try:
            from .db import db
            db.execute(
                """UPDATE agent_strategies
                   SET status = 'REJECTED', rejected_by = %s, rejected_at = CURRENT_TIMESTAMP,
                       rejection_reason = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s;""",
                (rejected_by, reason, candidate.strategy_id)
            )
        except Exception as e:
            logger.warning("DB update on strategy rejection failed: %s", e)

        try:
            from .finance_tools import record_audit_event
            record_audit_event(
                case_id=None,
                action="STRATEGY_REJECTED",
                details={
                    "source_agent": "Strategy Manager",
                    "destination_agent": "Archive Registry",
                    "handoff_reason": "Candidate strategy rejected",
                    "confidence": 1.0,
                    "context_summary": f"Rejected candidate {candidate.strategy_id}: {reason}",
                    "timestamp": time.time(),
                    "outcome": "rejected",
                    "strategy_id": candidate.strategy_id,
                    "agent_id": candidate.agent_id,
                    "version": candidate.version,
                    "rejected_by": rejected_by,
                    "reason": reason,
                },
                actor_type="human_reviewer" if "human" in rejected_by.lower() else "system",
                actor_id=rejected_by
            )
        except Exception:
            pass

        logger.info("Rejected strategy %s (Reason: %s)", strategy_id, reason)
        return candidate

    def list_strategies(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[AgentStrategy]:
        res = list(self._strategies.values())
        if agent_id:
            res = [s for s in res if s.agent_id == agent_id]
        if status:
            res = [s for s in res if s.status == status]
        return res

# Global registry singleton
strategy_registry = StrategyRegistry()


def diff_strategies(base: AgentStrategy, candidate: AgentStrategy) -> Dict[str, Any]:
    """Generate structured diff between a base strategy and a candidate strategy."""
    diff_items = []

    # Preferred tools diff
    base_tools = list(base.preferred_tools)
    cand_tools = list(candidate.preferred_tools)
    tools_added = [t for t in cand_tools if t not in base_tools]
    tools_removed = [t for t in base_tools if t not in cand_tools]
    if tools_added or tools_removed:
        diff_items.append({
            "field": "preferred_tools",
            "type": "modified",
            "added": tools_added,
            "removed": tools_removed,
            "summary": f"Tools modified: +{tools_added} -{tools_removed}"
        })

    # Preferred tool order diff
    base_order = list(base.preferred_tool_order)
    cand_order = list(candidate.preferred_tool_order)
    if base_order != cand_order:
        diff_items.append({
            "field": "preferred_tool_order",
            "type": "reordered",
            "base": base_order,
            "candidate": cand_order,
            "summary": f"Tool order changed from {base_order} to {cand_order}"
        })

    # Routing signals diff
    base_signals = list(base.routing_signals)
    cand_signals = list(candidate.routing_signals)
    signals_added = [s for s in cand_signals if s not in base_signals]
    signals_removed = [s for s in base_signals if s not in cand_signals]
    if signals_added or signals_removed:
        diff_items.append({
            "field": "routing_signals",
            "type": "modified",
            "added": signals_added,
            "removed": signals_removed,
            "summary": f"Routing signals modified: +{signals_added} -{signals_removed}"
        })

    # Escalation rules diff
    base_rules = list(base.escalation_rules)
    cand_rules = list(candidate.escalation_rules)
    rules_added = [r for r in cand_rules if r not in base_rules]
    rules_removed = [r for r in base_rules if r not in cand_rules]
    if rules_added or rules_removed:
        diff_items.append({
            "field": "escalation_rules",
            "type": "modified",
            "added": rules_added,
            "removed": rules_removed,
            "summary": f"Escalation rules modified: +{rules_added} -{rules_removed}"
        })

    # Strategy instructions diff
    if base.strategy_instructions.strip() != candidate.strategy_instructions.strip():
        diff_items.append({
            "field": "strategy_instructions",
            "type": "updated",
            "base": base.strategy_instructions,
            "candidate": candidate.strategy_instructions,
            "summary": "Strategy instructions updated"
        })

    return {
        "base_strategy_id": base.strategy_id,
        "base_version": base.version,
        "candidate_strategy_id": candidate.strategy_id,
        "candidate_version": candidate.version,
        "agent_id": candidate.agent_id,
        "domain": candidate.domain,
        "differences": diff_items,
        "change_count": len(diff_items),
        "rationale": candidate.source_or_reason,
        "summary": [d["summary"] for d in diff_items] or ["No configuration changes detected between versions"]
    }


def generate_candidate_from_reflection(
    reflection_result: Dict[str, Any],
    base_strategy: Optional[AgentStrategy] = None
) -> Optional[AgentStrategy]:
    """Given a reflection result containing recommended_strategy_changes, synthesize and persist a CANDIDATE strategy."""
    rec = reflection_result.get("recommended_strategy_change")
    if not rec:
        recs = reflection_result.get("recommended_strategy_changes", [])
        if recs:
            rec = recs[0]
    if not rec:
        return None

    affected_agent = rec.get("affected_agent")
    if not base_strategy:
        base_strategy = strategy_registry.get_active_strategy(agent_id=affected_agent)

    cur_ver = base_strategy.version
    try:
        next_num = int(cur_ver.lstrip("v")) + 1
        new_version = f"v{next_num}"
    except Exception:
        new_version = f"{cur_ver}_cand"

    field_to_modify = rec.get("field")
    suggested_val = rec.get("suggested_value")
    rationale = rec.get("rationale") or rec.get("change") or "Reflection-driven strategy evolution"

    changes = {}
    if field_to_modify and suggested_val is not None:
        changes[field_to_modify] = suggested_val

    if rec.get("change_type") == "TOOL_ORDER" and "preferred_tool_order" in changes:
        changes["preferred_tools"] = list(set(base_strategy.preferred_tools + changes["preferred_tool_order"]))

    candidate = base_strategy.evolve(
        new_version=new_version,
        changes=changes,
        rationale=rationale,
        status="CANDIDATE"
    )

    strategy_registry.register_strategy(candidate, persist_to_db=True)

    try:
        from .finance_tools import record_audit_event
        record_audit_event(
            case_id=reflection_result.get("case_id"),
            action="CANDIDATE_STRATEGY_CREATED",
            details={
                "source_agent": "Reflection Engine",
                "destination_agent": "Strategy Registry",
                "handoff_reason": "Reflection-driven strategy evolution candidate",
                "confidence": 1.0,
                "context_summary": f"Evolved candidate {candidate.version} for {candidate.agent_id}: {rationale}",
                "timestamp": time.time(),
                "outcome": "candidate_created",
                "strategy_id": candidate.strategy_id,
                "agent_id": candidate.agent_id,
                "from_version": base_strategy.version,
                "to_version": candidate.version,
                "status": "CANDIDATE",
                "reason": rationale,
                "changes": changes,
            },
            actor_type="system",
            actor_id="reflection_engine"
        )
    except Exception:
        pass

    return candidate
