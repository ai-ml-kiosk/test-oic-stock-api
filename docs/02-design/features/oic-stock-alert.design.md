# oic-stock-alert - Design Document

> Version: 1.1.0 | Date: 2026-05-26 | Status: Complete
> Level: Starter | Plan: `docs/01-plan/features/oic-stock-alert.plan.md`

---

## 1. Overview

The OIC Stock Alert application is a stateless HTTP API designed to be called from Oracle Integration Cloud (OIC). It accepts a stock alert evaluation request, retrieves quote data from a configured quote provider, evaluates one or more alert rules, and returns a stable JSON payload that OIC can map into Switch branches and downstream notification actions.

Repository: `https://github.com/ai-ml-kiosk/test-oic-stock-api`

Derived design artifacts:

- HLD: `docs/02-design/features/oic-stock-alert.hld.md` and `design/oic-stock-alert-hld.pdf`
- LLD: `docs/02-design/features/oic-stock-alert.lld.md` and `design/oic-stock-alert-lld.pdf`

The MVP keeps the service intentionally small:

- A health endpoint for runtime validation.
- A single alert evaluation endpoint for OIC orchestration.
- A quote provider abstraction with mock mode as the default local path.
- A live Alpha Vantage provider path for `GLOBAL_QUOTE` orchestration when explicitly enabled.
- A zero-trust local `.env` configuration layer for API keys, with committed `.env.example` placeholders only.
- Deterministic JSON contracts for success, no-alert, input error, and provider failure outcomes.
- Branch-friendly fields such as `decision.code`, `decision.triggered`, `decision.severity`, and `oic.switchBranch`.

## 2. Architecture

### 2.1 Runtime Components

| Component | Responsibility |
|-----------|----------------|
| API Router | Defines HTTP endpoints, parses JSON, invokes validation and service logic. |
| Request Validator | Validates required fields, stock symbol format, rule operators, thresholds, and callback metadata. |
| Quote Provider | Fetches current quote data. Uses `mock` mode locally and Alpha Vantage `GLOBAL_QUOTE` when `live` mode is explicitly configured. |
| Alert Evaluator | Compares normalized quote values against alert rules and produces rule-level outcomes. |
| Response Mapper | Builds OIC-friendly response JSON with stable decision and switch branch fields. |
| Error Mapper | Converts validation, provider, timeout, and unexpected errors into predictable error responses. |
| `.env` Config Loader | Parses local untracked `.env` values into runtime settings without exposing secrets to Git, logs, diagnostics, or responses. |
| Logger | Emits request ID, symbol, provider mode, elapsed time, decision code, and error code without secrets or full provider URLs. |

### 2.2 Request Flow

1. OIC invokes `POST /v1/alerts/evaluate` with a stock symbol, rule set, and optional OIC metadata.
2. API assigns or propagates `requestId`.
3. Validator checks JSON shape and field-level constraints.
4. Quote Provider retrieves normalized quote data from mock fixtures or Alpha Vantage `GLOBAL_QUOTE`.
5. Alert Evaluator evaluates every rule against the quote.
6. Response Mapper derives the aggregate decision and OIC Switch branch.
7. API returns HTTP status and JSON response to OIC.

### 2.3 Implementation Stack

The MVP is implemented as a dependency-free Python standard-library HTTP API. This keeps the first GitHub version easy to run in a clean environment and avoids package installation for OIC contract testing.

Runtime stack:

- Python 3.11 or newer.
- `http.server.ThreadingHTTPServer` for local API serving.
- `unittest` for evaluator and HTTP contract tests.
- No third-party runtime dependencies.

Module layout:

| Module | Purpose |
|--------|---------|
| `oic_stock_alert/config.py` | Environment-based runtime settings. |
| `oic_stock_alert/env_loader.py` | Local `.env` parser for development secrets and provider settings. |
| `oic_stock_alert/validation.py` | Request normalization and validation. |
| `oic_stock_alert/quote_provider.py` | Provider selection, mock quote provider, and shared provider errors. |
| `oic_stock_alert/alpha_vantage_provider.py` | Alpha Vantage `GLOBAL_QUOTE` outbound REST client and response normalizer. |
| `oic_stock_alert/evaluator.py` | Rule evaluation and aggregate decision logic. |
| `oic_stock_alert/mapper.py` | Success and error response mapping. |
| `oic_stock_alert/app.py` | Application service layer. |
| `oic_stock_alert/server.py` | HTTP route handling and server entry point. |

### 2.4 Alpha Vantage Live Provider Architecture

The live provider path is enabled only when runtime configuration selects live mode:

```text
QUOTE_PROVIDER_MODE=live
QUOTE_PROVIDER_NAME=alpha_vantage
QUOTE_PROVIDER_API_KEY=<local secret>
QUOTE_PROVIDER_TIMEOUT_MS=1500
```

Outbound request shape:

```text
GET https://www.alphavantage.co/query
  ?function=GLOBAL_QUOTE
  &symbol={normalizedSymbol}
  &apikey={secretApiKey}
```

Optional request parameters:

| Parameter | Design |
|-----------|--------|
| `datatype` | Omitted for MVP so Alpha Vantage returns JSON by default. |
| `entitlement` | Omitted for MVP; realtime or 15-minute delayed freshness requires the appropriate Alpha Vantage entitlement. |

Provider design rules:

- Never log the full provider URL because it contains the API key.
- Apply `QUOTE_PROVIDER_TIMEOUT_MS` to the outbound request, defaulting to 1500 ms.
- Parse provider responses into the existing internal `Quote` shape before rule evaluation.
- Preserve the existing OIC response contract and Switch branch values.
- Map Alpha Vantage empty quote, rate-limit note, invalid-key information, timeout, and malformed payloads into stable downstream OIC exception branches.

Official reference: `https://www.alphavantage.co/documentation/`

## 3. API Specification

### 3.1 Health Check

`GET /health`

Success response:

```json
{
  "status": "ok",
  "service": "oic-stock-alert",
  "version": "1.0.0",
  "providerMode": "mock",
  "timestamp": "2026-05-25T05:30:00Z"
}
```

### 3.2 Alert Evaluation

`POST /v1/alerts/evaluate`

