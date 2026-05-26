# OIC Stock Alert - Low-Level Design

> Version: 1.1.0 | Date: 2026-05-26 | Status: Complete
> Source Design: `docs/02-design/features/oic-stock-alert.design.md`
> Repository: `https://github.com/ai-ml-kiosk/test-oic-stock-api`

---

## 1. Purpose

This Low-Level Design defines the detailed contracts and implementation logic for the OIC Stock Alert API. It covers JSON payload specifications, mapping logic, validation rules, OIC Switch branch structures, module-level behavior, and test cases.

The companion HLD is:

`docs/02-design/features/oic-stock-alert.hld.md`

## 2. Source Artifacts

| Artifact | Purpose |
|----------|---------|
| `artifacts/openapi/oic-stock-alert.openapi.json` | REST API contract. |
| `artifacts/json-schema/alert-evaluation-request.schema.json` | Request payload schema. |
| `artifacts/json-schema/alert-evaluation-response.schema.json` | Success and error response schema. |
| `artifacts/oic/oic-switch-branches.md` | OIC Switch expression and branch mapping guide. |
| `artifacts/samples/*.json` | Example request, success, no-alert, validation error, and timeout payloads. |

## 3. Endpoint Detail

OIC-facing endpoint exposure:

- OIC invokes the API over HTTPS at the external ingress endpoint.
- HTTPS terminates at OCI API Gateway, OCI Load Balancer, or a reverse proxy.
- `oic_stock_alert.server` remains an HTTP-only internal service, normally listening on port `8080`.
- The internal HTTP port must be reachable only from the TLS termination layer or trusted private network, not directly from the public internet.

### 3.1 `GET /health`

Response status:

- `200 OK`

Response fields:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `ok` when service is running. |
| `service` | string | `oic-stock-alert`. |
| `version` | string | API version. |
| `providerMode` | string | Active quote provider mode. |
| `timestamp` | string | UTC timestamp in ISO-8601 format. |

### 3.2 `POST /v1/alerts/evaluate`

Request headers:

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type: application/json` | Yes | JSON payload format. |
| `X-Request-Id` | No | Caller-provided correlation ID fallback. |

Status mapping:

| Condition | HTTP Status |
|-----------|-------------|
| Valid evaluation, alert triggered | `200` |
| Valid evaluation, no alert | `200` |
| Invalid JSON or validation failure | `400` |
| Unsupported rule configuration | `422` |
| Quote not found or provider error | `502` |
| Provider timeout | `504` |
| Unexpected exception | `500` |

## 4. Request JSON Payload

Canonical request:

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

Field rules:

| Field | Required | Type | Rule |
|-------|----------|------|------|
| `requestId` | No | string | Max 80 characters. Body value wins over header fallback. |
| `source.system` | No | string | Expected `OIC` for OIC calls. |
| `source.integrationName` | No | string | Max 120 characters. |
| `source.instanceId` | No | string | Copied to `oic.trackingId` when present. |
| `symbol` | Yes | string | Trimmed, uppercased, pattern `^[A-Z][A-Z0-9.:-]{0,14}$`. |
| `currency` | No | string | 3-letter code, uppercased. |
| `rules` | Yes | array | Minimum 1, maximum 10. |
| `rules[].ruleId` | Yes | string | Unique per request, max 80 characters. |
| `rules[].metric` | Yes | string | `lastPrice`, `changePercent`, `dayHigh`, `dayLow`, or `volume`. |
| `rules[].operator` | Yes | string | `gt`, `gte`, `lt`, `lte`, `eq`, or `absGte`. |
| `rules[].threshold` | Yes | number | Finite numeric value. Non-negative except for `changePercent`. |
| `rules[].severity` | No | string | `info`, `warning`, `high`, or `critical`; defaults to `warning`. |
| `rules[].message` | No | string | Max 240 characters; defaults to empty string. |
| `options.providerMode` | No | string | `mock` or `live`. Runtime config controls override support. |
| `options.includeDiagnostics` | No | boolean | Defaults to `false`. |

## 4.1 Local `.env` Configuration Payload

Local live-provider testing uses an untracked `.env` file. The committed artifact is `.env.example` with placeholder values only.

```sh
QUOTE_PROVIDER_MODE=live
QUOTE_PROVIDER_NAME=alpha_vantage
QUOTE_PROVIDER_API_KEY=replace-with-local-alpha-vantage-key
QUOTE_PROVIDER_TIMEOUT_MS=1500
ALLOW_REQUEST_PROVIDER_OVERRIDE=false
```

Parser rules:

- Accept `KEY=value` lines.
- Trim surrounding whitespace around keys and values.
- Ignore blank lines and lines beginning with `#`.
- Do not execute shell commands, substitutions, or nested variable expansion.
- Process environment variables override `.env` values.
- Do not expose `QUOTE_PROVIDER_API_KEY` in diagnostics, logs, exceptions, or responses.

