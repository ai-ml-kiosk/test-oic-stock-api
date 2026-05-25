"""Response and error mapping for OIC-friendly contracts."""

from __future__ import annotations

import time
from typing import Any

from .config import Settings
from .errors import StockAlertError


def now_ms() -> int:
    return int(time.perf_counter() * 1000)


def build_success_response(
    request: dict[str, Any],
    quote: dict[str, Any],
    evaluations: list[dict[str, Any]],
    decision: dict[str, Any],
    settings: Settings,
    started_ms: int,
) -> dict[str, Any]:
    triggered_count = len([rule for rule in evaluations if rule["triggered"]])
    response = {
        "requestId": request["requestId"],
        "status": "success",
        "symbol": request["symbol"],
        "quote": quote,
        "rules": evaluations,
        "decision": decision,
        "oic": {
            "switchBranch": decision["code"],
            "notificationRecommended": decision["code"] == "ALERT_TRIGGERED",
            "retryRecommended": False,
            "trackingId": _tracking_id(request),
        },
    }
    if request["options"].get("includeDiagnostics"):
        response["diagnostics"] = {
            "providerMode": settings.quote_provider_mode,
            "elapsedMs": max(now_ms() - started_ms, 0),
            "ruleCount": len(evaluations),
            "triggeredCount": triggered_count,
        }
    return response


def build_error_response(
    error: StockAlertError,
    request_id: str,
    symbol: str | None = None,
    tracking_id: str | None = None,
) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "status": "error",
        "symbol": symbol,
        "error": {
            "code": error.error_code,
            "message": error.message,
            "details": error.details,
        },
        "decision": {
            "triggered": False,
            "code": error.decision_code,
            "severity": error.severity,
            "message": _decision_message(error.decision_code),
        },
        "oic": {
            "switchBranch": error.switch_branch,
            "notificationRecommended": False,
            "retryRecommended": error.retry_recommended,
            "trackingId": tracking_id or request_id,
        },
    }


def _tracking_id(request: dict[str, Any]) -> str:
    return request.get("source", {}).get("instanceId") or request["requestId"]


def _decision_message(decision_code: str) -> str:
    messages = {
        "INPUT_ERROR": "Input could not be evaluated",
        "QUOTE_UNAVAILABLE": "Quote data was unavailable",
        "PROVIDER_TIMEOUT": "Quote provider timed out",
        "SYSTEM_ERROR": "System error occurred",
    }
    return messages.get(decision_code, "Request could not be evaluated")

