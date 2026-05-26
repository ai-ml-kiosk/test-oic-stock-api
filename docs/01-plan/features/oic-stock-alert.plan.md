# oic-stock-alert - Plan Document

> Version: 1.0.0 | Date: 2026-05-25 | Status: Complete
> Level: Starter

---

## 1. Overview

### 1.1 Purpose

Plan the OIC Stock Alert application: a small API-centered service that supports stock watch configuration, retrieves market quote data, evaluates alert thresholds, and exposes results in a form suitable for Oracle Integration Cloud (OIC) orchestration or downstream notification flows.

### 1.2 Background

This repository is currently empty and has been initialized as a Starter-level BKit project. The requested blueprint was not found in the local workspace or by exact Confluence search, so this plan records the working assumptions for the OIC Stock Alert blueprint and keeps them visible for validation in the design phase.

The application is assumed to demonstrate a cloud-native OIC integration pattern:

- OIC or an OIC-triggered integration calls a stock alert API.
- The API retrieves current quote data from a configurable provider.
- The API compares quote values against user-defined alert rules.
- The API returns deterministic alert decisions and diagnostics for OIC to route to notification channels.

## 2. Goals

### 2.1 Primary Goals

- [x] Define a clear MVP scope for the OIC Stock Alert API.
- [x] Establish the functional requirements needed for watchlists, quote retrieval, threshold evaluation, and alert response payloads.
- [x] Identify non-functional expectations for reliability, observability, security, and OIC-friendly integration behavior.
- [x] Create PDCA planning artifacts that allow design and implementation to proceed in small, verifiable steps.

### 2.2 Non-Goals

- This phase will not implement the API, UI, database, deployment pipeline, or OIC integration flow.
- The MVP will not provide financial advice, trading actions, portfolio management, or broker integration.
- The MVP will not guarantee real-time market data unless a selected quote provider explicitly supports it.
- The MVP will not include multi-tenant enterprise administration unless confirmed in the design phase.

## 3. Scope

### 3.1 In Scope

- Define an HTTP API for OIC-friendly stock alert operations.
- Support stock symbols, threshold direction, threshold price, and alert status.
- Retrieve quote data from a configurable provider or mock provider for local development.
- Add an MVP milestone for live market data orchestration through an outbound REST quote provider while maintaining the local mock provider path as a runtime toggle.
- Evaluate alert rules for conditions such as price above, price below, and percentage change.
- Return structured JSON responses that include quote data, alert match status, and error details.
- Provide health and readiness endpoints.
- Support OIC-compatible HTTPS exposure through an external TLS termination layer such as OCI API Gateway, OCI Load Balancer, or a reverse proxy while the application server remains HTTP-only on its internal port.
- Define the preferred ingress/proxy pattern for OIC readiness: OCI API Gateway over HTTPS `443` forwarding to the private HTTP application on `8080`, with Nginx or Caddy as VM-hosted alternatives.
- Include configuration for provider API keys through environment variables and untracked local `.env` files.
- Provide local developer setup and verification instructions.
- Define basic tests for rule evaluation and API response contracts.

### 3.2 Out of Scope

- Production OIC flow creation and deployment.
- User authentication and role-based access control for the first MVP.
- Persistent user accounts and complex watchlist ownership.
- Advanced technical indicators, market history analytics, and backtesting.
- SMS, email, Slack, or push notification delivery inside this API unless the design phase confirms it as required.
- Paid market data provider procurement or subscription management.

## 4. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | The API must expose a health endpoint for runtime checks. | Must |
| FR-002 | The API must accept a stock symbol and alert rule input. | Must |
| FR-003 | The API must retrieve or simulate current quote data for a symbol. | Must |
| FR-004 | The API must evaluate whether the current quote satisfies the alert rule. | Must |
| FR-005 | The API must return an OIC-friendly JSON response with status, symbol, quote, rule, triggered flag, and message. | Must |
| FR-006 | The API must handle invalid symbols, invalid thresholds, provider failures, and timeouts with explicit error responses. | Must |
| FR-007 | The API should support a mock quote provider for local and CI verification. | Should |
| FR-008 | The API should expose enough metadata for OIC troubleshooting, such as request ID and provider mode. | Should |
| FR-009 | The API must support decoupled, zero-trust credential parsing through an untracked local `.env` file for sensitive provider settings. | Must |
| FR-010 | The API must support outbound connection mapping to Alpha Vantage's `GLOBAL_QUOTE` endpoint for live quote retrieval. | Must |

