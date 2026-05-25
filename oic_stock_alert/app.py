"""Application service layer for OIC Stock Alert."""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import Settings, load_settings
from .errors import StockAlertError
from .evaluator import build_decision, evaluate_rules
from .mapper import build_error_response, build_success_response, now_ms
from .quote_provider import get_quote
from .validation import resolve_request_id, validate_request

MAX_BODY_BYTES = 64 * 1024


class StockAlertApp:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        logging.basicConfig(level=getattr(logging, self.settings.log_level.upper(), logging.INFO))
        self.logger = logging.getLogger("oic_stock_alert")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "oic-stock-alert",
            "version": "1.0.0",
            "providerMode": self.settings.quote_provider_mode,
            "timestamp": _utc_timestamp(),
        }

    def evaluate(self, payload: Any, header_request_id: str | None = None) -> tuple[int, dict[str, Any]]:
        started_ms = now_ms()
        request_id = resolve_request_id(payload if isinstance(payload, dict) else None, header_request_id)
        raw_symbol = payload.get("symbol") if isinstance(payload, dict) else None
        tracking_id = _tracking_id_from_payload(payload, request_id)

        try:
            request = validate_request(payload, header_request_id)
            quote = get_quote(
                request["symbol"],
                self.settings,
                requested_mode=request["options"].get("providerMode"),
            )
            evaluations = evaluate_rules(request["rules"], quote)
            decision = build_decision(request["symbol"], evaluations)
            response = build_success_response(request, quote, evaluations, decision, self.settings, started_ms)
            self._log_decision(request["requestId"], request["symbol"], decision["code"])
            return 200, response
        except StockAlertError as error:
            response = build_error_response(error, request_id, str(raw_symbol) if raw_symbol is not None else None, tracking_id)
            self._log_decision(request_id, str(raw_symbol) if raw_symbol is not None else "", error.decision_code, error.error_code)
            return error.status_code, response
        except Exception as exc:
            self.logger.exception("Unexpected error while evaluating alert")
            error = StockAlertError("Unexpected API failure", [{"field": "system", "issue": str(exc)}])
            return error.status_code, build_error_response(error, request_id, str(raw_symbol) if raw_symbol is not None else None, tracking_id)

    def _log_decision(self, request_id: str, symbol: str, decision_code: str, error_code: str | None = None) -> None:
        self.logger.info(
            "requestId=%s symbol=%s providerMode=%s decision=%s error=%s",
            request_id,
            symbol,
            self.settings.quote_provider_mode,
            decision_code,
            error_code or "",
        )


def parse_json_body(body: bytes) -> Any:
    if len(body) > MAX_BODY_BYTES:
        from .errors import ValidationError

        raise ValidationError("Request body too large", [{"field": "body", "issue": "Maximum size is 64 KB"}])
    try:
        return json.loads(body.decode("utf-8"))
    except UnicodeDecodeError:
        from .errors import ValidationError

        raise ValidationError("Request body must be UTF-8 JSON")
    except json.JSONDecodeError as exc:
        from .errors import ValidationError

        raise ValidationError("Invalid JSON body", [{"field": "body", "issue": exc.msg}])


def _tracking_id_from_payload(payload: Any, request_id: str) -> str:
    if isinstance(payload, dict):
        source = payload.get("source")
        if isinstance(source, dict) and source.get("instanceId"):
            return str(source["instanceId"])
    return request_id


def _utc_timestamp() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

