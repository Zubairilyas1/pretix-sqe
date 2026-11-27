# Test Plan: pretix Ticket Capacity and Order Workflows

| Field | Value |
| :--- | :--- |
| Document | `src/tests/team/shared_management/TEST_PLAN.md` (living document; see change log at the end) |
| System under test | pretix (Community Edition), upstream `https://github.com/pretix/pretix` |
| Baseline commit | `c0d887738b6cd97f724b926718c55e2ae87c9901` (AGPL-3.0 with pretix additional terms) |
| Team repository | `https://github.com/Zubairilyas1/pretix-sqe` |
| Owners | Shared by Zubair (Area 1), Sami (Area 2), Tawassul (Area 3) |

## 1. Scope

### 1.1 Module and workflows
Module: event ticketing - products, quotas and orders (`pretix/base/models/items.py`, `pretix/base/services/quotas.py`, `pretix/base/models/orders.py`, `pretix/base/services/orders.py`, REST API `pretix/api/`, back office `pretix/control/`, shop `pretix/presale/`).

| Workflow | Starting condition | User action | Expected outcome |
| :--- | :--- | :--- | :--- |
| W1 Organizer sets up capacity | Event exists, organizer logged in (or API token with write permission) | Create a product and a quota of size N, or change N | Product and quota are stored; quota availability is `(OK, N)` |
| W2 Customer buys tickets | Product on sale, quota has free capacity | Put k tickets in the cart, check out, pay | Order is created (pending, then paid); quota availability falls by k; a request beyond the free capacity is rejected and nothing is written |

**Shared record:** `Quota` (`size`, and the availability derived from it). W1 writes `Quota.size`; W2 reads the availability and consumes it with cart positions and order positions. Cancelling or expiring an order, or an expired cart, gives capacity back.

### 1.2 Requirements and business rules
| ID | Requirement | Workflow |
| :--- | :--- | :--- |
| FR-01 | Organizer creates a product with price and sale window | W1 |
| FR-02 | Organizer creates a quota and links products to it | W1 |
| FR-03 | Organizer changes the quota size | W1 |
| FR-04 | Organizer controls the sale window (available from / until, active flag) | W1 |
| FR-05 | Customer reserves tickets in a cart (time-limited) | W2 |
| FR-06 | System creates an order from the cart | W2 |
| FR-07 | Customer redeems a voucher | W2 |
| FR-08 | Order moves through pending, paid, expired, canceled | W2 |

| Rule | Type required by the brief | Rule as implemented (source) |
| :--- | :--- | :--- |
| BR-1 Capacity limit | Boundary / limit | free = size - paid - pending - blocking vouchers - valid carts - waiting list; at free <= 0 the quota is sold out (`services/quotas.py` `_compute_*`) |
| BR-2 Purchasability | Decision with >= 2 Boolean conditions | `Item.is_available()` = active AND NOT(from set AND from > now) AND NOT(until set AND until < now), and the quota must have capacity |
| BR-3 Order state machine | Change of state | Allowed: n->p, n->e, n->c, p->c, e->p (if capacity), e->c, c->n (reactivate); payment of unapproved, canceled or (late payments off) expired orders is rejected (`Order._can_be_paid`, `services/orders.py`) |
| BR-4 Cart reservation | Domain rule (time limit) | A cart position holds capacity only while `expires >= now` (`_compute_carts`) |

**Roles:** Organizer (team member with all event permissions), Viewer (team member with read-only permission), Customer (anonymous shop user). Permissions are checked in the access matrix (`tawassul/security/rbac_access_matrix.md`).

**Test basis:** pretix documentation (`doc/`), REST API reference, and the source code at the baseline commit. Where behaviour is undocumented we record an assumption in the test file next to the test (for example: "BR-4 boundary: a cart that expires exactly now still counts, because the query uses `expires >= now`").

### 1.3 Out of scope
Payment provider plug-ins (Stripe, PayPal), e-mail delivery, PDF tickets, seating plans, the upstream test suite (earns no marks; it is not run or modified), production deployment on PostgreSQL.

## 2. Risk-based approach
Risks are scored on a 5x5 matrix (likelihood x impact, `RISK_REGISTER_5x5.md`). The score decides the technique and the depth.

| Risk level (score) | Techniques | Depth |
| :--- | :--- | :--- |
| High (10-25) | White-box unit tests with 100 % statement + branch coverage, MCC + MC/DC, state transition, 3-point BVA, mutation testing with custom operators, API EP/BVA, E2E use cases | Every condition combination, every boundary, read-back of the shared record after success and rejection; blocking CI gate |
| Medium (5-9) | EP + BVA, decision tables, security scans, accessibility scans | Every partition and boundary once; findings triaged and tracked |
| Low (1-4) | Smoke and review | Documented as residual risk |

## 3. Test levels, techniques and owners
| Level | Technique | Owner | Location |
| :--- | :--- | :--- | :--- |
| Static analysis | SonarQube, CFG + hand cyclomatic complexity | Zubair (CI gate), Tawassul (W1/W2 analysis, CFG) | `zubair/ci/`, `tawassul/static_analysis/` |
| Unit (white-box) | Statement/branch coverage, MCC, MC/DC, BVA, state transition | Zubair | `zubair/` |
| Mutation | Cosmic Ray + 2 custom operators | Zubair | `zubair/mutation/` |
| API + integration | EP, 3-point BVA from the OpenAPI generator, decision tables, state transition, idempotency, cross-workflow read-back | Sami | `sami/` |
| E2E (use cases) | Use case testing in Playwright | Tawassul | `tawassul/usecases/` |
| Usability / accessibility | Playwright task + keyboard tests, Lighthouse, axe-core | Tawassul | `tawassul/usability_a11y/` |
| Security | RBAC checks, OWASP ZAP passive, pip-audit | Tawassul | `tawassul/security/` |
| Performance + recovery | k6 OSS, failure/recovery test with a test double | Tawassul | `tawassul/performance/` |
| CI | GitHub Actions quality gate | Zubair | `.github/workflows/sqe_quality_gate.yml` |
| Test management | Plan, estimation, risk register, RTM, defects, RCA, Pareto, progress, completion report | Shared | `shared_management/` |