Headers:

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type: application/json` | Yes | Request body format. |
| `X-Request-Id` | No | OIC or caller-provided correlation ID. |

Success HTTP status:

- `200 OK` when the request is valid and quote evaluation completes, whether or not an alert is triggered.

Error HTTP status:

- `400 Bad Request` for invalid JSON or validation errors.
- `422 Unprocessable Entity` for valid JSON with unsupported rule configuration.
- `502 Bad Gateway` for quote provider errors.
- `504 Gateway Timeout` for quote provider timeout.
- `500 Internal Server Error` for unexpected API failures.

## 4. JSON Payload Contracts

### 4.1 Evaluation Request

```json
{
  "requestId": "oic-run-20260525-001",
  "source": {
    "system": "OIC",
    "integrationName": "StockAlertIntegration",
    "instanceId": "300000123456789"
  },
  "symbol": "ORCL",
  "currency": "USD",
  "rules": [
    {
      "ruleId": "orcl-above-150",
      "metric": "lastPrice",
      "operator": "gte",
      "threshold": 150.0,
      "severity": "high",
      "message": "ORCL crossed target price"
    }
  ],
  "options": {
    "providerMode": "mock",
    "includeDiagnostics": true
  }
}
```

### 4.2 Request Field Rules

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `requestId` | string | No | If missing, API generates one. Max 80 characters. |
| `source.system` | string | No | Expected value `OIC` for OIC calls. |
| `source.integrationName` | string | No | Max 120 characters. |
| `source.instanceId` | string | No | OIC tracking identifier. |
| `symbol` | string | Yes | Uppercase after normalization. Allowed pattern `^[A-Z][A-Z0-9.:-]{0,14}$`. |
| `currency` | string | No | ISO-style 3-letter code. Defaults to provider quote currency or `USD`. |
| `rules` | array | Yes | 1 to 10 rules. |
| `rules[].ruleId` | string | Yes | Unique within request. Max 80 characters. |
| `rules[].metric` | string | Yes | `lastPrice`, `changePercent`, `dayHigh`, `dayLow`, or `volume`. |
| `rules[].operator` | string | Yes | `gt`, `gte`, `lt`, `lte`, `eq`, `absGte`. |
| `rules[].threshold` | number | Yes | Finite numeric value. Must be `>= 0` except `changePercent`, which may be negative. |
| `rules[].severity` | string | No | `info`, `warning`, `high`, or `critical`. Defaults to `warning`. |
| `rules[].message` | string | No | OIC notification-friendly text. Max 240 characters. |
| `options.providerMode` | string | No | `mock`, `live`, or omitted. Runtime default controls omitted value. |
| `options.includeDiagnostics` | boolean | No | Defaults to `false`. |

### 4.3 Evaluation Success Response

```json
{
  "requestId": "oic-run-20260525-001",
  "status": "success",
  "symbol": "ORCL",
  "quote": {
    "symbol": "ORCL",
    "lastPrice": 152.31,
    "currency": "USD",
    "change": 2.14,
    "changePercent": 1.43,
    "dayHigh": 153.2,
    "dayLow": 149.7,
    "volume": 12654321,
    "asOf": "2026-05-25T05:30:00Z",
    "provider": "mock"
  },
  "rules": [
    {
      "ruleId": "orcl-above-150",
      "metric": "lastPrice",
      "operator": "gte",
      "threshold": 150.0,
      "actualValue": 152.31,
      "triggered": true,
      "severity": "high",
      "message": "ORCL crossed target price"
    }
  ],
  "decision": {
    "triggered": true,
    "code": "ALERT_TRIGGERED",
    "severity": "high",
    "message": "1 alert rule triggered for ORCL"
  },
  "oic": {
    "switchBranch": "ALERT_TRIGGERED",
    "notificationRecommended": true,
    "retryRecommended": false,
    "trackingId": "300000123456789"
  },
  "diagnostics": {
    "providerMode": "mock",
    "elapsedMs": 48,
    "ruleCount": 1,
    "triggeredCount": 1
  }
}
```

### 4.4 No-Alert Success Response

```json
{
  "requestId": "oic-run-20260525-002",
  "status": "success",
  "symbol": "ORCL",
  "quote": {
    "symbol": "ORCL",
    "lastPrice": 145.25,
    "currency": "USD",
    "change": -0.75,
    "changePercent": -0.51,
    "dayHigh": 146.1,
    "dayLow": 143.9,
    "volume": 10200111,
    "asOf": "2026-05-25T05:35:00Z",
    "provider": "mock"
  },
  "rules": [
    {
      "ruleId": "orcl-above-150",
      "metric": "lastPrice",
      "operator": "gte",
      "threshold": 150.0,
      "actualValue": 145.25,
      "triggered": false,
      "severity": "high",
      "message": "ORCL crossed target price"
    }
  ],
  "decision": {
    "triggered": false,
    "code": "NO_ALERT",
    "severity": "info",
    "message": "No alert rules triggered for ORCL"
  },
  "oic": {
    "switchBranch": "NO_ALERT",
    "notificationRecommended": false,
    "retryRecommended": false,
    "trackingId": "300000123456790"
  }
}
```

### 4.5 Error Response

```json
{
  "requestId": "oic-run-20260525-003",
  "status": "error",
  "symbol": "BAD SYMBOL",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "symbol",
        "issue": "Symbol must match pattern ^[A-Z][A-Z0-9.:-]{0,14}$"
      }
    ]
  },
  "decision": {
    "triggered": false,
    "code": "INPUT_ERROR",
    "severity": "warning",
    "message": "Input could not be evaluated"
  },
  "oic": {
    "switchBranch": "INPUT_ERROR",
    "notificationRecommended": false,
    "retryRecommended": false,
    "trackingId": "300000123456791"
  }
}
```

## 5. Data Model

### 5.1 Domain Types

| Type | Fields |
|------|--------|
| `AlertEvaluationRequest` | `requestId`, `source`, `symbol`, `currency`, `rules`, `options` |
| `AlertRule` | `ruleId`, `metric`, `operator`, `threshold`, `severity`, `message` |
| `Quote` | `symbol`, `lastPrice`, `currency`, `change`, `changePercent`, `dayHigh`, `dayLow`, `volume`, `asOf`, `provider` |
| `RuleEvaluation` | `ruleId`, `metric`, `operator`, `threshold`, `actualValue`, `triggered`, `severity`, `message` |
| `Decision` | `triggered`, `code`, `severity`, `message` |
| `OicRouting` | `switchBranch`, `notificationRecommended`, `retryRecommended`, `trackingId` |
| `ApiError` | `code`, `message`, `details` |

### 5.3 Alpha Vantage Normalized Quote

The Alpha Vantage `Global Quote` object is string-valued and must be normalized before evaluation.

| Alpha Vantage Field | Internal Quote Field | Conversion |
|---------------------|----------------------|------------|
| `01. symbol` | `symbol` | String, uppercased by prior validation. |
| `03. high` | `dayHigh` | Decimal string to number. |
| `04. low` | `dayLow` | Decimal string to number. |
| `05. price` | `lastPrice` | Decimal string to number. |
| `06. volume` | `volume` | Integer string to integer. |
| `07. latest trading day` | `asOf` | Date string converted to an ISO-style timestamp or date-preserving UTC value. |
| `09. change` | `change` | Decimal string to number. |
| `10. change percent` | `changePercent` | Percent string without `%` converted to number. |
| constant | `currency` | `USD` for MVP equity quotes unless a future provider supplies currency. |
| constant | `provider` | `alpha_vantage`. |

### 5.2 Enumerations

Decision codes:

- `ALERT_TRIGGERED`
- `NO_ALERT`
- `INPUT_ERROR`
- `QUOTE_UNAVAILABLE`
- `PROVIDER_TIMEOUT`
- `SYSTEM_ERROR`

Switch branches:

- `ALERT_TRIGGERED`
- `NO_ALERT`
- `INPUT_ERROR`
- `QUOTE_UNAVAILABLE`
- `PROVIDER_TIMEOUT`
- `SYSTEM_ERROR`

Severities:

- `info`
- `warning`
- `high`
- `critical`

## 6. Mapping Logic

### 6.1 Request Normalization

| Source Field | Target Field | Logic |
|--------------|--------------|-------|
| Header `X-Request-Id` | `requestId` | Use request body value first, then header, then generated UUID. |
| `symbol` | `symbol` | Trim, uppercase, validate against allowed pattern. |
| `currency` | `currency` | Uppercase if present. If absent, use quote provider currency. |
| `source.instanceId` | `oic.trackingId` | Copy when present; otherwise use `requestId`. |
| `options.providerMode` | provider mode | Use request value only if runtime allows override; otherwise use environment default. |

### 6.1.1 `.env` Configuration Normalization

Local configuration may be loaded from an untracked `.env` file before settings are finalized.

Parsing rules:

- Accept `KEY=value` lines with optional surrounding whitespace.
- Ignore blank lines and `#` comments.
- Do not evaluate shell expressions, command substitution, or nested variable expansion.
- Process environment variables take precedence over `.env` values when both exist.
- Never expose `QUOTE_PROVIDER_API_KEY` through diagnostics or error details.