## 4.2 Deployment and HTTPS Runtime Configuration

The Python service does not terminate TLS. HTTPS configuration belongs to the selected ingress layer.

| Setting or Control | Location | Requirement |
|--------------------|----------|-------------|
| TLS certificate | Gateway, load balancer, or reverse proxy | Must be valid and trusted by OIC. |
| HTTPS listener | Gateway, load balancer, or reverse proxy | Must expose the OIC invoke URL over TCP `443` or the approved HTTPS port. |
| Internal target | Ingress backend configuration | Must forward to the HTTP application service, default `http://<private-host>:8080`. |
| Application port | `PORT` environment variable | Defaults to `8080`; should not be publicly exposed directly. |
| Firewall / security list | Cloud network or host firewall | Allow inbound HTTPS to ingress; restrict application port to ingress/private callers only. |
| Certificate renewal | Ingress operations | Must be monitored so OIC invokes do not fail because of expiry. |

### 4.3 Preferred OCI API Gateway Mapping

Use OCI API Gateway as the preferred production ingress for OIC REST invokes.

| Field | Value |
|-------|-------|
| Public protocol | HTTPS |
| Public port | `443` |
| Public path | `/health`, `/v1/alerts/evaluate` |
| Backend protocol | HTTP |
| Backend target | Private application host or private load-balancer target |
| Backend port | `8080` unless `PORT` is overridden |
| OIC connection URL | `https://<gateway-host>/v1/alerts/evaluate` |

Header forwarding:

| Header | Requirement |
|--------|-------------|
| `Host` | Preserve or set to backend-compatible host according to platform routing. |
| `X-Forwarded-Proto` | Set to `https` where supported. |
| `X-Forwarded-For` | Preserve caller chain for operations visibility where supported. |
| `X-Request-Id` | Preserve OIC request correlation header when present. |
| `Content-Type` | Preserve `application/json` for POST requests. |

Security-list and firewall rules:

- Allow inbound TCP `443` to the API Gateway, load balancer, or reverse proxy.
- Allow inbound TCP `80` only when the ingress uses HTTP-to-HTTPS redirect.
- Restrict inbound TCP `8080` to the gateway, load balancer, reverse proxy, localhost, or private subnet only.
- Do not expose `8080` directly as the OIC endpoint.

### 4.4 VM Reverse Proxy Alternatives

Nginx conceptual mapping:

```text
listen 443 ssl
server_name <public-host>
proxy_pass http://127.0.0.1:8080
proxy_set_header Host $host
proxy_set_header X-Forwarded-Proto https
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for
proxy_set_header X-Request-Id $http_x_request_id
```

Caddy conceptual mapping:

```text
<public-host> {
  reverse_proxy 127.0.0.1:8080
}
```

Redirect behavior:

- HTTP `80 -> 443` redirect is owned by the ingress/proxy layer.
- `oic_stock_alert.server` does not redirect HTTP to HTTPS.
- Direct local HTTP remains valid for development and private health checks.

## 5. Response JSON Payloads

### 5.1 Success Response

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

### 5.2 Error Response

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

## 6. Mapping Logic

### 6.1 Request Normalization

