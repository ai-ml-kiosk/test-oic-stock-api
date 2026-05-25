"""Request normalization and validation."""

from __future__ import annotations

import math
import re
import uuid
from typing import Any

from .errors import UnsupportedRuleError, ValidationError

SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.:-]{0,14}$")
ALLOWED_METRICS = {"lastPrice", "changePercent", "dayHigh", "dayLow", "volume"}
ALLOWED_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "absGte"}
ALLOWED_SEVERITIES = {"info", "warning", "high", "critical"}
MAX_RULES = 10
MAX_REQUEST_ID_LENGTH = 80
MAX_RULE_ID_LENGTH = 80
MAX_MESSAGE_LENGTH = 240
MAX_INTEGRATION_NAME_LENGTH = 120


def resolve_request_id(payload: dict[str, Any] | None, header_request_id: str | None) -> str:
    body_request_id = payload.get("requestId") if isinstance(payload, dict) else None
    request_id = body_request_id or header_request_id or str(uuid.uuid4())
    return str(request_id)[:MAX_REQUEST_ID_LENGTH]


def validate_request(payload: Any, header_request_id: str | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    request_id = resolve_request_id(payload, header_request_id)
    details: list[dict[str, str]] = []

    source = payload.get("source") or {}
    if not isinstance(source, dict):
        details.append({"field": "source", "issue": "source must be an object"})
        source = {}

    integration_name = source.get("integrationName")
    if integration_name is not None and len(str(integration_name)) > MAX_INTEGRATION_NAME_LENGTH:
        details.append({"field": "source.integrationName", "issue": "integrationName is too long"})

    symbol = payload.get("symbol")
    normalized_symbol = str(symbol).strip().upper() if symbol is not None else ""
    if not normalized_symbol or not SYMBOL_PATTERN.match(normalized_symbol):
        details.append(
            {
                "field": "symbol",
                "issue": "Symbol must match pattern ^[A-Z][A-Z0-9.:-]{0,14}$",
            }
        )

    currency = payload.get("currency")
    normalized_currency = str(currency).strip().upper() if currency else None
    if normalized_currency is not None and not re.match(r"^[A-Z]{3}$", normalized_currency):
        details.append({"field": "currency", "issue": "currency must be a 3-letter code"})

    rules = payload.get("rules")
    normalized_rules = _validate_rules(rules, details)

    options = payload.get("options") or {}
    if not isinstance(options, dict):
        details.append({"field": "options", "issue": "options must be an object"})
        options = {}

    provider_mode = options.get("providerMode")
    if provider_mode is not None and str(provider_mode).lower() not in {"mock", "live"}:
        details.append({"field": "options.providerMode", "issue": "providerMode must be mock or live"})

    include_diagnostics = bool(options.get("includeDiagnostics", False))

    if details:
        raise ValidationError("Request validation failed", details)

    return {
        "requestId": request_id,
        "source": {
            "system": source.get("system"),
            "integrationName": source.get("integrationName"),
            "instanceId": source.get("instanceId"),
        },
        "symbol": normalized_symbol,
        "currency": normalized_currency,
        "rules": normalized_rules,
        "options": {
            "providerMode": str(provider_mode).lower() if provider_mode else None,
            "includeDiagnostics": include_diagnostics,
        },
    }


def _validate_rules(rules: Any, details: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not isinstance(rules, list) or not rules:
        details.append({"field": "rules", "issue": "rules must contain 1 to 10 items"})
        return []
    if len(rules) > MAX_RULES:
        details.append({"field": "rules", "issue": "rules must not contain more than 10 items"})
        return []

    seen_rule_ids: set[str] = set()
    normalized_rules = []
    for index, raw_rule in enumerate(rules):
        field_prefix = f"rules[{index}]"
        if not isinstance(raw_rule, dict):
            details.append({"field": field_prefix, "issue": "rule must be an object"})
            continue

        rule_id = str(raw_rule.get("ruleId", "")).strip()
        if not rule_id or len(rule_id) > MAX_RULE_ID_LENGTH:
            details.append({"field": f"{field_prefix}.ruleId", "issue": "ruleId is required and max 80 characters"})
        elif rule_id in seen_rule_ids:
            details.append({"field": f"{field_prefix}.ruleId", "issue": "ruleId values must be unique"})
        seen_rule_ids.add(rule_id)

        metric = raw_rule.get("metric")
        operator = raw_rule.get("operator")
        if metric not in ALLOWED_METRICS:
            raise UnsupportedRuleError("Unsupported rule metric", [{"field": f"{field_prefix}.metric", "issue": "Unsupported metric"}])
        if operator not in ALLOWED_OPERATORS:
            raise UnsupportedRuleError(
                "Unsupported rule operator",
                [{"field": f"{field_prefix}.operator", "issue": "Unsupported operator"}],
            )

        threshold = raw_rule.get("threshold")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not math.isfinite(threshold):
            details.append({"field": f"{field_prefix}.threshold", "issue": "threshold must be a finite number"})
        elif metric != "changePercent" and threshold < 0:
            details.append({"field": f"{field_prefix}.threshold", "issue": "threshold must be >= 0"})

        severity = raw_rule.get("severity", "warning")
        if severity not in ALLOWED_SEVERITIES:
            details.append({"field": f"{field_prefix}.severity", "issue": "severity is invalid"})

        message = raw_rule.get("message")
        if message is not None and len(str(message)) > MAX_MESSAGE_LENGTH:
            details.append({"field": f"{field_prefix}.message", "issue": "message is too long"})

        normalized_rules.append(
            {
                "ruleId": rule_id,
                "metric": metric,
                "operator": operator,
                "threshold": float(threshold) if isinstance(threshold, (int, float)) and not isinstance(threshold, bool) else threshold,
                "severity": severity,
                "message": str(message) if message is not None else "",
            }
        )

    return normalized_rules

