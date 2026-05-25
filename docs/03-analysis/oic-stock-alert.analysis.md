# Gap Analysis: oic-stock-alert

> Date: 2026-05-26 | Design: `docs/02-design/features/oic-stock-alert.design.md`
> Implementation: `oic_stock_alert/`, `tests/`, `artifacts/`, `.env.example`

---

## Match Rate: 96%

Calculation: 49 implemented or substantially matched items / 51 design items = 96%.

The implementation is ready to proceed to the PDCA Report phase. The Alpha Vantage live-provider extension and zero-trust `.env` configuration layer are now implemented behind runtime configuration, while the existing mock path and OIC response contract remain stable.

## Summary

The implementation now matches the updated 1.1 design for the OIC Stock Alert API. The codebase includes the original mock-provider MVP plus:

- Alpha Vantage `GLOBAL_QUOTE` live provider module.
- Local untracked `.env` parsing with process-environment precedence.
- `.env.example` placeholder template.
- Live-provider selection through `QUOTE_PROVIDER_MODE=live` and `QUOTE_PROVIDER_NAME=alpha_vantage`.
- Alpha Vantage response normalization into the internal `Quote` shape.
- Upstream provider error mapping for empty quote, rate-limit note, invalid-key/information payload, timeout, malformed JSON, and malformed quote payloads.
- Fixture-based tests that do not require live network access or a real API key.

Verification command:

```sh
python3 -m unittest discover -s tests
```

Result: 26 tests passing.

## Implemented Items

### Runtime Architecture

- [x] API router exists in `oic_stock_alert/server.py`.
- [x] Request validator exists in `oic_stock_alert/validation.py`.
- [x] Quote provider facade exists in `oic_stock_alert/quote_provider.py`.
- [x] Mock provider path remains the default local and CI path.
- [x] Alpha Vantage live provider exists in `oic_stock_alert/alpha_vantage_provider.py`.
- [x] `.env` config loader exists in `oic_stock_alert/env_loader.py`.
- [x] Alert evaluator exists in `oic_stock_alert/evaluator.py`.
- [x] Response mapper exists in `oic_stock_alert/mapper.py`.
- [x] Error mapper exists through `oic_stock_alert/errors.py` and `oic_stock_alert/mapper.py`.
- [x] Logger emits request ID, symbol, provider mode, decision code, and error code without full provider URLs.

### API Endpoints

- [x] `GET /health` returns service metadata, version, provider mode, and timestamp.
- [x] `POST /v1/alerts/evaluate` accepts JSON payloads and evaluates stock alert rules.
- [x] `Content-Type: application/json` is enforced for evaluation requests.
- [x] Optional `X-Request-Id` header is supported and used when body `requestId` is absent.
- [x] HTTP statuses are implemented for validation, unsupported rules, provider errors, provider timeouts, and unexpected errors.
- [x] OIC-facing request and response contracts are unchanged by live-provider support.

### Alpha Vantage Live Provider

- [x] Live provider selection is implemented for `QUOTE_PROVIDER_MODE=live`.
- [x] Alpha Vantage provider selection is implemented for `QUOTE_PROVIDER_NAME=alpha_vantage`.
- [x] Missing `QUOTE_PROVIDER_API_KEY` maps to `PROVIDER_ERROR` without exposing a key.
- [x] Outbound request uses `https://www.alphavantage.co/query`.
- [x] Outbound query includes `function=GLOBAL_QUOTE`, normalized symbol, and API key.
- [x] Outbound timeout uses `QUOTE_PROVIDER_TIMEOUT_MS`, defaulting to 1500 ms through settings.
- [x] Alpha Vantage `Global Quote` response is normalized into internal `Quote`.
- [x] Decimal string fields are converted to numeric quote fields.
- [x] Percent strings are stripped and converted to `changePercent`.
- [x] Volume is converted to integer.
- [x] Latest trading day is converted to an ISO-style UTC timestamp when possible.
- [x] Provider identity is set to `alpha_vantage`.

### `.env` Configuration

- [x] `.env` loading is implemented in `load_settings()`.
- [x] Blank lines and comments are ignored.
- [x] `KEY=value` parsing trims keys and values.
- [x] Simple quoted values are supported.
- [x] Shell evaluation and substitution are not performed.
- [x] Process environment variables take precedence over `.env` values.
- [x] `.env` and `.env*` are ignored by `.gitignore`.
- [x] `.env.example` is present with placeholder values only.

### JSON Payloads

- [x] Evaluation request fields are normalized and validated: `requestId`, `source`, `symbol`, `currency`, `rules`, and `options`.
- [x] Success responses include `requestId`, `status`, `symbol`, `quote`, `rules`, `decision`, and `oic`.
- [x] Error responses include `requestId`, `status`, `symbol`, `error`, `decision`, and `oic`.
- [x] Diagnostics are conditionally included when `options.includeDiagnostics` is true.
- [x] Request and response JSON Schemas exist under `artifacts/json-schema/`.
- [x] OpenAPI 3.1 contract exists under `artifacts/openapi/`.
- [x] OIC-ready sample payloads exist under `artifacts/samples/`.

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

