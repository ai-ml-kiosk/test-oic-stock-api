"""Alpha Vantage GLOBAL_QUOTE provider."""

from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Settings
from .errors import ProviderError, ProviderTimeoutError, QuoteNotFoundError

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
PROVIDER_NAME = "alpha_vantage"


def get_alpha_vantage_quote(symbol: str, settings: Settings) -> dict[str, Any]:
    if not settings.quote_provider_api_key:
        raise ProviderError("Alpha Vantage API key is not configured")

    payload = _fetch_global_quote(symbol, settings)
    return normalize_global_quote(payload)


def normalize_global_quote(payload: dict[str, Any]) -> dict[str, Any]:
    if "Note" in payload:
        raise ProviderError("Alpha Vantage rate limit response")
    if "Information" in payload:
        raise ProviderError("Alpha Vantage provider information response")
    if "Error Message" in payload:
        raise QuoteNotFoundError("Alpha Vantage symbol was not found")

    global_quote = payload.get("Global Quote")
    if not isinstance(global_quote, dict) or not global_quote:
        raise QuoteNotFoundError("Alpha Vantage quote was unavailable")

    try:
        symbol = str(global_quote["01. symbol"]).strip().upper()
        return {
            "symbol": symbol,
            "lastPrice": _decimal(global_quote["05. price"]),
            "currency": "USD",
            "change": _decimal(global_quote["09. change"]),
            "changePercent": _percent(global_quote["10. change percent"]),
            "dayHigh": _decimal(global_quote["03. high"]),
            "dayLow": _decimal(global_quote["04. low"]),
            "volume": int(str(global_quote["06. volume"]).strip()),
            "asOf": _as_of(global_quote["07. latest trading day"]),
            "provider": PROVIDER_NAME,
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError("Alpha Vantage quote payload was malformed") from exc


def _fetch_global_quote(symbol: str, settings: Settings) -> dict[str, Any]:
    query = urlencode(
        {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": settings.quote_provider_api_key,
        }
    )
    request = Request(f"{ALPHA_VANTAGE_URL}?{query}", headers={"User-Agent": "oic-stock-alert/1.0"})
    timeout_seconds = max(settings.quote_provider_timeout_ms, 1) / 1000

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except TimeoutError as exc:
        raise ProviderTimeoutError("Alpha Vantage provider timed out") from exc
    except socket.timeout as exc:
        raise ProviderTimeoutError("Alpha Vantage provider timed out") from exc
    except HTTPError as exc:
        raise ProviderError(f"Alpha Vantage provider returned HTTP {exc.code}") from exc
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise ProviderTimeoutError("Alpha Vantage provider timed out") from exc
        raise ProviderError("Alpha Vantage provider connection failed") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProviderError("Alpha Vantage provider returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ProviderError("Alpha Vantage provider returned unexpected JSON")
    return payload


def _decimal(value: Any) -> float:
    return float(str(value).strip())


def _percent(value: Any) -> float:
    return float(str(value).strip().rstrip("%"))


def _as_of(value: Any) -> str:
    raw = str(value).strip()
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC)
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        return raw
