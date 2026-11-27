# Area 3 (Tawassul): rows for the shared test-management documents

These rows are Area 3's input to the team files in `tests/team/shared_management/`
(risk register, RTM, defect log, estimation). They are kept here until the team
merges them into the shared tables.

## 1. Risk register (5×5: likelihood × impact, 1–5)

| ID | Type | Risk | L | I | Score | Evidence | Mitigation / test |
| :--- | :-: | :--- | :-: | :-: | :-: | :--- | :--- |
| PR-SEC-01 | Product | Known CVEs in `oauthlib 3.3.1` (CVE-2026-49272 high 8.5, CVE-2026-49265 medium 6.8) | 2 | 4 | 8 | `security/dependency_audit_pip.md` | upgrade to oauthlib ≥ 4.0.1; add device-grant rejection test |
| PR-SEC-02 | Product | Order secret leaks via `Referer` and responses are MIME-sniffable (no `Referrer-Policy`, no `nosniff`) | 3 | 2 | 6 | A3-D02, `zap_passive_scan_report.md` | send both headers (Django `SecurityMiddleware` or nginx `add_header`) |
| PR-SEC-03 | Product | End-of-life Bootstrap 3.4.1 with unpatched XSS advisories (A3-D05) | 2 | 3 | 6 | `zap_passive_scan_report.md` | migrate to Bootstrap 5; audit `data-*` and popover inputs |
| PR-A11Y-01 | Product | Organizer back office not usable with screen readers (missing lang, image alt, link names) | 4 | 3 | 12 | axe: 5 rules / 11 elements | template fix in `screen_remediation/`; axe regression test |
| PR-CODE-01 | Product | Cart keeps stale add-on prices because the correction code is a no-op (A3-D06) | 3 | 3 | 9 | `static_analysis/sonar_findings.md` | fix the assignments; white-box test via CartManager |
| PR-PERF-01 | Product | Checkout API misses the p95 ≤ 500 ms SLA at 5 VUs (p95 ≈ 1.5 s, 24 % errors from database write locks, returned as HTTP 500) | 4 | 3 | 12 | `performance/k6_metrics_report.md` | re-measure on PostgreSQL; return 503 with `Retry-After` on lock timeouts |
| PR-DATA-01 | Product | A database failure mid-checkout leaves partial orders or lost seats | 2 | 5 | 10 | `test_failure_recovery.py` (passes) | keep the test in CI; transaction atomicity verified |
| PR-VAL-01 | Product | Back office accepts a negative item price (A3-D01, same root cause as W-01) | 3 | 4 | 12 | `test_uc1_exc_negative_price_rejected_in_backoffice` | `MinValueValidator(0)` on `Item.default_price` |
| PJ-ENV-01 | Project | Tools differ from production (Windows, SQLite, waitress instead of Linux, PostgreSQL, gunicorn) | 4 | 3 | 12 | `perf_server.py`, `patch_manifest_windows.py` | state as a threat to validity; repeat k6 on Linux if time allows |

## 2. Requirements traceability (Area 3 rows)

| Requirement / rule | Use case | Test file → tests |
| :--- | :--- | :--- |
| FR: organizer creates item and quota (W1) | UC-1 | `usecases/test_e2e_usecases.py` → `test_uc1_*` (5) |
| FR: organizer controls when sales are open; R2 | UC-2 | `test_uc2_*` (5) |
| FR: customer checkout (W2); R1, R3 | UC-3 | `test_uc3_*` (5), `test_keyboard_nav.py` |
| FR: vouchers; R4 | UC-4 | `test_uc4_*` (5) |
| R1 shared record never oversold | UC-5 | `test_uc5_*` (5), `static_analysis/test_cfg_paths.py` (5) |
| R3 pending order can be cancelled, seats released | UC-6 | `test_uc6_*` (5) |
| NFR usability / WCAG 2.1 AA | UC-1, UC-3 | `test_keyboard_nav.py` (3), `test_axe_scan.py` (3+), Lighthouse reports |
| NFR security: access control | all | `security/test_rbac_decisions.py` (10) |
| NFR security: headers, cookies | all | `security/test_security_headers.py` (9), `zap_passive_scan_report.md` |
| NFR security: dependencies | — | `dependency_audit_pip.md` |
| NFR performance: p95 ≤ 500 ms, errors < 1 % | UC-3 | `performance/k6_workload.js`, `k6_metrics_report.md` |
| NFR reliability: recover from DB failure | UC-3 | `performance/test_failure_recovery.py` (2) |

## 3. Defects (to be filed as GitHub Issues)

| ID | Title | Severity | Found by |
| :--- | :--- | :-: | :--- |
| A3-D01 | Back office saves a negative item price | Major | Playwright UC-1 E1 |
| A3-D02 | `X-Content-Type-Options` and `Referrer-Policy` headers missing | Minor | header test + ZAP |
| A3-D03 | Organizer pages fail WCAG 2.1 A (lang, image alt, link names) | Major | axe-core, Lighthouse |
| A3-D04 | `oauthlib` 3.3.1 with known high CVE | Major | pip-audit |
| A3-D06 | Add-on price correction in `cart.py:1056-1066` is a no-op (self-assignments, duplicated `update_fields`) | Major | SonarQube S1656, verified in source |
| A3-D05 | Bootstrap 3.4.1 (end-of-life) with two unpatched XSS advisories (CVE-2024-6485, CVE-2025-1647) | Minor | ZAP rule 10003 |

## 4. Three-point estimate vs actual (hours)

E = (O + 4M + P) / 6

| Task | O | M | P | E | Actual |
| :--- | :-: | :-: | :-: | :-: | :-: |
| Environment (Playwright, Docker images, perf instance) | 1 | 2 | 5 | 2.3 | 3 |
| Use case specification | 2 | 3 | 5 | 3.2 | 2 |
| Playwright E2E for 30 flows | 5 | 8 | 14 | 8.5 | 7 |
| Keyboard + axe + Lighthouse + screen fix | 3 | 5 | 8 | 5.2 | 4 |
| RBAC + headers + ZAP + pip-audit | 3 | 5 | 8 | 5.2 | 4 |
| k6 (4 runs) + failure recovery | 3 | 5 | 9 | 5.3 | 4 |
| SonarQube + CFG hand calculation | 2 | 3 | 6 | 3.3 | 3 |
| Reports, screenshots, PR | 2 | 3 | 5 | 3.2 | 3 |
| **Total** | **21** | **34** | **60** | **36.2** | **30** |

Actual hours were recorded from the work session on 2026-11-26. The environment took longer than estimated because of Windows-specific deployment issues (static manifest paths, no gunicorn).
