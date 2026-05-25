# OIC Stock Alert API

Dependency-free Python implementation of the OIC Stock Alert MVP.

Repository: https://github.com/ai-ml-kiosk/test-oic-stock-api

## Run

```sh
python3 -m oic_stock_alert.server
```

Default URL:

```text
http://localhost:8080
```

## Health

```sh
curl http://localhost:8080/health
```

## Evaluate An Alert

```sh
curl -s http://localhost:8080/v1/alerts/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "requestId": "oic-run-20260525-001",
    "source": {
      "system": "OIC",
      "integrationName": "StockAlertIntegration",
      "instanceId": "300000123456789"
    },
    "symbol": "ORCL",
    "rules": [
      {
        "ruleId": "orcl-above-150",
        "metric": "lastPrice",
        "operator": "gte",
        "threshold": 150,
        "severity": "high",
        "message": "ORCL crossed target price"
      }
    ],
    "options": {
      "includeDiagnostics": true
    }
  }'
```

## OIC Switch Field

Map this response field into the OIC Switch expression:

```text
response.oic.switchBranch
```

Supported branch values:

- `ALERT_TRIGGERED`
- `NO_ALERT`
- `INPUT_ERROR`
- `QUOTE_UNAVAILABLE`
- `PROVIDER_TIMEOUT`
- `SYSTEM_ERROR`

## Extracted Artifacts

Reusable contract artifacts are available under `artifacts/`:

| Path | Purpose |
|------|---------|
| `artifacts/openapi/oic-stock-alert.openapi.json` | OpenAPI 3.1 contract for the API. |
| `artifacts/json-schema/alert-evaluation-request.schema.json` | JSON Schema for evaluation requests. |
| `artifacts/json-schema/alert-evaluation-response.schema.json` | JSON Schema for success and error responses. |
| `artifacts/samples/*.json` | OIC-ready sample request and response payloads. |
| `artifacts/oic/oic-switch-branches.md` | Switch branch setup and field mappings. |

## Test

```sh
python3 -m unittest discover -s tests
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | API listen port. |
| `QUOTE_PROVIDER_MODE` | `mock` | `mock` or `live`. |
| `QUOTE_PROVIDER_NAME` | `mock` | Provider identifier for diagnostics. |
| `QUOTE_PROVIDER_API_KEY` | None | Reserved for live provider integration. |
| `QUOTE_PROVIDER_TIMEOUT_MS` | `1500` | Outbound provider timeout. |
| `ALLOW_REQUEST_PROVIDER_OVERRIDE` | `false` | Allows request `options.providerMode` override. |
| `LOG_LEVEL` | `info` | Runtime log level. |
