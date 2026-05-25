"""Alert rule evaluation and aggregate decision logic."""

from __future__ import annotations

from typing import Any

from .errors import ProviderError

SEVERITY_ORDER = {"info": 0, "warning": 1, "high": 2, "critical": 3}


def evaluate_rules(rules: list[dict[str, Any]], quote: dict[str, Any]) -> list[dict[str, Any]]:
    evaluations = []
    for rule in rules:
        metric = rule["metric"]
        if metric not in quote:
            raise ProviderError(f"Quote did not include required metric: {metric}")
        actual_value = quote[metric]
        triggered = _evaluate_operator(float(actual_value), rule["operator"], float(rule["threshold"]))
        evaluations.append(
            {
                "ruleId": rule["ruleId"],
                "metric": metric,
                "operator": rule["operator"],
                "threshold": rule["threshold"],
                "actualValue": actual_value,
                "triggered": triggered,
                "severity": rule.get("severity", "warning"),
                "message": rule.get("message", ""),
            }
        )
    return evaluations


def build_decision(symbol: str, evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    triggered_rules = [rule for rule in evaluations if rule["triggered"]]
    if not triggered_rules:
        return {
            "triggered": False,
            "code": "NO_ALERT",
            "severity": "info",
            "message": f"No alert rules triggered for {symbol}",
        }

    highest = max(triggered_rules, key=lambda rule: SEVERITY_ORDER[rule["severity"]])
    count = len(triggered_rules)
    noun = "rule" if count == 1 else "rules"
    return {
        "triggered": True,
        "code": "ALERT_TRIGGERED",
        "severity": highest["severity"],
        "message": f"{count} alert {noun} triggered for {symbol}",
    }


def _evaluate_operator(actual_value: float, operator: str, threshold: float) -> bool:
    if operator == "gt":
        return actual_value > threshold
    if operator == "gte":
        return actual_value >= threshold
    if operator == "lt":
        return actual_value < threshold
    if operator == "lte":
        return actual_value <= threshold
    if operator == "eq":
        return actual_value == threshold
    if operator == "absGte":
        return abs(actual_value) >= threshold
    raise ValueError(f"Unsupported operator: {operator}")