Expected committed template:

```sh
QUOTE_PROVIDER_MODE=live
QUOTE_PROVIDER_NAME=alpha_vantage
QUOTE_PROVIDER_API_KEY=replace-with-local-alpha-vantage-key
QUOTE_PROVIDER_TIMEOUT_MS=1500
ALLOW_REQUEST_PROVIDER_OVERRIDE=false
```

### 6.2 Rule Evaluation

| Operator | Logic |
|----------|-------|
| `gt` | Trigger when `actualValue > threshold`. |
| `gte` | Trigger when `actualValue >= threshold`. |
| `lt` | Trigger when `actualValue < threshold`. |
| `lte` | Trigger when `actualValue <= threshold`. |
| `eq` | Trigger when `actualValue === threshold` after numeric normalization. |
| `absGte` | Trigger when `abs(actualValue) >= threshold`; intended for `changePercent`. |

Missing quote metrics produce an `INPUT_ERROR` if the metric is unsupported by design, or `QUOTE_UNAVAILABLE` if the metric should exist but provider did not return it.

### 6.3 Aggregate Decision Mapping

| Condition | `decision.code` | `decision.triggered` | `decision.severity` | `oic.switchBranch` | Retry |
|-----------|-----------------|----------------------|---------------------|--------------------|-------|
| At least one rule triggered | `ALERT_TRIGGERED` | `true` | Highest triggered severity | `ALERT_TRIGGERED` | `false` |
| No rules triggered | `NO_ALERT` | `false` | `info` | `NO_ALERT` | `false` |
| Validation failure | `INPUT_ERROR` | `false` | `warning` | `INPUT_ERROR` | `false` |
| Provider returns not found/no quote | `QUOTE_UNAVAILABLE` | `false` | `warning` | `QUOTE_UNAVAILABLE` | `false` |
| Provider timeout | `PROVIDER_TIMEOUT` | `false` | `warning` | `PROVIDER_TIMEOUT` | `true` |
| Unexpected API exception | `SYSTEM_ERROR` | `false` | `critical` | `SYSTEM_ERROR` | `true` |

