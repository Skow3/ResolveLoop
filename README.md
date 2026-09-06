# ResolveLoop MVP

ResolveLoop is an experience-driven multi-agent customer-support MVP for hackathon Track 1: Automated Agent Engineering.

## What is ResolveLoop?
- A hierarchy of L1-L4 agents routing, solving, and learning from cases.
- A memory layer that stores customer/case experiences and a learning loop that improves routing and tool usage over time.
- A lightweight tool layer that mocks CRM, orders, payments, and a knowledge base.

## Architecture (quick view)
- CUSTOMER → INPUT/VOICE → RESOLVELOOP ROUTER → L1/L2/L3/L4 → TOOL LAYER → KNOWLEDGE BASE/ORDERS/CRM/PAYMENTS
- Evaluator → Reflection → MEMORY → LEARNING POLICY → NEXT CASE

## Agent levels
- L1: Basic Support
- L2: Investigation
- L3: Expert
- L4: Escalation / Final Expert

## Learning loop (high level)
- CASE → ROUTE → SOLVE → USE TOOLS → EVALUATE → REFLECT → REMEMBER → IMPROVE → NEXT CASE

## How to run
- Uses the OpenAI API (gpt-5-nano) for the agents when enabled, and a small mock for tools when not configured.
- Real memory persistence without external services (data/memories.json, data/experiences.json).
- A simple data-driven benchmark to demonstrate before/after improvements.

## What you’ll see in the MVP
- A demo harness that loads sample cases, routes to an agent level, invokes mock tools, evaluates, reflects, and stores experiences.
- A simple dashboard-like console output via the CLI showing routing decisions, tool usage, and learning outcomes.

## How to run locally (quick start)
- Install Python 3.9+ (if not already installed).
- Ensure dependencies exist (requirements.txt is minimal for MVP). Use a virtualenv if desired.
- Copy .env.example to .env and set OPENAI_API_KEY if you want to enable LLM-powered routing, otherwise keep RESOLVELOOP_USE_LLM=0.
- Run: python -m resolve_loop.main

## Environment variables
- OPENAI_API_KEY: API key for OpenAI (optional if LLM is disabled)
- SMALLEST_API_KEY: Reserved for optional voice feature (not required for MVP)
- RESOLVELOOP_USE_LLM: 1 to enable LLM calls, 0 to use heuristic routing (default 0 for safe MVP)

## Learning and benchmarks
- The MVP stores experiences and can retrieve similar past cases to influence future routing and tool usage.
- A simple before/after benchmark demonstrates improvement in routing decisions and tool efficiency.

## Notes
- This is a hackathon MVP focused on end-to-end flow and demonstrable learning, not production-grade infra.
- No external authentication is required.

![ResolveLoop Architecture Diagram](diagram-placeholder.png)

"ResolveLoop is not just a multi-agent system. It is a multi-agent system with an experience-driven learning loop."
