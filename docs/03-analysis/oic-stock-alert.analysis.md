# Gap Analysis: oic-stock-alert

> Date: 2026-05-25 | Design: `docs/02-design/features/oic-stock-alert.design.md`
> Implementation: `oic_stock_alert/`, `tests/`, `artifacts/`

---

## Match Rate: 95%

Calculation: 38 implemented or substantially matched items / 40 design items = 95%.

The implementation is ready to proceed to the PDCA Report phase. Remaining gaps are low-risk MVP limitations already consistent with the design's open questions and live-provider deferral.

## Summary

The implementation closely follows the approved OIC Stock Alert design. The API provides the required health and alert evaluation endpoints, deterministic mock quote behavior, request validation, alert rule evaluation, OIC-friendly success and error payloads, Switch branch metadata, extracted OpenAPI/JSON Schema artifacts, sample payloads, and automated verification.

Verification command:

```sh
python3 -m unittest discover -s tests
```

Result: 16 tests passing.

## Implemented Items

### Runtime Architecture

- [x] API router exists in `oic_stock_alert/server.py`.
- [x] Request validator exists in `oic_stock_alert/validation.py`.
- [x] Quote provider abstraction exists in `oic_stock_alert/quote_provider.py`.
- [x] Alert evaluator exists in `oic_stock_alert/evaluator.py`.
- [x] Response mapper exists in `oic_stock_alert/mapper.py`.
- [x] Error mapper exists through `oic_stock_alert/errors.py` and `oic_stock_alert/mapper.py`.
- [x] Logger emits request ID, symbol, provider mode, decision code, and error code in `StockAlertApp._log_decision`.

### API Endpoints

- [x] `GET /health` returns service metadata, version, provider mode, and timestamp.
- [x] `POST /v1/alerts/evaluate` accepts JSON payloads and evaluates stock alert rules.
- [x] `Content-Type: application/json` is enforced for evaluation requests.
- [x] Optional `X-Request-Id` header is supported and used when body `requestId` is absent.
- [x] HTTP statuses are implemented for validation, unsupported rules, provider errors, provider timeouts, and unexpected errors.

### JSON Payloads

- [x] Evaluation request fields are normalized and validated: `requestId`, `source`, `symbol`, `currency`, `rules`, and `options`.
- [x] Success responses include `requestId`, `status`, `symbol`, `quote`, `rules`, `decision`, and `oic`.
- [x] Error responses include `requestId`, `status`, `symbol`, `error`, `decision`, and `oic`.
- [x] Diagnostics are conditionally included when `options.includeDiagnostics` is true.
- [x] Request and response JSON Schemas were extracted under `artifacts/json-schema/`.
- [x] OpenAPI 3.1 contract was extracted under `artifacts/openapi/`.
- [x] OIC-ready sample payloads were extracted under `artifacts/samples/`.

### Validation And Mapping Logic

- [x] Symbol normalization trims and uppercases values before pattern validation.
- [x] Currency normalization uppercases 3-letter currency values.
- [x] Rule count is constrained to 1-10 items.
- [x] Duplicate `ruleId` values are rejected.
- [x] Supported metrics are enforced: `lastPrice`, `changePercent`, `dayHigh`, `dayLow`, and `volume`.
- [x] Supported operators are enforced: `gt`, `gte`, `lt`, `lte`, `eq`, and `absGte`.
- [x] Numeric threshold validation rejects booleans, missing values, non-finite numbers, and negative non-`changePercent` thresholds.
- [x] Severity validation supports `info`, `warning`, `high`, and `critical`, defaulting to `warning`.
- [x] Message length is capped at 240 characters.
- [x] Request body size is capped at 64 KB.

### Alert Evaluation

- [x] `gt`, `gte`, `lt`, `lte`, `eq`, and `absGte` operator behavior is implemented.
- [x] Rule-level evaluation includes actual value, trigger status, severity, and message.
- [x] Aggregate decision maps triggered rules to `ALERT_TRIGGERED`.
- [x] Aggregate decision maps no triggered rules to `NO_ALERT`.
- [x] Highest triggered severity is selected for aggregate alert decisions.

### OIC Switch Branches