Severity order:

`critical > high > warning > info`

### 6.4 Notification Mapping

| Decision Code | `notificationRecommended` | Suggested OIC Action |
|---------------|---------------------------|----------------------|
| `ALERT_TRIGGERED` | `true` | Send notification using rule message and quote details. |
| `NO_ALERT` | `false` | End integration successfully or log no-op. |
| `INPUT_ERROR` | `false` | Route to input validation handling. |
| `QUOTE_UNAVAILABLE` | `false` | Route to business exception handling or monitoring. |
| `PROVIDER_TIMEOUT` | `false` | Retry or route to recoverable fault handling. |
| `SYSTEM_ERROR` | `false` | Route to technical fault handling and incident logging. |

### 6.5 Alpha Vantage Error Mapping

| Upstream Condition | Detection | API Error | Switch Branch | Retry |
|--------------------|-----------|-----------|---------------|-------|
| Empty `Global Quote` object | Missing or empty quote object | `QUOTE_NOT_FOUND` | `QUOTE_UNAVAILABLE` | No |
| Invalid symbol payload | Empty quote for validated symbol | `QUOTE_NOT_FOUND` | `QUOTE_UNAVAILABLE` | No |
| Rate limit note | Provider response includes `Note` | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | Maybe by OIC policy |
| Invalid API key / entitlement message | Provider response includes `Information` or similar provider message | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | No |
| Timeout | Outbound request exceeds `QUOTE_PROVIDER_TIMEOUT_MS` | `PROVIDER_TIMEOUT` | `PROVIDER_TIMEOUT` | Yes |
| Non-JSON or malformed payload | JSON parse or expected-field failure | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | Maybe by OIC policy |
| Unexpected client exception | Unhandled provider client error | `SYSTEM_ERROR` | `SYSTEM_ERROR` | Yes |

## 7. OIC Switch Branch Structure

