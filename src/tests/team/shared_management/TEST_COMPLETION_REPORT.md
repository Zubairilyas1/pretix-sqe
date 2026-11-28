# Test Completion Report

**System:** pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901` - workflows W1 (capacity set-up) and W2 (ticket purchase).
**Date:** 2026-11-27. **Plan:** `TEST_PLAN.md`. **Progress:** `PROGRESS_REPORTS.md`.

## 1. Recommendation: **HOLD**
The capacity, purchasability and payment rules are verified to the planned depth (EC-1 and EC-2 met), but the order
operation fails the performance criterion at 5 concurrent users (EC-3 not met: about 72 % of orders fail with
HTTP 500 "database is locked") and seven P1 defects are open, on the highest risks PR-API-01, PR-API-06, PR-VAL-01
and PR-SEC-01. Release once the P1 defects are fixed and
EC-3 is re-measured on the production database (PostgreSQL).

## 2. Exit criteria: actual vs target
| ID | Criterion | Target | Actual | Met? | Evidence |
| :--- | :--- | :--- | :--- | :-: | :--- |
| EC-1 | Business-rule coverage; failing unit/API tests | 100 % statement + branch on scope (documented infeasible branches only); 0 failing | `quotas.py` 239/239 statements, 143/144 branches (1 infeasible, justified); `is_available`, `is_available_by_time`, `_can_be_paid` 100 %/100 %; Area 1: 218 passed; Area 2: 490 passed + 30 strict xfail (tracked defects W-01..W-12), 0 failed | **Yes** | `docs/sqe/zubair/COVERAGE_REPORT.md`, `evidence/` |
| EC-2 | Mutation score on `quotas.py` incl. 2 custom operators | >= 85 % and every survivor classified | Run 1: 650/715 = 90.91 %; run 2 (after new tests): 692/715 = 96.78 %; all 65 run-1 survivors classified (23 equivalent, 42 killed) | **Yes** | `docs/sqe/zubair/MUTATION_REPORT.md`, `zubair/mutation/results/` |
| EC-3 | `POST orders/` performance (limits fixed before the run) | 1 user: p95 <= 500 ms; 5 users: p95 <= 1000 ms; < 1 % unexpected failures | 1 user: p95 133 / 129 ms, 0 % / 0 % (met); 5 users: p95 492 / 527 ms (met) but **72.85 % / 71.99 % failures** (HTTP 500, SQLite "database is locked") | **No** | `tawassul/performance/k6_metrics_report.md` section 7, `results_v2/` |

## 3. What was tested / not tested
| Tested | Level | Result |
| :--- | :--- | :--- |
| BR-1 capacity limit, BR-4 cart expiry (`QuotaAvailability`) | Unit, MCC/MC-DC, BVA, mutation | Pass |
| BR-2 purchasability | Unit MCC (18 feasible rows), BVA; API rule 2; UC-2 | Pass at unit level; API defect W-07 |
| BR-3 order state machine | Unit state transitions via services, MCC O1; API transitions; UC-6 | Pass |
| REST API items/quotas/carts/orders | EP + 3-point BVA from the OpenAPI generator on every body field, array item and path/query/header parameter; every documented status code; decision tables; idempotency; cross-workflow read-back | 490 pass, 30 strict xfail = 12 weaknesses |
| Use cases UC-1..UC-6 (30 flows) | Playwright E2E with DB postconditions | 29 pass, 1 strict xfail (A3-D01) |
| Full Area 3 suite (68 tests, Playwright HTML report) | Playwright, axe, RBAC, headers, recovery, CFG paths | 63 pass, 4 strict xfail, 1 transient SQLite-lock failure; that file re-run 3 x: 10/10 (`tawassul/README.md`) |
| Usability tasks W1 + W2 | Playwright task tests incl. reject-then-correct and a W1 keyboard-only form | 3 pass |
| Accessibility / SEO on every use-case screen | Lighthouse (accessibility, best practices, SEO) + axe, de-duplicated | 3 open a11y findings (organizer screens), missing meta description |
| Accessibility, security, performance, recovery | axe, Lighthouse, RBAC tests, ZAP passive, pip-audit, k6, failure/recovery test | See Area 3 reports |

| Not tested (and why) |
| :--- |
| PostgreSQL behaviour (W-05 500 error, EC-3 lock errors) - local and CI runs use SQLite |
| Payment provider plug-ins, e-mails, PDF tickets, seating - out of scope (Test Plan 1.3) |
| Voucher redemption (FR-07) through the REST API - covered only by unit and E2E tests |

## 4. Deviations from the plan
| # | Deviation | Effect |
| :-: | :--- | :--- |
| DV-1 | Area 1 evidence of 25-26 Nov (coverage, MCC, mutation, CI PR) was not valid and was redone on 27 Nov | One extra day of Area 1 work; reports rebuilt from real tool output; risk PJ-INT-01 |
| DV-2 | Defects were tracked only as strict xfail until 27 Nov; GitHub Issues #16-#34 were created on 28 Nov | Reopen rate could only be measured from 27 Nov |
| DV-3 | All work in one calendar week instead of four | One weekly report with daily checkpoints |
| DV-5 | The Area 2 and Area 3 gaps found by the audit were closed by Zubair on 27 Nov on the `zubair` branch, at the team's request (AI-use rows 20-21) | Those commits carry Zubair's name; Sami and Tawassul reviewed and must be able to explain them |
| DV-4 | Mutation testing uses Cosmic Ray (listed in the brief) instead of mutmut, because mutmut 3 does not run natively on Windows and has no plug-in mechanism for custom operators | Custom operators are real Cosmic Ray plug-ins |

## 5. Open defects (detail: `CONSOLIDATED_DEFECT_LOG.md`)
| Priority | Defects |
| :--- | :--- |
| P1 | W-01, W-02, W-07, W-08, W-09, A3-D01, A3-D04 |
| P2 | W-03, W-05, W-12, A3-D02, A3-D06 |
| P3 | W-04, W-06, W-10, W-11, A3-D05 |
| Closed | A3-D03 (fixed, issue #27 closed); D-Z01 (fixed by pull request #36: regression test red, fix green, merged 28 Nov; issue #16 closed) |

## 6. Residual risk per risk
| Risk | Score before | Residual | Reason |
| :--- | :-: | :--- | :--- |
| PR-WB-01 capacity off by one | 12 | **Low** | 100 % stmt/branch, BVA at size-1/size/size+1, mutation >= 85 % incl. verdict operator, D-Z01 fixed (PR #36) |
| PR-WB-02 order paid when it must not be | 10 | **Low** | MCC O1, all `_can_be_paid` branches, 14 state-transition tests, all `SwapOrderStatus` mutants killed |
| PR-WB-03 stale cache | 9 | **Low** | cache age BVA (119/120/121 s), TTL and lock tests |
| PR-API-01 negative price via API | 12 | **High** | W-01, W-02, W-09 open |
| PR-API-02 duplicate order on retry | 12 | **Medium** | works with idempotency key; W-03 accepted for trusted clients |
| PR-API-03 item name validation | 6 | Medium | W-04 open |
| PR-API-04 quota size overflow | 8 | Medium | W-05 open, not verified on PostgreSQL |
| PR-API-05 detail availability | 8 | Low | workaround endpoint used and documented |
| PR-API-06 API bypasses rules | 12 | **High** | W-07/W-08 open (decision tables DT-1/DT-2 confirm) |
| PR-API-07 order action body not validated | 6 | Medium | W-12 open |
| PR-SEC-01 vulnerable dependency | 8 | Medium | upgrade pending |
| PR-SEC-02 missing headers | 6 | Medium | config fix pending |
| PR-SEC-03 Bootstrap EOL | 6 | Low | CSP mitigates |
| PR-SEC-04 CSP / SameSite / framing | 6 | Low | accepted by design for the widget; order pages frameable (ZAP 10020), cancel needs a confirmed CSRF POST |
| PR-A11Y-01 back office a11y | 12 | **Low** | fixed and verified (Lighthouse 81 -> 93) |
| PR-A11Y-02 contrast / select2 | 8 | Medium | open |
| PR-CODE-01 dead price correction | 9 | Medium | open upstream |
| PR-PERF-01 performance | 12 | **High** | EC-3 failed at 5 users (72 % HTTP 500) |
| PR-DATA-01 partial data on failure | 10 | Low | recovery test passes, no partial data under load |
| PR-VAL-01 negative price in back office | 12 | **High** | A3-D01 open |

## 7. Metrics at completion (GQM)
| Metric | Value |
| :--- | :--- |
| Defect density | 19 confirmed defects / 8.11 KLOC = **2.34 per KLOC** |
| Requirements coverage | 8/8 = **100 %** (7/8 at all three levels) |
| Reopen rate | 0 reopened / 2 closed = **0 %** (A3-D03, D-Z01) |
| Estimation | see `PROJECT_ESTIMATION_PERT.md` (actual vs expected) |
