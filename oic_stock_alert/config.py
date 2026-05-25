"""Runtime configuration for the OIC Stock Alert API."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .env_loader import apply_env_defaults, load_env_file


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    port: int = 8080
    quote_provider_mode: str = "mock"
    quote_provider_name: str = "mock"
    quote_provider_api_key: str | None = None
    quote_provider_timeout_ms: int = 1500
    allow_request_provider_override: bool = False
    log_level: str = "info"


def load_settings() -> Settings:
    apply_env_defaults(load_env_file())
    return Settings(
        port=_env_int("PORT", 8080),
        quote_provider_mode=os.getenv("QUOTE_PROVIDER_MODE", "mock").strip().lower(),
        quote_provider_name=os.getenv("QUOTE_PROVIDER_NAME", "mock").strip() or "mock",
        quote_provider_api_key=os.getenv("QUOTE_PROVIDER_API_KEY"),
        quote_provider_timeout_ms=_env_int("QUOTE_PROVIDER_TIMEOUT_MS", 1500),
        allow_request_provider_override=_env_bool("ALLOW_REQUEST_PROVIDER_OVERRIDE", False),
        log_level=os.getenv("LOG_LEVEL", "info").strip().lower(),
    )