### 7.1 Switch Expression

OIC should branch on the response field:

```text
response.oic.switchBranch
```

If the OIC mapper has trouble with nested fields, map `response.oic.switchBranch` into a top-level OIC variable named `stockAlertSwitchBranch` immediately after the REST invoke.

### 7.2 Branches

| Branch Name | Match Value | Purpose |
|-------------|-------------|---------|
| Alert Triggered | `ALERT_TRIGGERED` | Build and send alert notification. |
| No Alert | `NO_ALERT` | Log evaluation result and end normally. |
| Input Error | `INPUT_ERROR` | Record validation issue and optionally notify integration owner. |
| Quote Unavailable | `QUOTE_UNAVAILABLE` | Record business exception for missing market data. |
| Provider Timeout | `PROVIDER_TIMEOUT` | Retry path or invoke OIC fault handling. |
| System Error | `SYSTEM_ERROR` | Raise technical fault and route to operations. |
| Otherwise | Any unmatched value | Treat as technical fault; include raw response for diagnostics. |

### 7.3 Alert Triggered Branch

Switch condition:

```text
stockAlertSwitchBranch = "ALERT_TRIGGERED"
```

Mapping into notification payload:

| Notification Field | Source |
|--------------------|--------|
| `subject` | `concat(response.symbol, " stock alert: ", response.decision.severity)` |
| `body` | `response.decision.message` plus triggered rule messages and quote values |
| `symbol` | `response.symbol` |
| `price` | `response.quote.lastPrice` |
| `currency` | `response.quote.currency` |
| `triggeredRules` | Filter `response.rules` where `triggered = true` |
| `trackingId` | `response.oic.trackingId` |
| `requestId` | `response.requestId` |

### 7.4 No Alert Branch

Switch condition:

```text
stockAlertSwitchBranch = "NO_ALERT"
```

Behavior:

- Record an OIC activity log entry with symbol, last price, rule count, and request ID.
- Do not send a user notification.
- End integration successfully.

### 7.5 Input Error Branch

Switch condition:

```text
stockAlertSwitchBranch = "INPUT_ERROR"
```

Behavior:

- Map `response.error.details` to an integration error log payload.
- Do not retry automatically.
- Optionally notify the integration owner if repeated input errors occur upstream.

### 7.6 Quote Unavailable Branch

Switch condition:

```text
stockAlertSwitchBranch = "QUOTE_UNAVAILABLE"
```

Behavior:

- Treat as a business exception.
- Log symbol, provider, and request ID.
- Do not retry unless the provider-specific error indicates temporary unavailability.

### 7.7 Provider Timeout Branch

Switch condition:

```text
stockAlertSwitchBranch = "PROVIDER_TIMEOUT"
```

Behavior:

- Use OIC retry handling if the integration pattern supports retry.
- Preserve request ID across retry attempts.
- If retries are exhausted, route to the same operations handling used for `SYSTEM_ERROR`.

### 7.8 System Error Branch

Switch condition:

```text
stockAlertSwitchBranch = "SYSTEM_ERROR"
```

Behavior:

- Treat as a technical fault.
- Include `requestId`, `error.code`, `error.message`, and OIC `instanceId` in operations logging.
- Avoid including provider credentials or raw secret-bearing configuration.

## 8. Error Contract

| Error Code | HTTP Status | Switch Branch | Retry Recommended | Description |
|------------|-------------|---------------|-------------------|-------------|
| `VALIDATION_ERROR` | 400 | `INPUT_ERROR` | No | Required fields missing or invalid. |
| `UNSUPPORTED_RULE` | 422 | `INPUT_ERROR` | No | Metric/operator combination is not supported. |
| `QUOTE_NOT_FOUND` | 502 | `QUOTE_UNAVAILABLE` | No | Provider cannot find a quote for the symbol. |
| `PROVIDER_ERROR` | 502 | `QUOTE_UNAVAILABLE` | Maybe | Provider returned a non-timeout error. |
| `PROVIDER_TIMEOUT` | 504 | `PROVIDER_TIMEOUT` | Yes | Provider did not respond within configured timeout. |
| `SYSTEM_ERROR` | 500 | `SYSTEM_ERROR` | Yes | Unexpected API exception. |

