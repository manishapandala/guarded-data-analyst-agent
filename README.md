# Guarded Data Analyst Agent

A provider-neutral analytics agent that routes natural-language questions to allowlisted, read-only tools. It validates the dataset, blocks side-effect requests, returns structured results, and records every guardrail and tool decision in an audit trace.

## What it demonstrates

- tool routing for profiling, aggregation, trends, and anomaly detection;
- input guardrails that block destructive or representational actions;
- structured tool arguments and JSON-ready outputs;
- deterministic offline evaluation of routing decisions;
- traceability from user question to final data artifact.

## Run

```bash
python -m pip install -r requirements-dev.txt
ruff check .
python -m unittest discover -s tests -v
python run_demo.py
```

See [ENGINEERING.md](ENGINEERING.md) for the trust boundary, tool contract, guardrail behavior, and extension path.

## Outputs

- `sample_transactions.csv` — 480 generated transactions;
- `demo_summary.json` — routing accuracy, guardrail result, and local latency;
- `sample_agent_output.json` — a complete question → guardrail → plan → tool → output trace.

## Scope

The public build deliberately uses deterministic routing and generated data so its behavior can be tested without an API key. A hosted LLM or MCP adapter can be added later without changing the allowlisted tool layer, guardrails, or evaluation contract.

## Repository map

- `analytics_agent.py` — planner, guardrails, allowlisted tools, structured results, and traces;
- `run_demo.py` — generated transaction data and deterministic evaluation harness;
- `tests/` — behavioral tests for routing, calculations, blocked actions, and trace structure;
- `index.html` — GitHub Pages case study with downloadable outputs;
- `.github/workflows/tests.yml` — lint, test, and demo regeneration on each push.
