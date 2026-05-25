"""Quote provider abstraction with a deterministic mock provider."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .errors import ProviderError, ProviderTimeoutError, QuoteNotFoundError


def get_quote(symbol: str, settings: Settings, requested_mode: str | None = None) -> dict[str, Any]:
    mode = settings.quote_provider_mode
    if settings.allow_request_provider_override and requested_mode:
        mode = requested_mode

    if mode == "mock":
        return _mock_quote(symbol)
    if mode == "live":
        raise ProviderError("Live quote provider is not configured for this MVP")
    raise ProviderError(f"Unsupported quote provider mode: {mode}")


def _mock_quote(symbol: str) -> dict[str, Any]:
    if symbol == "MISSING":
        raise QuoteNotFoundError("No quote found for symbol", [{"field": "symbol", "issue": "Quote not found"}])
    if symbol == "TIMEOUT":
        raise ProviderTimeoutError("Quote provider timed out")
    if symbol == "ERROR":
        raise ProviderError("Quote provider returned an error")

    fixtures = {
        "ORCL": {
            "lastPrice": 152.31,
            "change": 2.14,
            "changePercent": 1.43,
            "dayHigh": 153.2,
            "dayLow": 149.7,
            "volume": 12654321,
        },
        "AAPL": {
            "lastPrice": 185.64,
            "change": -1.06,
            "changePercent": -0.57,
            "dayHigh": 188.04,
            "dayLow": 184.81,
            "volume": 55123000,
        },
    }
    quote = fixtures.get(
        symbol,
        {
            "lastPrice": 100.0,
            "change": 0.0,
            "changePercent": 0.0,
            "dayHigh": 101.0,
            "dayLow": 99.0,
            "volume": 1000000,
        },
    )
    return {
        "symbol": symbol,
        "currency": "USD",
        "asOf": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "provider": "mock",
        **quote,
    }