| Source | Target | Logic |
|--------|--------|-------|
| Body `requestId` | `request.requestId` | Use when supplied and valid. |
| Header `X-Request-Id` | `request.requestId` | Fallback when body value is absent. |
| Generated UUID | `request.requestId` | Fallback when body and header are absent. |
| Body `symbol` | `request.symbol` | Trim, uppercase, validate pattern. |
| Body `currency` | `request.currency` | Uppercase; if absent, use provider quote currency or `USD`. |
| `source.instanceId` | `oic.trackingId` | Copy when present; otherwise use `requestId`. |
| `options.providerMode` | provider mode | Apply only when request override is enabled; otherwise use runtime default. |
| Missing `rules[].severity` | normalized rule severity | Default to `warning`. |
| Missing `rules[].message` | normalized rule message | Default to empty string. |

### 6.1.1 Alpha Vantage Outbound Request Mapping

Provider selection:

| Setting | Required Value |
|---------|----------------|
| `QUOTE_PROVIDER_MODE` | `live` |
| `QUOTE_PROVIDER_NAME` | `alpha_vantage` |
| `QUOTE_PROVIDER_API_KEY` | Non-empty local or runtime secret |

Outbound request:

```text
GET https://www.alphavantage.co/query
```

Query parameters:

| Parameter | Value |
|-----------|-------|
| `function` | `GLOBAL_QUOTE` |
| `symbol` | Normalized request symbol |
| `apikey` | `QUOTE_PROVIDER_API_KEY` |
| `datatype` | Omitted; JSON is the default |
| `entitlement` | Omitted for MVP |

Timeout:

- Use `QUOTE_PROVIDER_TIMEOUT_MS`.
- Default: `1500`.
- Timeout maps to `PROVIDER_TIMEOUT`.

Freshness:

- Alpha Vantage quote freshness depends on API entitlement.
- Realtime or 15-minute delayed data is outside the default MVP guarantee.

### 6.1.2 Alpha Vantage Response Normalization

| Alpha Vantage Field | Internal Field | Conversion |
|---------------------|----------------|------------|
| `01. symbol` | `symbol` | String. |
| `03. high` | `dayHigh` | Decimal string to number. |
| `04. low` | `dayLow` | Decimal string to number. |
| `05. price` | `lastPrice` | Decimal string to number. |
| `06. volume` | `volume` | Integer string to integer. |
| `07. latest trading day` | `asOf` | Date string to UTC date-like timestamp. |
| `09. change` | `change` | Decimal string to number. |
| `10. change percent` | `changePercent` | Strip `%`, then decimal string to number. |
| constant | `currency` | `USD` for MVP. |
| constant | `provider` | `alpha_vantage`. |

### 6.2 Rule Evaluation

| Operator | Trigger Logic |
|----------|---------------|
| `gt` | `actualValue > threshold` |
| `gte` | `actualValue >= threshold` |
| `lt` | `actualValue < threshold` |
| `lte` | `actualValue <= threshold` |
| `eq` | `actualValue == threshold` after numeric normalization |
| `absGte` | `abs(actualValue) >= threshold` |

The evaluator reads the requested metric from the quote. If the metric is missing from a quote that should contain it, the provider path is mapped to a quote-unavailable style error.

### 6.3 Aggregate Decision

| Condition | Decision Code | Triggered | Severity | Switch Branch | Retry |
|-----------|---------------|-----------|----------|---------------|-------|
| One or more rules triggered | `ALERT_TRIGGERED` | `true` | Highest triggered severity | `ALERT_TRIGGERED` | `false` |
| No rules triggered | `NO_ALERT` | `false` | `info` | `NO_ALERT` | `false` |
| Validation failure | `INPUT_ERROR` | `false` | `warning` | `INPUT_ERROR` | `false` |
| Unsupported rule | `INPUT_ERROR` | `false` | `warning` | `INPUT_ERROR` | `false` |
| Quote not found | `QUOTE_UNAVAILABLE` | `false` | `warning` | `QUOTE_UNAVAILABLE` | `false` |
| Provider timeout | `PROVIDER_TIMEOUT` | `false` | `warning` | `PROVIDER_TIMEOUT` | `true` |
| Unexpected exception | `SYSTEM_ERROR` | `false` | `critical` | `SYSTEM_ERROR` | `true` |
| Alpha Vantage empty quote | `QUOTE_UNAVAILABLE` | `false` | `warning` | `QUOTE_UNAVAILABLE` | `false` |
| Alpha Vantage rate-limit note | `QUOTE_UNAVAILABLE` | `false` | `warning` | `QUOTE_UNAVAILABLE` | OIC policy |
| Alpha Vantage invalid-key information | `QUOTE_UNAVAILABLE` | `false` | `warning` | `QUOTE_UNAVAILABLE` | `false` |