## 4. Environment
| Item | Version / value |
| :--- | :--- |
| OS (local) | Windows 11 Pro 10.0.26300; WSL Ubuntu 24.04 available |
| CI | GitHub Actions `ubuntu-latest` |
| Python / Django | 3.11.15 / 5.2.19 |
| Database | SQLite (pytest-django test database, recreated per test) |
| Cache | Redis is not required; Redis code paths are tested with `fakeredis` 2.40.0 |
| Test tools | pytest 9.2.0, pytest-django 4.14.0, pytest-cov 7.1.0, coverage.py 7.17.5, pytest-xdist 3.8.0 |
| Mutation | Cosmic Ray 8.9.0 + `sqe-mutation-operators` 1.0.0 (own plug-in) |
| Browser | Playwright 1.65.2 (pytest-playwright 0.10.0), Chromium |
| Accessibility | Lighthouse 12.8.2, axe-core via axe-playwright-python 0.1.9 |
| Security | OWASP ZAP 2.17.0 (passive), pip-audit |
| Performance | Grafana k6 OSS |
| Static analysis | SonarQube Community Build 25.1.0.102122, sonar-scanner-cli 11.1 |
| Node | 24.18.0 (Lighthouse) |

Installation, start, seed and reset commands are in the repository `README.md` ("Reproduce").

## 5. Test data
All data is synthetic and created by fixtures inside each test (`src/tests/team/conftest.py`: organizer `sqe-org`, event `sqe-conf`, product "General Admission Ticket", quota of 10). API tests use the generator output `sami/generator/test_data.json`. The k6 runs use `tawassul/performance/seed_perf_event.py`. **Reset:** pytest-django rolls back or recreates the test database for every test, so no manual reset is needed; the k6 seed script deletes and recreates its event before every run.

## 6. Schedule (planned vs actual)
| Phase | Planned | Actual |
| :--- | :--- | :--- |
| Selection, scope, registration | Week 1 | 23-25 Nov 2026 |
| Test design and automation (all areas) | Weeks 2-3 | 25-26 Nov 2026 |
| Mutation, CI gate, defect triage | Week 3 | 25-27 Nov 2026 |
| Rework after internal audit (Area 1 evidence replaced by real runs) | not planned | 27 Nov 2026 (deviation D-1, see completion report) |
| Completion report, package | Week 4 | 27 Nov 2026 onwards |

## 7. Criteria

### 7.1 Entry criteria (a test level may start when)
1. The baseline commit is checked out and `pip install -e ".[dev]"` succeeds.
2. The team fixtures pass the smoke test (`zubair/test_fixtures_smoke.py`).
3. The requirements and business rules of section 1.2 are reviewed by the owner of the level.
4. For API tests: the OpenAPI spec validates and every path resolves (`sami/openapi/test_openapi_spec.py`).
5. For E2E tests: Chromium is installed and `live_server` starts.

### 7.2 Exit criteria (measurable; EC-1 and EC-2 are tied to the highest risks)
| ID | Criterion | Target | Linked risks |
| :--- | :--- | :--- | :--- |
| EC-1 | Functional correctness of the capacity, purchasability and payment rules | 100 % statement and 100 % branch coverage on the business-rule scope (only documented infeasible branches allowed); 0 failing unit or API tests | PR-WB-01 (12), PR-WB-02 (10), PR-API-06 (12) |
| EC-2 | Strength of the tests on the critical module | Mutation score >= 85 % on `quotas.py` with Cosmic Ray including both custom operators; every surviving mutant classified | PR-WB-01 (12), PR-API-02 (12) |
| EC-3 | Performance of the order operation | p95 <= 500 ms and < 1 % unexpected failures at 1 and at 5 concurrent virtual users | PR-PERF-01 (12) |

### 7.3 Suspension criteria
Testing of a level is suspended when (a) the baseline or the unmutated suite fails (mutation baseline, smoke test), (b) the test environment is unusable (SQLite "database is locked" in more than 10 % of runs, live server does not start), (c) a blocking defect makes more than 30 % of the planned cases of the level unrunnable, or (d) more than 5 tests are flaky (pass and fail on the same commit).

### 7.4 Resumption criteria
Testing resumes when the cause is removed and verified: the smoke test and the baseline pass again, the blocking defect is fixed or worked around and tracked as a GitHub Issue, flaky tests are fixed or quarantined with an issue, and the test lead records the decision in the progress report.

## 8. Deliverables
Test plan (this file), risk register, estimation, RTM, defect log and GitHub Issues, RCA and Pareto, progress report, completion report, automated tests and reports in `src/tests/team/`, CI workflow, final PDF.

## 9. Project risks
See `RISK_REGISTER_5x5.md` section 4 (PJ-ENV-01, PJ-SCH-01, PJ-CI-01, PJ-INT-01).

## Change log
| Date | Change | By |
| :--- | :--- | :--- |
| 2026-11-25 | Scope, workflows, rules and roles agreed (previously only in README and RTM) | Team |
| 2026-11-27 | Plan written as one document; exit criteria made measurable and re-tied to the risk register; tool versions recorded; Area 1 schedule deviation added | Zubair |
