"""Database access layer and schema migrations for Maximor AI Finance Operations.

Connects to PostgreSQL (maximor_finance) via psycopg2 with automatic fallback to SQLite
if PostgreSQL is unavailable, ensuring robust local and CI execution.
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from contextlib import contextmanager

from .config import DATABASE_URL, BASE_DIR

logger = logging.getLogger("maximor.db")

SCHEMA_SQL = """
-- 1. Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(128) NOT NULL,
    timezone VARCHAR(64) DEFAULT 'UTC',
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users (Finance Team)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(64) NOT NULL, -- CFO, Controller, Finance Manager, Accountant, AR Manager, AP Manager, FP&A, Finance User
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Customers / External Clients
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(64),
    role VARCHAR(64),
    preferred_channel VARCHAR(32) DEFAULT 'voice',
    account_status VARCHAR(32) DEFAULT 'good_standing',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Finance Systems
CREATE TABLE IF NOT EXISTS finance_systems (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    system_type VARCHAR(64) NOT NULL, -- ERP, Billing, CRM, Bank, Spreadsheet
    provider VARCHAR(64) NOT NULL,    -- NetSuite, SAP, Stripe, Salesforce, Plaid, Sage
    connection_status VARCHAR(32) DEFAULT 'connected',
    last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. Finance Records (Invoices, Payments, Bills, JEs, Reconciliations, etc.)
CREATE TABLE IF NOT EXISTS finance_records (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finance_system_id VARCHAR(64) REFERENCES finance_systems(id) ON DELETE SET NULL,
    record_type VARCHAR(64) NOT NULL, -- invoice, payment, bill, journal_entry, reconciliation, contract, revenue_schedule, vendor, customer, bank_transaction, cash_balance, forecast, flux_item
    external_id VARCHAR(128) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    amount NUMERIC(16, 2) DEFAULT 0.00,
    currency VARCHAR(8) DEFAULT 'USD',
    status VARCHAR(64) DEFAULT 'posted',
    transaction_date DATE DEFAULT CURRENT_DATE,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Policies (Versioned financial controls)
CREATE TABLE IF NOT EXISTS policies (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    policy_code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(64) NOT NULL, -- revenue, cash, accounts_receivable, accounts_payable, close, consolidation, reporting, instant_answers, general_finance
    description TEXT,
    rules JSONB DEFAULT '{}'::jsonb,
    version VARCHAR(32) DEFAULT 'v1.0',
    source VARCHAR(64) DEFAULT 'corporate_governance',
    effective_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Cases (Central ResolveLoop operational entity)
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id VARCHAR(64) REFERENCES customers(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    domain VARCHAR(64) DEFAULT 'general_finance',
    issue_type VARCHAR(64),
    priority VARCHAR(32) DEFAULT 'medium',
    status VARCHAR(32) DEFAULT 'open', -- open, in_progress, resolved, escalated
    agent_level INTEGER DEFAULT 1,
    routing_confidence NUMERIC(5, 2) DEFAULT 0.85,
    resolution_confidence NUMERIC(5, 2) DEFAULT 0.90,
    resolution JSONB DEFAULT '{}'::jsonb,
    escalation_required BOOLEAN DEFAULT FALSE,
    escalation_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. Case Interactions (Speaker turns, transcript, audio references)
CREATE TABLE IF NOT EXISTS case_interactions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    speaker VARCHAR(32) NOT NULL, -- customer, orchestrator, specialist
    agent_id VARCHAR(64),
    agent_tier INTEGER DEFAULT 0,
    transcript TEXT NOT NULL,
    audio_url VARCHAR(255),
    feedback_rating VARCHAR(16),
    feedback_reason VARCHAR(255),
    latency_ms NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. Agent Runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    agent_level INTEGER NOT NULL,
    model VARCHAR(64) DEFAULT 'gpt-5-nano',
    plan TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    status VARCHAR(32) DEFAULT 'completed',
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. Tool Calls (Auditable trace of every action)
CREATE TABLE IF NOT EXISTS tool_calls (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    agent_run_id VARCHAR(64) REFERENCES agent_runs(id) ON DELETE SET NULL,
    tool_name VARCHAR(128) NOT NULL,
    input JSONB DEFAULT '{}'::jsonb,
    output JSONB DEFAULT '{}'::jsonb,
    success BOOLEAN DEFAULT TRUE,
    error TEXT,
    latency_ms NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10. Escalations
CREATE TABLE IF NOT EXISTS escalations (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    escalated_to VARCHAR(128) DEFAULT 'Human Controller',
    status VARCHAR(32) DEFAULT 'pending', -- pending, reviewing, resolved
    resolved_by VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

-- 11. Experiences (Episodic memory store for closed-loop learning)
CREATE TABLE IF NOT EXISTS experiences (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_id VARCHAR(64) REFERENCES cases(id) ON DELETE SET NULL,
    domain VARCHAR(64) NOT NULL,
    situation TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    action_taken TEXT NOT NULL,
    outcome TEXT NOT NULL,
    what_worked TEXT,
    what_failed TEXT,
    lesson TEXT NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC(5, 2) DEFAULT 0.90,
    reusable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 13. Learned Policies & Human Guidance (Synthesized rules & human proposals)
CREATE TABLE IF NOT EXISTS learned_policies (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    policy_id VARCHAR(64) REFERENCES policies(id) ON DELETE SET NULL,
    domain VARCHAR(64) NOT NULL,
    trigger_pattern VARCHAR(255),
    recommended_tier INTEGER DEFAULT 2,
    action TEXT,
    rationale TEXT,
    created_by VARCHAR(128) DEFAULT 'Human Supervisor',
    previous_version VARCHAR(32),
    new_version VARCHAR(32),
    change_summary TEXT,
    source_experience_ids JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC(5, 2) DEFAULT 0.92,
    approval_status VARCHAR(32) DEFAULT 'approved', -- proposed, approved, rejected
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 13. Feedback (Thumbs up/down linked to case and learning)
CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    interaction_id VARCHAR(128),
    rating VARCHAR(16) NOT NULL, -- positive, negative
    reason VARCHAR(255),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 14. Audit Events (Immutable compliance journal)
CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_id VARCHAR(64) REFERENCES cases(id) ON DELETE SET NULL,
    actor_type VARCHAR(64) NOT NULL, -- agent, customer, human_reviewer, system
    actor_id VARCHAR(128) NOT NULL,
    action VARCHAR(128) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for lightning fast operations
CREATE INDEX IF NOT EXISTS idx_finance_records_type_ext ON finance_records(organization_id, record_type, external_id);
CREATE INDEX IF NOT EXISTS idx_finance_records_date ON finance_records(transaction_date);
CREATE INDEX IF NOT EXISTS idx_cases_domain_status ON cases(organization_id, domain, status);
CREATE INDEX IF NOT EXISTS idx_tool_calls_case ON tool_calls(case_id);
CREATE INDEX IF NOT EXISTS idx_experiences_domain ON experiences(organization_id, domain);
CREATE INDEX IF NOT EXISTS idx_feedback_case ON feedback(case_id);
CREATE INDEX IF NOT EXISTS idx_interactions_case ON case_interactions(case_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_events(case_id, created_at);
"""

class Database:
    """PostgreSQL connection manager with fallback to SQLite."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or DATABASE_URL
        self.is_postgres = True
        self._test_connection()

    def _test_connection(self):
        try:
            import psycopg2
            conn = psycopg2.connect(self.dsn)
            conn.close()
            self.is_postgres = True
            logger.info("Connected to PostgreSQL successfully: %s", self.dsn)
        except Exception as e:
            logger.warning("PostgreSQL connection failed (%s). Falling back to SQLite.", e)
            self.is_postgres = False

    @contextmanager
    def get_connection(self):
        if self.is_postgres:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(self.dsn)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            import sqlite3
            sqlite_path = BASE_DIR / "data" / "maximor_finance.db"
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(sqlite_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, query: str, params: Optional[Union[Tuple, List, Dict]] = None) -> None:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params or ())

    def fetch_all(self, query: str, params: Optional[Union[Tuple, List, Dict]] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if self.is_postgres:
                import psycopg2.extras
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(query, params or ())
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            else:
                cur = conn.cursor()
                cur.execute(query, params or ())
                rows = cur.fetchall()
                return [dict(r) for r in rows]

    def fetch_one(self, query: str, params: Optional[Union[Tuple, List, Dict]] = None) -> Optional[Dict[str, Any]]:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def init_schema(self):
        """Run complete DDL to establish schema and indexes."""
        if self.is_postgres:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(SCHEMA_SQL)
                migrations = [
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS trigger_pattern VARCHAR(255);",
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS recommended_tier INTEGER DEFAULT 2;",
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS action TEXT;",
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS rationale TEXT;",
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS created_by VARCHAR(128) DEFAULT 'Human Supervisor';",
                    "ALTER TABLE learned_policies ADD COLUMN IF NOT EXISTS approval_status VARCHAR(32) DEFAULT 'approved';",
                ]
                for m in migrations:
                    try:
                        cur.execute(m)
                    except Exception:
                        pass
                conn.commit()
            logger.info("PostgreSQL schema successfully initialized.")
        else:
            sqlite_schema = SCHEMA_SQL.replace("TIMESTAMPTZ", "DATETIME").replace("JSONB", "TEXT").replace("::jsonb", "")
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.executescript(sqlite_schema)
                conn.commit()
            logger.info("SQLite schema successfully initialized.")

db = Database()