Severity precedence:

```text
critical > high > warning > info
```

## 7. OIC Switch Branch Structures

Primary expression:

```text
response.oic.switchBranch
```

Optional assigned variable:

```text
stockAlertSwitchBranch = response.oic.switchBranch
```

Branches:

| Branch | Match Value | Retry | Notification | Purpose |
|--------|-------------|-------|--------------|---------|
| Alert Triggered | `ALERT_TRIGGERED` | No | Yes | Build and send alert notification. |
| No Alert | `NO_ALERT` | No | No | Log no-op and end successfully. |
| Input Error | `INPUT_ERROR` | No | No | Record invalid inbound payload or unsupported rule. |
| Quote Unavailable | `QUOTE_UNAVAILABLE` | Usually no | No | Record business exception for missing market data. |
| Provider Timeout | `PROVIDER_TIMEOUT` | Yes | No | Route to retry or recoverable fault handling. |
| System Error | `SYSTEM_ERROR` | Yes | No | Route to technical fault handling and operations logging. |
| Otherwise | unmatched | No | No | Treat as technical fault and preserve diagnostics. |

Alert notification mapping:

| Target Field | Source |
|--------------|--------|
| `subject` | `concat(response.symbol, " stock alert: ", response.decision.severity)` |
| `body` | `response.decision.message` plus triggered rule messages and quote values |
| `symbol` | `response.symbol` |
| `price` | `response.quote.lastPrice` |
| `currency` | `response.quote.currency` |
| `triggeredRules` | Filter `response.rules` where `triggered = true` |
| `trackingId` | `response.oic.trackingId` |
| `requestId` | `response.requestId` |

Error logging mapping:

| Branch | Primary Fields |
|--------|----------------|
| `INPUT_ERROR` | `requestId`, `symbol`, `error.code`, `error.details` |
| `QUOTE_UNAVAILABLE` | `requestId`, `symbol`, `error.code`, `error.message` |
| `PROVIDER_TIMEOUT` | `requestId`, `symbol`, `error.code`, `oic.retryRecommended` |
| `SYSTEM_ERROR` | `requestId`, `symbol`, `error.code`, `error.message` |

## 8. Module-Level Design

| Module | Key Functions or Types | Behavior |
|--------|------------------------|----------|
| `config.py` | `Settings`, settings loader | Reads environment defaults for port, provider, timeout, and override behavior. |
| `validation.py` | request validation and normalization | Enforces JSON shape, symbols, rule count, unique IDs, metrics, operators, thresholds, severity, and options. |
| `quote_provider.py` | mock quote provider | Returns deterministic quote data and provider error fixtures for contract tests. |
| `alpha_vantage_provider.py` | Alpha Vantage REST client | Calls `GLOBAL_QUOTE`, applies timeout, normalizes response, and maps provider errors. |
| `env_loader.py` | local `.env` parser | Loads untracked local settings without shell execution or secret logging. |
| `evaluator.py` | `evaluate_rules`, `build_decision` | Applies rule operators and derives aggregate decision code, severity, and message. |
| `mapper.py` | `build_success_response`, `build_error_response` | Builds OIC-friendly response payloads with decision and branch fields. |
| `errors.py` | stock alert exception classes | Converts validation, provider, timeout, and system conditions into stable error metadata. |
| `app.py` | application service | Coordinates validation, provider lookup, evaluation, mapping, and error handling. |
| `server.py` | HTTP handler | Parses requests, routes endpoints, serializes JSON responses, and emits status codes. |