## 9. Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8080` | API listen port. |
| `QUOTE_PROVIDER_MODE` | No | `mock` | `mock` or `live`. |
| `QUOTE_PROVIDER_NAME` | No | `mock` | Provider identifier used in diagnostics. |
| `QUOTE_PROVIDER_API_KEY` | Live only | None | Secret for live quote provider. |
| `QUOTE_PROVIDER_TIMEOUT_MS` | No | `1500` | Outbound provider timeout. |
| `ALLOW_REQUEST_PROVIDER_OVERRIDE` | No | `false` | Allows `options.providerMode` to override runtime mode. |
| `LOG_LEVEL` | No | `info` | Runtime logging level. |

Local `.env` behavior:

- `.env` and `.env*` remain untracked.
- `.env.example` may be committed with placeholder values only.
- Runtime environment variables override `.env` values.
- Production runtimes should inject secrets through platform-managed environment variables or secret stores rather than committing local secret files.

## 10. Validation Rules

- Reject request bodies larger than the chosen framework default for small JSON requests, with a target maximum of 64 KB.
- Require `symbol` and at least one rule.
- Reject more than 10 rules per request for MVP simplicity.
- Reject duplicate `ruleId` values.
- Reject unknown metrics and operators.
- Reject missing or non-numeric thresholds.
- Validate severity and default missing severity to `warning`.
- Exclude `diagnostics` from responses unless `options.includeDiagnostics` is `true`.

## 11. Test Plan

### 11.1 Unit Tests

| Test | Expected Result |
|------|-----------------|
| `lastPrice gte threshold` with actual above threshold | Rule triggered. |
| `lastPrice lt threshold` with actual above threshold | Rule not triggered. |
| `changePercent absGte threshold` with negative actual beyond threshold | Rule triggered. |
| Multiple triggered rules with different severities | Aggregate severity is highest severity. |
| Duplicate `ruleId` values | Validation error. |
| Unsupported metric | `INPUT_ERROR`. |
| `.env` parser ignores comments and blank lines | Settings load without secret exposure. |
| Process environment overrides `.env` value | Runtime setting follows process environment. |
| Alpha Vantage quote normalization | Numeric quote fields are parsed into internal `Quote`. |
| Alpha Vantage rate-limit note | `PROVIDER_ERROR`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |
| Alpha Vantage empty quote | `QUOTE_NOT_FOUND`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |
| Alpha Vantage timeout | `PROVIDER_TIMEOUT`, `oic.switchBranch = PROVIDER_TIMEOUT`, `retryRecommended = true`. |
| Alpha Vantage network timeout mock | Patch `urllib.request.urlopen` with a `urllib.error.URLError("timeout")` side effect and verify `ProviderTimeoutError`. |
| Environment-backed settings mock | Use `unittest.mock.patch.dict` to seed environment variables before calling `load_settings()`; use `Settings(...)` only for explicit test object construction. |
| Secret redaction | API key is absent from logs, diagnostics, errors, and test output. |

### 11.2 API Contract Tests

| Scenario | Expected Result |
|----------|-----------------|
| `GET /health` | `200` with service metadata. |
| Valid alert-triggered request | `200`, `decision.code = ALERT_TRIGGERED`, `oic.switchBranch = ALERT_TRIGGERED`. |
| Valid no-alert request | `200`, `decision.code = NO_ALERT`, `oic.switchBranch = NO_ALERT`. |
| Invalid symbol | `400`, `error.code = VALIDATION_ERROR`, `oic.switchBranch = INPUT_ERROR`. |
| Mock provider quote missing | `502`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |
| Simulated provider timeout | `504`, `oic.switchBranch = PROVIDER_TIMEOUT`, `retryRecommended = true`. |
| Live mode without API key | `502`, `error.code = PROVIDER_ERROR`, no secret in response. |
| Live mode Alpha Vantage invalid symbol fixture | `502`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |

### 11.3 OIC Mapping Verification

- Confirm OIC can map `response.oic.switchBranch` into `stockAlertSwitchBranch`.
- Confirm each Switch branch expression matches one and only one expected value.
- Confirm triggered rule arrays can be mapped into a notification body.
- Confirm error details can be mapped into a fault or error logging payload.
- Confirm retry handling preserves `requestId`.

### 11.4 Local Verification Commands

The test suite must support both discovery-based execution and direct test-file execution from the repository root.

```sh
python3 -m unittest discover -s tests
```

```sh
python3 tests/test_alpha_vantage_provider.py
python3 tests/test_env_loader.py
python3 tests/test_api_contract.py
python3 tests/test_artifacts.py
python3 tests/test_evaluator.py
```

Direct test-file execution is required so handover reviewers can run focused tests without setting `PYTHONPATH` manually.

## 12. Implementation Order

1. Create project scaffold and `.gitignore`. Done.
2. Add API route for `GET /health`. Done.
3. Define request, response, quote, rule, decision, and error types. Done.
4. Implement request validation. Done.
5. Implement mock quote provider. Done.
6. Implement alert evaluator and aggregate decision mapper. Done.
7. Implement `POST /v1/alerts/evaluate`. Done.
8. Implement error mapper and logging. Done.
9. Add unit tests for evaluator and mapper. Done.
10. Add API contract checks using the selected test runner. Done.
11. Document local run and OIC mapping examples. Done.
12. Add `.env.example` with placeholder Alpha Vantage settings. Pending.
13. Add `.env` parser and setting precedence tests. Pending.
14. Add Alpha Vantage live provider module and fixture-based tests. Pending.
15. Wire live provider selection behind `QUOTE_PROVIDER_MODE=live` and `QUOTE_PROVIDER_NAME=alpha_vantage`. Pending.
16. Verify OIC branch mappings for Alpha Vantage rate-limit, invalid-symbol, timeout, and malformed-payload cases. Pending.

## 13. Traceability

| Plan Requirement | Design Coverage |
|------------------|-----------------|
| FR-001 Health endpoint | Sections 3.1 and 11.2 |
| FR-002 Rule input | Sections 4.1 and 4.2 |
| FR-003 Quote retrieval/mock | Sections 2.1, 3.2, 9, and 11.2 |
| FR-004 Alert evaluation | Sections 6.2 and 11.1 |
| FR-005 OIC-friendly response | Sections 4.3, 4.4, 6.3, and 7 |
| FR-006 Error handling | Sections 4.5 and 8 |
| FR-007 Mock provider | Sections 2.1, 9, and 11 |
| FR-008 Diagnostics | Sections 4.3, 6.1, and 9 |
| FR-009 `.env` credential parsing | Sections 2.1, 6.1.1, 9, and 11 |
| FR-010 Alpha Vantage `GLOBAL_QUOTE` outbound mapping | Sections 2.4, 5.3, 6.5, and 11 |

## 14. Open Questions

- Should the API persist watchlists later, or should OIC remain the system of record for alert rules?
- Which notification channels should OIC invoke when `ALERT_TRIGGERED` is returned?
- Should `QUOTE_UNAVAILABLE` ever retry automatically for provider-specific transient errors?
- Should Alpha Vantage `entitlement=delayed` or `entitlement=realtime` be supported as an optional setting for premium API keys?

## 15. Repository Publication

The project is prepared for publication to GitHub at:

```text
https://github.com/ai-ml-kiosk/test-oic-stock-api
```

The initial repository version includes the PDCA plan, design, Do notes, Python API implementation, README, and automated tests.
