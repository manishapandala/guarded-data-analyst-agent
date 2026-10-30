# Engineering notes

## Trust boundary

The agent may inspect an explicitly supplied CSV through four read-only tools: schema profiling, grouped aggregation, time trends, and anomaly detection. It cannot execute arbitrary code, write files on the user's behalf, contact people, upload data, or mutate the source dataset.

## Tool contract

The planner produces a named tool and typed argument dictionary. The executor rejects tools outside the allowlist and validates required columns before calculation. Results use a stable JSON-ready envelope with the question, decision trace, selected tool, arguments, and output.

## Guardrail behavior

Potential side effects are blocked before planning or tool execution. The public evaluation includes a destructive request and verifies that no tool is called. These keyword checks are an educational baseline, not a complete security boundary for a production natural-language system.

## Evaluation contract

- Five supported questions must route to the expected tool.
- A side-effect request must stop at the input guardrail.
- Aggregations and anomaly results are checked against deterministic generated data.
- Published latency is a local measurement and not a production service-level claim.

## Extension path

An LLM or MCP client can replace the deterministic planner while retaining the same allowlist, typed arguments, executor, audit trace, and evaluation cases. A production build would add identity-aware authorization, row-level data policies, sandboxing, redaction, and human approval for any action-capable tool.