`server.py` runtime boundary:

- Uses Python `ThreadingHTTPServer` for plain HTTP handling.
- Does not load certificates or private keys.
- Does not implement HTTPS listeners directly.
- Relies on the deployment ingress layer to provide OIC-compatible HTTPS.

## 9. Error Contract

| Error Code | HTTP Status | Decision Code | Switch Branch | Retry |
|------------|-------------|---------------|---------------|-------|
| `VALIDATION_ERROR` | 400 | `INPUT_ERROR` | `INPUT_ERROR` | No |
| `UNSUPPORTED_RULE` | 422 | `INPUT_ERROR` | `INPUT_ERROR` | No |
| `QUOTE_NOT_FOUND` | 502 | `QUOTE_UNAVAILABLE` | `QUOTE_UNAVAILABLE` | No |
| `PROVIDER_ERROR` | 502 | `QUOTE_UNAVAILABLE` | `QUOTE_UNAVAILABLE` | Maybe by OIC policy |
| `PROVIDER_TIMEOUT` | 504 | `PROVIDER_TIMEOUT` | `PROVIDER_TIMEOUT` | Yes |
| `SYSTEM_ERROR` | 500 | `SYSTEM_ERROR` | `SYSTEM_ERROR` | Yes |

Alpha Vantage provider mapping:

| Upstream Payload or Condition | Error Code | Switch Branch | Notes |
|-------------------------------|------------|---------------|-------|
| Empty `Global Quote` object | `QUOTE_NOT_FOUND` | `QUOTE_UNAVAILABLE` | Covers invalid or unsupported symbol payloads. |
| `Note` message | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | Covers provider rate-limit messages. |
| `Information` message | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | Covers invalid key or entitlement-style messages. |
| Outbound timeout | `PROVIDER_TIMEOUT` | `PROVIDER_TIMEOUT` | Must set `oic.retryRecommended=true`. |
| Malformed JSON | `PROVIDER_ERROR` | `QUOTE_UNAVAILABLE` | Do not expose raw provider payload if it might include secrets. |
| Unexpected client exception | `SYSTEM_ERROR` | `SYSTEM_ERROR` | Log sanitized exception category only. |

## 10. Validation Rules

- Reject malformed JSON.
- Reject oversized JSON bodies beyond the service limit.
- Require `symbol`.
- Require one to ten rules.
- Reject duplicate `ruleId` values.
- Reject unknown metrics.
- Reject unknown operators.
- Reject missing or non-numeric thresholds.
- Reject negative thresholds except where supported for `changePercent`.
- Validate severity against `info`, `warning`, `high`, and `critical`.
- Default missing severity to `warning`.
- Exclude diagnostics unless `options.includeDiagnostics` is `true`.
- Reject live mode when `QUOTE_PROVIDER_API_KEY` is missing or blank.
- Reject unsupported live provider names.
- Never include `QUOTE_PROVIDER_API_KEY` in error details.

## 11. Test Cases

### 11.1 Unit Tests

| Test | Expected Result |
|------|-----------------|
| `lastPrice gte threshold` with actual above threshold | Rule triggered. |
| `lastPrice lt threshold` with actual above threshold | Rule not triggered. |
| `changePercent absGte threshold` with negative actual beyond threshold | Rule triggered. |
| Multiple triggered rules with different severities | Aggregate severity is highest severity. |
| No triggered rules | `decision.code = NO_ALERT`. |
| Duplicate `ruleId` values | Validation error. |
| Unsupported metric | Input error path. |
| `.env` parser ignores comments and blank lines | Settings load successfully. |
| Process environment overrides `.env` | Effective runtime setting comes from process environment. |
| Missing Alpha Vantage API key in live mode | Provider error without secret leakage. |
| Alpha Vantage `Global Quote` fixture | Normalized quote has numeric `lastPrice`, `dayHigh`, `dayLow`, `change`, `changePercent`, and integer `volume`. |
| Alpha Vantage rate-limit `Note` fixture | `QUOTE_UNAVAILABLE` branch. |
| Alpha Vantage invalid-key `Information` fixture | `QUOTE_UNAVAILABLE` branch. |
| Alpha Vantage timeout | `PROVIDER_TIMEOUT` branch and retry recommended. |
| Secret redaction | API key absent from logs, diagnostics, response body, and assertion output. |

