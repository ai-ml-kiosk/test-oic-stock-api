# oic-stock-alert - Do Phase Implementation Notes

> Version: 1.1.0 | Date: 2026-05-26 | Status: Complete
> Design: `docs/02-design/features/oic-stock-alert.design.md`

---

## Summary

Implemented the OIC Stock Alert MVP as a dependency-free Python HTTP API. The implementation follows the approved design contract for JSON payloads, mapping logic, error handling, and OIC Switch branch routing.

This Do phase now includes the Alpha Vantage live provider extension and zero-trust local `.env` configuration layer added to the design on 2026-05-26.

Repository: `https://github.com/ai-ml-kiosk/test-oic-stock-api`

## Implemented Items

- Project scaffold with `.gitignore`, `pyproject.toml`, and `README.md`.
- Health endpoint: `GET /health`.
- Alert evaluation endpoint: `POST /v1/alerts/evaluate`.
- Request normalization for `requestId`, symbol, currency, provider mode, and OIC tracking ID.
- Validation for symbol format, rule counts, duplicate rule IDs, metrics, operators, thresholds, severity, and JSON body size.
- Mock quote provider with deterministic quotes for `ORCL`, `AAPL`, default symbols, and error fixtures:
  - `MISSING` -> quote unavailable.
  - `TIMEOUT` -> provider timeout.
  - `ERROR` -> provider error.
- Alpha Vantage live provider path:
  - `QUOTE_PROVIDER_MODE=live`
  - `QUOTE_PROVIDER_NAME=alpha_vantage`
  - `GLOBAL_QUOTE` outbound request mapping.
  - Alpha Vantage response normalization into the internal `Quote` model.
  - Upstream `Note`, `Information`, empty quote, malformed payload, and timeout mapping.
- Local `.env` configuration parser for untracked development secrets.
- `.env.example` placeholder template with no real credentials.
- Rule evaluation for `gt`, `gte`, `lt`, `lte`, `eq`, and `absGte`.
- Aggregate decision mapping for `ALERT_TRIGGERED` and `NO_ALERT`.
- Error mapping for `INPUT_ERROR`, `QUOTE_UNAVAILABLE`, `PROVIDER_TIMEOUT`, and `SYSTEM_ERROR`.
- OIC response metadata:
  - `oic.switchBranch`
  - `oic.notificationRecommended`
  - `oic.retryRecommended`
  - `oic.trackingId`
- Unit and API contract tests using Python `unittest`.
- Test files support both `python3 -m unittest discover -s tests` and direct file execution from the repository root.
- Direct-executable test files bootstrap the repository root onto `sys.path` before importing `oic_stock_alert`.
- Extracted reusable API/OIC artifacts under `artifacts/`:
  - OpenAPI 3.1 contract.
  - Request and response JSON Schemas.
  - Sample OIC request and response payloads.
  - OIC Switch branch mapping guide.

## Source Files

| File | Purpose |
|------|---------|
| `oic_stock_alert/config.py` | Runtime environment configuration. |
| `oic_stock_alert/env_loader.py` | Local `.env` parser and environment-default loader. |
| `oic_stock_alert/errors.py` | Application error classes and branch metadata. |
| `oic_stock_alert/validation.py` | Request validation and normalization. |
| `oic_stock_alert/quote_provider.py` | Quote provider abstraction and mock provider. |
| `oic_stock_alert/alpha_vantage_provider.py` | Alpha Vantage `GLOBAL_QUOTE` client and normalizer. |
| `oic_stock_alert/evaluator.py` | Rule evaluation and aggregate decision logic. |
| `oic_stock_alert/mapper.py` | Success/error response mapping. |
| `oic_stock_alert/app.py` | Application service layer. |
| `oic_stock_alert/server.py` | Standard-library HTTP server. |
| `tests/test_evaluator.py` | Unit tests for evaluator and validation behavior. |
| `tests/test_api_contract.py` | HTTP contract tests for API and OIC branch responses. |
| `tests/test_env_loader.py` | Unit tests for `.env` parsing and environment precedence. |
| `tests/test_alpha_vantage_provider.py` | Unit tests for Alpha Vantage normalization and provider errors. |
| `.env.example` | Non-secret local live-provider configuration template. |
| `artifacts/openapi/oic-stock-alert.openapi.json` | OpenAPI contract artifact. |
| `artifacts/json-schema/alert-evaluation-request.schema.json` | Request schema artifact. |
| `artifacts/json-schema/alert-evaluation-response.schema.json` | Response schema artifact. |
| `artifacts/samples/*.json` | Sample payload artifacts. |
| `artifacts/oic/oic-switch-branches.md` | OIC Switch branch artifact. |

## Verification Commands

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

```sh
python3 -m oic_stock_alert.server
```

## GitHub Publication

The repository target is:

```text
https://github.com/ai-ml-kiosk/test-oic-stock-api
```

This Do phase is ready for initial commit and push with the implementation, tests, README, and PDCA documentation.

## Design Traceability

| Design Item | Implementation |
|-------------|----------------|
| Health endpoint | `StockAlertHandler.do_GET`, `StockAlertApp.health` |
| Evaluation endpoint | `StockAlertHandler.do_POST`, `StockAlertApp.evaluate` |
| Request schema | `validate_request` |
| Mock provider | `get_quote`, `_mock_quote` |
| `.env` credential parsing | `load_env_file`, `apply_env_defaults`, `load_settings` |
| Alpha Vantage live provider | `get_alpha_vantage_quote`, `normalize_global_quote`, `get_quote` |
| Provider timeout mapping | `ProviderTimeoutError`, Alpha Vantage timeout handling |
| Alpha Vantage timeout test mock | `tests/test_alpha_vantage_provider.py` patches `urlopen` with `URLError(socket.timeout("timed out"))` |
| Environment-backed settings test mock | `tests/test_alpha_vantage_provider.py` uses `patch.dict` before `load_settings()` |
| Provider rate-limit / invalid-key mapping | Alpha Vantage `Note` and `Information` handling |
| Direct test-file execution | `tests/test_*.py` repository-root path bootstrap |
| Rule evaluation | `evaluate_rules`, `build_decision` |
| Success response mapping | `build_success_response` |
| Error response mapping | `build_error_response` |
| OIC Switch branches | `decision.code`, `oic.switchBranch`, error metadata |
| Contract tests | `tests/test_api_contract.py` |

## Next Step

Run `$pdca analyze oic-stock-alert` to compare the design against the implementation and calculate the match rate.
