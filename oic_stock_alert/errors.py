"""Application-specific errors and OIC branch metadata."""

from __future__ import annotations


class StockAlertError(Exception):
    status_code = 500
    error_code = "SYSTEM_ERROR"
    decision_code = "SYSTEM_ERROR"
    switch_branch = "SYSTEM_ERROR"
    severity = "critical"
    retry_recommended = True

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationError(StockAlertError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    decision_code = "INPUT_ERROR"
    switch_branch = "INPUT_ERROR"
    severity = "warning"
    retry_recommended = False


class UnsupportedRuleError(ValidationError):
    status_code = 422
    error_code = "UNSUPPORTED_RULE"


class QuoteNotFoundError(StockAlertError):
    status_code = 502
    error_code = "QUOTE_NOT_FOUND"
    decision_code = "QUOTE_UNAVAILABLE"
    switch_branch = "QUOTE_UNAVAILABLE"
    severity = "warning"
    retry_recommended = False


class ProviderError(StockAlertError):
    status_code = 502
    error_code = "PROVIDER_ERROR"
    decision_code = "QUOTE_UNAVAILABLE"
    switch_branch = "QUOTE_UNAVAILABLE"
    severity = "warning"
    retry_recommended = False


class ProviderTimeoutError(StockAlertError):
    status_code = 504
    error_code = "PROVIDER_TIMEOUT"
    decision_code = "PROVIDER_TIMEOUT"
    switch_branch = "PROVIDER_TIMEOUT"
    severity = "warning"
    retry_recommended = True