### 11.2 API Contract Tests

| Scenario | Expected Result |
|----------|-----------------|
| `GET /health` | `200` with service metadata. |
| Valid alert-triggered request | `200`, `decision.code = ALERT_TRIGGERED`, `oic.switchBranch = ALERT_TRIGGERED`. |
| Valid no-alert request | `200`, `decision.code = NO_ALERT`, `oic.switchBranch = NO_ALERT`. |
| Invalid symbol | `400`, `error.code = VALIDATION_ERROR`, `oic.switchBranch = INPUT_ERROR`. |
| Mock provider quote missing | `502`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |
| Simulated provider timeout | `504`, `oic.switchBranch = PROVIDER_TIMEOUT`, `retryRecommended = true`. |

### 11.3 Deployment Smoke Tests

HTTPS is validated through deployment smoke tests against the selected ingress endpoint, not through the internal Python unittest server.

| Scenario | Command Shape | Expected Result |
|----------|---------------|-----------------|
| HTTPS health through ingress | `curl https://<gateway-host>/health` | `200` JSON health response. |
| HTTPS evaluation through ingress | `curl -X POST https://<gateway-host>/v1/alerts/evaluate ...` | `200` JSON response with `oic.switchBranch`. |
| Optional HTTP redirect | `curl -I http://<gateway-host>/health` | `301` or `308` redirect to HTTPS when port `80` is enabled. |
| App port blocked publicly | `curl http://<public-host>:8080/health` | Connection blocked or unavailable from the public internet. |
| Live Alpha Vantage fixture alert-triggered | `200`, provider `alpha_vantage`, expected branch from evaluated quote. |
| Live Alpha Vantage invalid symbol fixture | `502`, `oic.switchBranch = QUOTE_UNAVAILABLE`. |

### 11.4 Artifact Tests

| Artifact | Expected Result |
|----------|-----------------|
| OpenAPI JSON | Valid JSON and includes `/v1/alerts/evaluate`. |
| Request schema | Valid JSON and requires `symbol` and `rules`. |
| Response schema | Valid JSON and defines success and error response alternatives. |
| Sample payloads | Valid JSON and aligned with branch expectations. |
| OIC switch guide | Documents all branch values. |

### 11.5 Verification Commands
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

## 12. Implementation Sequence

1. Load runtime settings.
2. Parse HTTP request and JSON body.
3. Normalize and validate request.
4. Load `.env` and process environment into settings.
5. Select provider mode.
6. If live Alpha Vantage mode is selected, require API key and call `GLOBAL_QUOTE`.
7. Normalize provider quote into internal shape.
8. Evaluate rules.
9. Build aggregate decision.
10. Map success or error response.
11. Return HTTP status and JSON response.
12. Let OIC branch on `response.oic.switchBranch`.

## 13. LLD Decisions

| Decision | Rationale |
|----------|-----------|
| Keep `decision.code` equal to success `oic.switchBranch` | Prevents branch mismatch for successful evaluations. |
| Always include `oic` routing object | OIC can branch consistently on success and error responses. |
| Keep diagnostics optional | Reduces payload noise while preserving troubleshooting support. |
| Preserve `requestId` in all responses | Enables retry correlation and support investigation. |
| Use explicit switch branch enum | Avoids brittle text matching in OIC. |
| Keep Alpha Vantage behind provider interface | Live market data changes do not alter OIC-facing API contracts. |
| Use `.env` only as local secret input | Prevents accidental API-key commits while preserving deployed environment-variable configuration. |
| Omit Alpha Vantage entitlement for MVP | Keeps first live integration small; realtime and delayed entitlement can be added later. |
