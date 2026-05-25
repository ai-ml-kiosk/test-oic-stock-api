# OIC Switch Branch Mapping

Use this extracted artifact when configuring the Oracle Integration Cloud Switch after the REST invoke to the OIC Stock Alert API.

## Switch Expression

Preferred expression:

```text
response.oic.switchBranch
```

If nested fields are awkward in the mapper, first assign:

```text
stockAlertSwitchBranch = response.oic.switchBranch
```

Then configure Switch conditions against `stockAlertSwitchBranch`.

## Branches

| Branch | Match Value | Retry | Notification | Purpose |
|--------|-------------|-------|--------------|---------|
| Alert Triggered | `ALERT_TRIGGERED` | No | Yes | Build and send alert notification. |
| No Alert | `NO_ALERT` | No | No | Log no-op and end successfully. |
| Input Error | `INPUT_ERROR` | No | No | Record invalid inbound payload or rule configuration. |
| Quote Unavailable | `QUOTE_UNAVAILABLE` | Usually no | No | Record business exception for missing market data. |
| Provider Timeout | `PROVIDER_TIMEOUT` | Yes | No | Route to retry or recoverable fault handling. |
| System Error | `SYSTEM_ERROR` | Yes | No | Route to technical fault handling and operations logging. |
| Otherwise | Unmatched | No | No | Treat as technical fault and include raw response diagnostics. |

## Alert Triggered Branch

Condition:

```text
stockAlertSwitchBranch = "ALERT_TRIGGERED"
```

Notification field mapping:

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

## Error Branch Mapping

| Error Branch | Primary Fields To Log |
|--------------|-----------------------|
| `INPUT_ERROR` | `requestId`, `symbol`, `error.code`, `error.details` |
| `QUOTE_UNAVAILABLE` | `requestId`, `symbol`, `error.code`, `error.message` |
| `PROVIDER_TIMEOUT` | `requestId`, `symbol`, `error.code`, `oic.retryRecommended` |
| `SYSTEM_ERROR` | `requestId`, `symbol`, `error.code`, `error.message` |

## Notes

- Preserve `requestId` across OIC retries.
- Prefer `oic.trackingId` when correlating back to an OIC integration instance.
- Do not include provider credentials or environment configuration in branch logging.