## 5. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Reliability | Quote provider failures must fail gracefully with clear status codes and messages. |
| Security | Secrets must be read from environment variables or untracked local `.env` files and never committed. |
| Security | OIC-facing REST invokes must use HTTPS through external TLS termination; the Python application server must not be exposed directly to the public internet without gateway, load balancer, reverse proxy, firewall, and certificate controls. |
| Observability | Requests, provider calls, and alert decisions should be logged without exposing secrets. |
| Performance | A single alert evaluation should complete within 2 seconds in normal provider conditions, and live mode must adhere to configured timeout limits with a default of 1500 ms. |
| Testability | Rule evaluation must be testable without external network calls. |
| Maintainability | Provider access, alert rules, and API routes should be separated enough to keep future changes small. |
| Integration | Responses should use stable JSON fields and predictable HTTP status codes for OIC mappings; upstream Alpha Vantage rate-limit and invalid-symbol payloads must map cleanly into downstream OIC exception branches. |

## 6. Success Criteria

- [x] Plan document exists at `docs/01-plan/features/oic-stock-alert.plan.md`.
- [ ] Design document defines architecture, data model, API contract, error contract, and test plan.
- [ ] Implementation provides local run instructions and a working API service.
- [ ] Health endpoint returns a successful response locally.
- [ ] Alert evaluation endpoint supports at least one positive and one negative threshold scenario.
- [ ] Mock provider mode works without external network access.
- [ ] Automated or command-based verification covers rule evaluation, invalid input, and provider failure behavior.
- [ ] No API keys, credentials, or generated secrets are committed.

## 7. Schedule

| Phase | Target Date | Status |
|-------|-------------|--------|
| Plan | 2026-05-25 | Complete |
| Design | 2026-05-25 | Pending |
| Implementation | 2026-05-25 | Pending |
| Check | 2026-05-25 | Pending |
| Report | 2026-05-25 | Pending |

## 8. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Original blueprint details are not available in this workspace. | Medium | High | Document assumptions in this plan and validate them during design. |
| Market data provider limits, authentication, or pricing may block live quote tests. | High | Medium | Use a provider abstraction and mock provider as the default verification path. |
| OIC payload mapping may require stricter schemas than a generic REST API. | Medium | Medium | Define explicit request and response examples in the design document. |
| External API latency may make OIC flows unreliable. | Medium | Medium | Set timeouts, surface retryable failures, and keep the alert endpoint stateless. |
| Stock symbol validation rules vary by exchange/provider. | Medium | Medium | Start with conservative symbol validation and provider-specific error mapping. |

## 9. Architecture Considerations

- Keep the MVP stateless unless persistence is confirmed during design.
- Separate API handlers from alert evaluation logic.
- Define a quote provider interface with mock and live implementations.
- Route Alpha Vantage `GLOBAL_QUOTE` payloads through the live provider path without changing the OIC-facing response contract.
- Prefer JSON contracts that are easy for OIC integrations to map.
- Use an HTTPS ingress boundary for OIC invokes: `OIC -> HTTPS Gateway/LB/Proxy -> HTTP service:8080`.
- Prefer OCI API Gateway for production OIC invokes; use Nginx or Caddy only when deploying the service directly on a VM or lightweight host.
- Use environment-based and untracked `.env` configuration for provider mode, API keys, timeout, and log level.
- Enforce the configured live provider timeout, defaulting to 1500 ms, and map upstream rate-limit, invalid-symbol, timeout, and provider-error outcomes into existing OIC exception branches.
- Include request IDs in logs and responses to support OIC troubleshooting.

## 9.1 Deliverables Checklist

- [x] MVP plan document
- [x] Mock quote provider path
- [x] OIC-friendly response contract
- [ ] `.env.example` template
- [ ] Alpha Vantage live provider module logic
- [ ] HTTPS ingress/proxy deployment guide with `443 -> 8080` forwarding and smoke-test commands

## 10. Convention Prerequisites

- Choose the implementation stack during design based on repository needs and OIC integration fit.
- Define naming conventions for routes, request models, response models, errors, and tests.
- Establish local run, test, and lint commands before implementation.
- Add a `.gitignore` before any generated files or local secrets are introduced.

## 11. References

- BKit PDCA skill: `$pdca plan`
- Project workspace: `test-oic-stock-api`
- GitHub repository: `https://github.com/ai-ml-kiosk/test-oic-stock-api`
- Source blueprint status: not found locally or by exact Confluence search; assumptions captured above.
