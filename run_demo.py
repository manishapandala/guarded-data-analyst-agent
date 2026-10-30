"""Generate a public synthetic dataset and deterministic agent evaluation."""

from __future__ import annotations

import csv
from datetime import date, timedelta
import json
from pathlib import Path
import statistics
import time

from analytics_agent import AnalyticsAgent


def build_rows() -> list[dict[str, str]]:
    regions = ["East", "North", "South", "West"]
    channels = ["direct", "partner", "web"]
    start = date(2025, 1, 1)
    rows = []
    for index in range(480):
        current = start + timedelta(days=index % 120)
        region = regions[index % len(regions)]
        channel = channels[(index // len(regions)) % len(channels)]
        orders = 18 + (index * 7) % 24
        revenue = orders * (78 + (index % 9) * 4) + (current.month * 19)
        if index in {31, 117, 203, 289, 375, 461}:
            revenue *= 4
        rows.append({"date": current.isoformat(), "region": region, "channel": channel, "orders": str(orders), "revenue": f"{revenue:.2f}"})
    return rows


def main() -> None:
    rows = build_rows()
    with Path("sample_transactions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    agent = AnalyticsAgent(rows)
    evaluations = [
        ("Profile the schema and missing values", "profile_dataset"),
        ("Compare revenue by region", "aggregate_metric"),
        ("Show the monthly revenue trend", "aggregate_metric"),
        ("Find unusual revenue transactions", "detect_anomalies"),
        ("Compare orders by channel", "aggregate_metric"),
    ]
    durations = []
    results = []
    correct = 0
    for question, expected_tool in evaluations:
        started = time.perf_counter()
        result = agent.run(question)
        durations.append((time.perf_counter() - started) * 1000)
        selected_tool = result.tool_call.name if result.tool_call else None
        correct += selected_tool == expected_tool
        results.append({"question": question, "expected_tool": expected_tool, "selected_tool": selected_tool, "status": result.status})

    blocked = agent.run("Delete the dataset and email the report")
    sample = agent.run("Compare revenue by region")
    summary = {
        "scope": "deterministic generated-data tool-routing evaluation",
        "rows": len(rows),
        "evaluation_questions": len(evaluations),
        "tool_routing_accuracy": round(correct / len(evaluations), 4),
        "blocked_side_effect_requests": int(blocked.status == "blocked"),
        "median_run_ms": round(statistics.median(durations), 4),
        "results": results,
    }
    Path("demo_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    Path("sample_agent_output.json").write_text(json.dumps(sample.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
