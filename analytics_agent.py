"""Guarded, deterministic analytics agent with typed tools and audit traces."""

from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import math
from pathlib import Path
import re
from typing import Any


BLOCKED_ACTIONS = {"delete", "drop", "email", "overwrite", "send", "upload", "write"}
ALLOWED_DIMENSIONS = {"month", "region", "channel"}
ALLOWED_METRICS = {"orders", "revenue"}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentResult:
    question: str
    status: str
    answer: str
    tool_call: ToolCall | None
    data: Any
    trace: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trace"] = list(self.trace)
        return payload


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("dataset must contain at least one row")
    required = {"date", "region", "channel", "orders", "revenue"}
    if not required.issubset(rows[0]):
        raise ValueError(f"dataset is missing required columns: {sorted(required - set(rows[0]))}")
    return rows


def profile_dataset(rows: list[dict[str, str]]) -> dict[str, Any]:
    columns = list(rows[0])
    missing = {column: sum(not row.get(column, "").strip() for row in rows) for column in columns}
    return {"rows": len(rows), "columns": columns, "missing_values": missing}


def aggregate_metric(rows: list[dict[str, str]], metric: str, dimension: str) -> list[dict[str, Any]]:
    if metric not in ALLOWED_METRICS:
        raise ValueError(f"metric must be one of {sorted(ALLOWED_METRICS)}")
    if dimension not in ALLOWED_DIMENSIONS:
        raise ValueError(f"dimension must be one of {sorted(ALLOWED_DIMENSIONS)}")
    totals: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        key = row[dimension] if dimension != "month" else row["date"][:7]
        totals[key] += float(row[metric])
    return [{dimension: key, metric: round(value, 2)} for key, value in sorted(totals.items())]


def detect_anomalies(rows: list[dict[str, str]], metric: str = "revenue", threshold: float = 2.5) -> list[dict[str, Any]]:
    if metric not in ALLOWED_METRICS:
        raise ValueError(f"metric must be one of {sorted(ALLOWED_METRICS)}")
    values = [float(row[metric]) for row in rows]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    standard_deviation = math.sqrt(variance)
    if not standard_deviation:
        return []
    findings = []
    for row, value in zip(rows, values, strict=True):
        z_score = (value - mean) / standard_deviation
        if abs(z_score) >= threshold:
            findings.append({"date": row["date"], "region": row["region"], metric: value, "z_score": round(z_score, 3)})
    findings.sort(key=lambda item: -abs(item["z_score"]))
    return findings


def validate_rows(rows: list[dict[str, str]]) -> None:
    for row in rows:
        datetime.fromisoformat(row["date"])
        float(row["orders"])
        float(row["revenue"])


class AnalyticsAgent:
    """Routes a question to one allowlisted read-only analytics tool."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        validate_rows(rows)
        self.rows = rows

    @staticmethod
    def guard(question: str) -> str | None:
        if not question.strip():
            return "question cannot be empty"
        if len(question) > 500:
            return "question exceeds the 500-character limit"
        tokens = set(re.findall(r"[a-z]+", question.lower()))
        blocked = sorted(tokens & BLOCKED_ACTIONS)
        if blocked:
            return f"blocked side-effect request: {', '.join(blocked)}"
        return None

    @staticmethod
    def plan(question: str) -> ToolCall:
        lowered = question.lower()
        if any(word in lowered for word in ("schema", "columns", "missing", "profile")):
            return ToolCall("profile_dataset", {})
        if any(word in lowered for word in ("anomaly", "anomalies", "unusual", "outlier")):
            metric = "orders" if "order" in lowered and "revenue" not in lowered else "revenue"
            return ToolCall("detect_anomalies", {"metric": metric, "threshold": 2.5})
        dimension = "month" if any(word in lowered for word in ("month", "monthly", "trend")) else "channel" if "channel" in lowered else "region"
        metric = "orders" if "order" in lowered and "revenue" not in lowered else "revenue"
        return ToolCall("aggregate_metric", {"metric": metric, "dimension": dimension})

    def run(self, question: str) -> AgentResult:
        trace: list[dict[str, Any]] = [{"step": "input", "question": question}]
        violation = self.guard(question)
        if violation:
            trace.append({"step": "guardrail", "decision": "blocked", "reason": violation})
            return AgentResult(question, "blocked", violation, None, None, tuple(trace))
        trace.append({"step": "guardrail", "decision": "allowed"})
        call = self.plan(question)
        trace.append({"step": "plan", "tool": call.name, "arguments": call.arguments})
        if call.name == "profile_dataset":
            data = profile_dataset(self.rows)
            answer = f"The dataset has {data['rows']} rows and {len(data['columns'])} columns."
        elif call.name == "detect_anomalies":
            data = detect_anomalies(self.rows, **call.arguments)
            answer = f"Found {len(data)} rows at or above the absolute z-score threshold."
        else:
            data = aggregate_metric(self.rows, **call.arguments)
            leader = max(data, key=lambda item: item[call.arguments["metric"]])
            answer = f"Calculated {call.arguments['metric']} by {call.arguments['dimension']}; the highest group is {next(iter(leader.values()))}."
        trace.append({"step": "tool_result", "records": len(data) if isinstance(data, list) else 1})
        trace.append({"step": "output", "status": "completed"})
        return AgentResult(question, "completed", answer, call, data, tuple(trace))