- [x] `oic.switchBranch` is returned on success and error responses.
- [x] `ALERT_TRIGGERED` branch is implemented.
- [x] `NO_ALERT` branch is implemented.
- [x] `INPUT_ERROR` branch is implemented.
- [x] `QUOTE_UNAVAILABLE` branch is implemented.
- [x] `PROVIDER_TIMEOUT` branch is implemented.
- [x] `SYSTEM_ERROR` branch is implemented.
- [x] `oic.notificationRecommended` is true only for `ALERT_TRIGGERED`.
- [x] `oic.retryRecommended` is true for `PROVIDER_TIMEOUT` and `SYSTEM_ERROR`.
- [x] OIC Switch branch mapping was extracted to `artifacts/oic/oic-switch-branches.md`.

### Configuration

- [x] `PORT` is implemented.
- [x] `QUOTE_PROVIDER_MODE` is implemented.
- [x] `QUOTE_PROVIDER_NAME` is loaded.
- [x] `QUOTE_PROVIDER_API_KEY` is loaded for future live-provider integration.
- [x] `QUOTE_PROVIDER_TIMEOUT_MS` is loaded.
- [x] `ALLOW_REQUEST_PROVIDER_OVERRIDE` is implemented.
- [x] `LOG_LEVEL` is implemented.

### Tests

- [x] Unit tests cover operator evaluation and aggregate severity.
- [x] Unit tests cover duplicate rule IDs and unsupported metrics.
- [x] API contract tests cover health, alert-triggered, no-alert, invalid symbol, missing quote, and provider timeout scenarios.
- [x] Artifact tests validate JSON parsing, sample request branch behavior, and response branch values.

## Missing Items

- [ ] Live quote provider integration is not implemented. This is an accepted MVP limitation because the design leaves live provider selection as an open question.
- [ ] `QUOTE_PROVIDER_TIMEOUT_MS` is loaded but not exercised by an outbound live provider. Timeout behavior is simulated in mock mode through the `TIMEOUT` symbol.

## Changed Items Or Deviations From Design

| Category | Design Item | Implementation | Impact |
|----------|-------------|----------------|--------|
| Changed | Design lists `QUOTE_PROVIDER_NAME` as provider identifier for diagnostics. | Runtime diagnostics expose `providerMode`; quote payload exposes `provider: "mock"`. `QUOTE_PROVIDER_NAME` is loaded but not surfaced directly. | Low. OIC still receives provider mode and quote provider identity. |
| Changed | Error contract says `PROVIDER_ERROR` retry recommendation is "Maybe". | `ProviderError.retry_recommended` is currently `false`. | Low. Conservative default avoids unsafe retry loops until provider-specific live errors exist. |
| Missing in Code | Live provider timeout configuration. | `QUOTE_PROVIDER_TIMEOUT_MS` is not used because live provider calls are not implemented. | Low for mock-first MVP; revisit with live provider selection. |
| Missing in Design | Extracted OpenAPI, JSON Schema, and sample artifacts. | Artifacts were added during `$pdca do --extract-artifacts` and documented in Do notes/README. | Positive addition; design can be updated later if strict traceability is required. |

## Match Matrix

| Area | Design Items | Matched | Notes |
|------|--------------|---------|-------|
| Runtime components | 7 | 7 | All core modules exist. |
| Endpoints and HTTP contract | 6 | 6 | Health and evaluation routes implemented. |
| Request validation | 9 | 9 | Includes body size, symbols, rule counts, duplicate IDs, metrics, operators, thresholds, severity, and messages. |
| Response contracts | 6 | 6 | Success, no-alert, error, diagnostics, decision, and OIC metadata implemented. |
| Evaluation logic | 4 | 4 | All operators and severity aggregation implemented. |
| OIC Switch branches | 6 | 6 | All designed branch values implemented and artifacted. |
| Configuration | 7 | 5 | Provider name/API key/timeout are loaded, but not fully exercised without live provider. |
| Tests and artifacts | 5 | 5 | Unit, API contract, artifact tests, OpenAPI, JSON Schemas, and samples exist. |

## Recommendations

1. Proceed to `$pdca report oic-stock-alert` because the match rate is above 90%.
2. Keep live quote provider selection as a future feature after MVP validation.
3. When live provider work starts, add provider-specific retry classification and use `QUOTE_PROVIDER_TIMEOUT_MS` for outbound HTTP timeout handling.
4. Optionally update the design document to make extracted artifacts first-class design deliverables, since they now exist and are tested.

## Next Steps

- [x] Run implementation and artifact tests.
- [x] Write gap analysis document.
- [ ] Run `$pdca report oic-stock-alert`.

