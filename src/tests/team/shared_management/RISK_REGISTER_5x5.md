# Risk Register (5x5) and Exit Criteria

**System:** pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`  
**Owners:** shared (Zubair, Sami, Tawassul). Last review: 2026-11-27.

## 1. Scoring
Score = Likelihood (1-5) x Impact (1-5).
Likelihood: 1 rare, 2 unlikely, 3 possible, 4 likely, 5 almost certain. Impact: 1 negligible, 2 minor, 3 moderate, 4 major, 5 critical.

| Level | Score | Technique and depth (decided by the level, see Test Plan section 2) |
| :--- | :--- | :--- |
| **High** | 10-25 | White-box 100 % statement + branch, MCC + MC/DC, state transition, 3-point BVA, mutation with custom operators, API EP/BVA with read-back, E2E; enforced by a blocking CI gate |
| **Medium** | 5-9 | EP + BVA or decision table once per partition, automated scan, finding triaged and tracked |
| **Low** | 1-4 | Review / smoke; documented as residual risk |

## 2. Matrix
| Likelihood \ Impact | 1 | 2 | 3 | 4 | 5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **5** | | | | | |
| **4** | | PR-API-05, PR-A11Y-02 (8) | PR-PERF-01, PR-A11Y-01, PJ-ENV-01 (12) | | PJ-INT-01 (20) |
| **3** | | PR-API-03, PR-API-07, PR-SEC-02 (6) | PR-WB-03, PR-CODE-01, PJ-SCH-01, PJ-CI-01 (9) | PR-WB-01, PR-API-01, PR-API-02, PR-API-06, PR-VAL-01 (12) | |
| **2** | | | PR-SEC-03, PR-SEC-04 (6) | PR-API-04, PR-SEC-01 (8) | PR-WB-02, PR-DATA-01 (10) |
| **1** | | | | | |

## 3. Product risks (21)
| ID | Owner | Risk | L | I | Score | Level | Technique and depth applied (evidence) |
| :--- | :--- | :--- | :-: | :-: | :-: | :-: | :--- |
| PR-WB-01 | Zubair | Capacity limit off by one (`<` vs `<=`, wrong counting of carts/vouchers/waiting list) lets a quota oversell or close too early | 3 | 4 | 12 | High | 100 % stmt+branch of `quotas.py`, 3-point BVA at size-1/size/size+1, MCC Q5/Q6, mutation (Cosmic Ray + `SwapAvailabilityVerdict`) - `zubair/test_quota_availability_whitebox.py`, `zubair/mutation/` |
| PR-WB-02 | Zubair | Order paid although it must not be (unapproved, canceled, expired with late payments off, last payment date over) | 2 | 5 | 10 | High | MCC O1 + branch coverage of `_can_be_paid`, state transition tests (8 allowed, 6 disallowed) through the real services, `SwapOrderStatus` operator - `zubair/test_whitebox_order_rules.py`, `test_order_state_transitions.py` |
| PR-WB-03 | Zubair | Availability served from the Redis cache is stale (sold out but shown as available) | 3 | 3 | 9 | Medium | Cache freshness MCC Q2 (fresh / stale / stale allowed), write lock, cache-miss tests with `fakeredis` |
| PR-API-01 | Sami | Negative item / cart / order-position price accepted by the REST API | 3 | 4 | 12 | High | Generator BVA `min-1` on every price input incl. array items; W-01, W-02, W-09 (strict xfail) |
| PR-API-02 | Sami | Retry without idempotency key creates a duplicate order | 3 | 4 | 12 | High | Repeated-request tests; W-03 characterisation test |
| PR-API-03 | Sami | Empty or over-long item name accepted | 3 | 2 | 6 | Medium | String-length BVA; W-04 |
| PR-API-04 | Sami | Quota size above 32-bit range accepted (crash on PostgreSQL) | 2 | 4 | 8 | Medium | BVA `max+1`; W-05 |
| PR-API-05 | Sami | `with_availability` ignored on the quota detail endpoint | 4 | 2 | 8 | Medium | Detail vs list test; W-06 |
| PR-API-06 | Sami | Order API ignores sale window and per-order limits | 3 | 4 | 12 | High | Rule tests; W-07, W-08 |
| PR-API-07 | Sami | Order state actions accept an invalid body and act on it (`send_email` by truthiness) | 3 | 2 | 6 | Medium | Generator EP on the action body; W-12 |
| PR-SEC-01 | Tawassul | Vulnerable dependency `oauthlib 3.3.1` | 2 | 4 | 8 | Medium | pip-audit; A3-D04 |
| PR-SEC-02 | Tawassul | Missing `X-Content-Type-Options` / `Referrer-Policy` | 3 | 2 | 6 | Medium | Header tests + ZAP; A3-D02 |
| PR-SEC-03 | Tawassul | End-of-life Bootstrap 3.4.1 with XSS advisories | 2 | 3 | 6 | Medium | ZAP 10003; A3-D05 |
| PR-SEC-04 | Tawassul | CSP without `frame-ancestors`; cookies without SameSite over HTTP (accepted by design for the widget) | 2 | 3 | 6 | Medium | ZAP 10055/10054 triage against source; clickjacking test |
| PR-A11Y-01 | Tawassul | Back office unusable with a screen reader (lang, alt, link names) | 4 | 3 | 12 | High | axe + Lighthouse before/after, keyboard test; A3-D03 fixed |
| PR-A11Y-02 | Tawassul | Low colour contrast and unnamed select2 combobox in the product form | 4 | 2 | 8 | Medium | axe findings F4/F5 (open) |
| PR-CODE-01 | Tawassul | Add-on price correction is a self-assignment (dead code) | 3 | 3 | 9 | Medium | SonarQube S1656; A3-D06 |
| PR-PERF-01 | Tawassul | Order creation misses p95 <= 500 ms / < 1 % errors at 5 users | 4 | 3 | 12 | High | k6 1 VU and 5 VUs, 2 runs each |
| PR-DATA-01 | Tawassul | Failure during order creation leaves partial data or lost capacity | 2 | 5 | 10 | High | Failure/recovery test with a test double |
| PR-VAL-01 | Tawassul | Back office saves a negative price | 3 | 4 | 12 | High | Playwright exception flow; A3-D01 |

## 4. Project risks (4)
| ID | Risk | L | I | Score | Level | Mitigation / status |
| :--- | :--- | :-: | :-: | :-: | :-: | :--- |
| PJ-ENV-01 | Windows + SQLite behave differently from Linux + PostgreSQL (locks, file handles) | 4 | 3 | 12 | High | CI runs on Linux; SQLite lock retries in Area 3 fixtures; PostgreSQL-only branch covered with a registered SQL function |
| PJ-SCH-01 | Member branches integrated late, causing conflicts | 3 | 3 | 9 | Medium | One folder per member, PR per area, shared fixtures in `tests/team/conftest.py` |
| PJ-CI-01 | Long-running gates (mutation about 60 min locally) slow down pull requests | 3 | 3 | 9 | Medium | Mutation runs in parallel workers; job time limits; gates independent so failures are visible early |
| PJ-INT-01 | AI-generated content accepted without verification (claims, numbers or screenshots not produced by real runs) | 4 | 5 | 20 | High | **Materialised on 27 Nov 2026** in Area 1 (hard-coded mutation numbers, drawn terminal images, undocumented defects). Corrective: all removed, results re-produced by real runs, reports rebuilt from tool output. Preventive: every number in a report must point to a committed raw output; AI-use record lists what was checked |

## 5. Exit criteria
Defined in the Test Plan section 7.2. Actual vs target is reported in `TEST_COMPLETION_REPORT.md`.

| ID | Target | Highest risks covered |
| :--- | :--- | :--- |
| EC-1 | 100 % statement + branch coverage on the business-rule scope, 0 failing unit/API tests | PR-WB-01, PR-WB-02, PR-API-06 |
| EC-2 | Mutation score >= 85 % on `quotas.py` (incl. both custom operators), all survivors classified | PR-WB-01, PR-API-02 |
| EC-3 | `POST orders/`: 1 user p95 <= 500 ms, 5 users p95 <= 1000 ms, < 1 % unexpected failures | PR-PERF-01 |