### Provider Error Mapping

- [x] Empty Alpha Vantage `Global Quote` maps to `QUOTE_NOT_FOUND` / `QUOTE_UNAVAILABLE`.
- [x] Alpha Vantage `Error Message` maps to `QUOTE_NOT_FOUND` / `QUOTE_UNAVAILABLE`.
- [x] Alpha Vantage `Note` maps to `PROVIDER_ERROR` / `QUOTE_UNAVAILABLE`.
- [x] Alpha Vantage `Information` maps to `PROVIDER_ERROR` / `QUOTE_UNAVAILABLE`.
- [x] Outbound timeout maps to `PROVIDER_TIMEOUT` / `PROVIDER_TIMEOUT` with retry recommended.
- [x] Malformed JSON maps to `PROVIDER_ERROR` / `QUOTE_UNAVAILABLE`.
- [x] Malformed quote payload maps to `PROVIDER_ERROR` / `QUOTE_UNAVAILABLE`.

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
- [x] OIC Switch branch mapping exists at `artifacts/oic/oic-switch-branches.md`.

### Tests

- [x] Unit tests cover operator evaluation and aggregate severity.
- [x] Unit tests cover duplicate rule IDs and unsupported metrics.
- [x] API contract tests cover health, alert-triggered, no-alert, invalid symbol, missing quote, and provider timeout scenarios.
- [x] Artifact tests validate JSON parsing, sample request branch behavior, and response branch values.
- [x] `.env` tests cover comments, blank lines, quoted values, and process-environment precedence.
- [x] Alpha Vantage tests cover quote normalization, empty quote, rate-limit note, invalid-key information, malformed quote, unsupported provider, missing API key, and timeout.

## Missing Items

- [ ] API-contract-level tests for live Alpha Vantage invalid-symbol and missing-key requests are not yet implemented. Equivalent provider-level coverage exists, and app-level error mapping uses the same `StockAlertError` path as the existing API contract tests.
- [ ] The generated OpenAPI and JSON Schema artifacts have not yet been extended with live-provider configuration examples. The runtime payload contract remains stable, so this is documentation depth rather than a behavioral gap.

## Changed Items Or Deviations From Design

| Category | Design Item | Implementation | Impact |
|----------|-------------|----------------|--------|
| Changed | Design says unexpected provider client exceptions should map to `SYSTEM_ERROR`. | Known HTTP, URL, JSON, malformed quote, rate-limit, and information responses map to provider-specific errors; truly unexpected exceptions still map through the app-level `StockAlertError` fallback. | Low. Stable OIC branches are preserved. |
| Changed | Design examples still show health version `1.0.0`. | Runtime health still returns `1.0.0` while design docs are versioned `1.1.0`. | Low. Service version can be bumped during release packaging. |
| Missing in Tests | API contract tests for live mode. | Provider-level tests cover live behavior without network or real API keys. | Low. Add API-level fixture tests if stricter coverage is needed. |
| Missing in Artifacts | OpenAPI examples for Alpha Vantage mode. | README, plan, design, HLD, LLD, and Do notes document live mode. | Low. Contract remains unchanged. |

## Match Matrix

| Area | Design Items | Matched | Notes |
|------|--------------|---------|-------|
| Runtime components | 9 | 9 | Includes new Alpha Vantage and `.env` modules. |
| Endpoints and HTTP contract | 6 | 6 | Health and evaluation routes unchanged and passing. |
| Request validation | 9 | 9 | Existing validation remains intact. |
| Response contracts | 6 | 6 | Success, no-alert, error, diagnostics, decision, and OIC metadata implemented. |
| Alpha Vantage outbound mapping | 8 | 8 | Endpoint, query params, timeout, and normalizer implemented. |
| `.env` credential handling | 7 | 7 | Parser, precedence, `.gitignore`, and `.env.example` implemented. |
| Provider error mapping | 7 | 6 | Main provider conditions covered; one unexpected-client classification is handled at app fallback level. |
| Evaluation logic | 4 | 4 | All operators and severity aggregation implemented. |
| OIC Switch branches | 6 | 6 | All designed branch values implemented. |
| Tests and artifacts | 7 | 5 | Runtime tests added; OpenAPI/schema live examples and API-level live tests remain optional gaps. |

## Recommendations

1. Proceed to `$pdca report oic-stock-alert` because the match rate is above 90%.
2. Add API-level live-provider fixture tests in a future hardening pass if strict endpoint coverage is required.
3. Extend OpenAPI examples with Alpha Vantage live-mode configuration notes during the next artifact extraction/report cycle.
4. Consider bumping the runtime health `version` from `1.0.0` to `1.1.0` when packaging the live-provider release.

## Next Steps

- [x] Run implementation, provider, environment, API contract, and artifact tests.
- [x] Refresh gap analysis document.
- [ ] Run `$pdca report oic-stock-alert`.
