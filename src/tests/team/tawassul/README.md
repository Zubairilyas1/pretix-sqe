# Area 3: Use Cases, Usability, Accessibility, Security, Performance (Tawassul)

Plan: `docs/sqe/TAWASSUL_MASTER_EXECUTION_PLAN.md`. Every test runs against a **real pretix server** (pytest-django `live_server`) in **Chromium** (Playwright), and checks both the UI and the database.

| Folder | Brief task | Main files | Result |
| :--- | :--- | :--- | :--- |
| `usecases/` | 3.1 Use cases + Playwright E2E | `use_case_spec.md` (UC-1..6, each with 2 alternative + 2 exception flows), `test_e2e_usecases.py` (30) | 29 pass, 1 strict xfail (**A3-D01**) |
| `usability_a11y/` | 3.2 Keyboard, Lighthouse, axe, screen fix | `test_keyboard_nav.py` (3), `test_axe_scan.py` (6), `lighthouse_run.py`, `a11y_findings.md`, `screen_remediation/`, `reports/` | Organizer page Lighthouse **81 → 93**; 3 WCAG A rules fixed (**A3-D03**) |
| `security/` | 3.3 RBAC, ZAP, pip-audit | `rbac_access_matrix.md`, `test_rbac_decisions.py` (10), `test_security_headers.py`, `zap_scan.py`, `zap_passive_scan_report.md`, `dependency_audit_pip.md`, `evidence/` | **A3-D02** headers, **A3-D04** oauthlib CVE (8.5), **A3-D05** Bootstrap 3 |
| `performance/` | 3.4 k6 + failure recovery | `k6_workload.js`, `k6_metrics_report.md`, `results/`, `test_failure_recovery.py` (2), `seed_perf_event.py`, `perf_server.py` | 1 VU meets the SLA (p95 ≈ 435 ms); 5 VUs fail it (p95 ≈ 1.5 s, 24 % errors). Recovery: no partial data. |
| `static_analysis/` | Static analysis + CFG | `sonar_findings.md`, `cfg_cyclomatic.md` (V(G) = 6, three ways), `test_cfg_paths.py` (5), `sonar_scan.py` | SonarQube gate passed, 3 bugs = **A3-D06**; 5 feasible basis paths, 100 % edge coverage |
| (root) | Shared management | `SHARED_MANAGEMENT_ROWS.md` (risks, RTM, defects, estimates) | rows for the team documents |

## Defects found
| ID | Defect | Severity | Evidence |
| :--- | :--- | :-: | :--- |
| A3-D01 | Back office saves a negative item price | Major | `test_uc1_exc_negative_price_rejected_in_backoffice` (xfail) |
| A3-D02 | `X-Content-Type-Options` and `Referrer-Policy` not sent | Minor | `test_no_mime_sniffing`, `test_referrer_policy_*` (xfail), ZAP 10021 |
| A3-D03 | Back-office layout fails WCAG 2.1 A (lang, image alt, link names): **fixed** | Major | axe and Lighthouse before/after |
| A3-D04 | `oauthlib 3.3.1`: CVE-2026-49272 (high, 8.5), CVE-2026-49265 | Major | `dependency_audit_pip.md` |
| A3-D05 | Bootstrap 3.4.1 end-of-life with 2 unpatched XSS advisories | Minor | ZAP 10003 |
| A3-D06 | Add-on price correction in the cart is a no-op (`cart.py:1056-1066`) | Major | SonarQube, verified in source |

## Run
```bash
cd src
../.venv/Scripts/python -m playwright install chromium          # once
../.venv/Scripts/python -m pytest tests/team/tawassul -v         # all Area 3 tests (~12 min)
../.venv/Scripts/python -m pytest tests/team/tawassul/usecases -k uc3 --headed   # watch a use case
```
The tools that need a running server (k6, ZAP, Lighthouse, SonarQube) are described in each report's "How to reproduce" section.
