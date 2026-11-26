# SE3002 SQE: Tawassul's Master Execution Plan (Area 3)

**Owner:** Tawassul (Member 3). Tawassul does the work, commits it from his own GitHub account (`tawassulAkbr`) and defends it in the viva.
**Plan drafted by:** Sami with Claude Code on 2026-11-26, to be disclosed as an AI-use row.
**Baseline:** pretix `c0d887738b6cd97f724b926718c55e2ae87c9901`
**Workflows:** W1 organizer creates item and quota; W2 customer buys. The shared record is `Quota`.
**Folder:** everything goes under `src/tests/team/tawassul/` (upstream tests earn 0 marks).

---

## 0. Decisions that make Area 3 achievable on one laptop

| Decision | Why |
| :--- | :--- |
| Write the E2E, keyboard and RBAC tests in **Python Playwright with pytest** (`pytest-playwright` is already installed in `.venv`), not TypeScript. The brief allows either language. | Tests can use pytest-django's `live_server` (a real pretix server per test run) and the ORM. Asserting **database state** next to the UI then takes one line, and the team's shared fixtures (`team_organizer`, `team_event`, `team_item`, `team_quota`) can be reused. |
| Run **SonarQube, OWASP ZAP and k6 in Docker** (Docker Desktop is installed). | No Java or k6 install is needed: `sonarqube:community`, `zaproxy/zap-stable`, `grafana/k6`. |
| Run **Lighthouse with `npx lighthouse`** and axe through **`axe-playwright-python`**. | Node 24 is installed, and the axe scan then lives inside the same pytest suite. |
| For performance and ZAP, use **one long-running pretix dev server** (`python manage.py runserver`) with a seeded event, not the test server. | k6 and ZAP need a stable URL; the data is reset by a seed command so runs repeat from identical data (a brief requirement). |

Real routes used (from `src/pretix/presale/urls.py` and `control/urls.py`):

- Shop: `/{org}/{event}/`
- Cart: `/{org}/{event}/cart/add`
- Vouchers: `/{org}/{event}/redeem`
- Checkout: `/{org}/{event}/checkout/start`, then `/{org}/{event}/checkout/{step}/`
- Customer order: `/{org}/{event}/order/{code}/{secret}/`, with `/cancel` appended to cancel
- Back office: `/control/`, `/control/event/{org}/{event}/items/`, `/control/event/{org}/{event}/quotas/`

---

## 1. Task 3.0: Static analysis and cyclomatic complexity

**Folder:** `static_analysis/` | **Branch:** `tawassul/feat-static-cfg`

1. Start SonarQube with `docker run -d -p 9000:9000 sonarqube:community`, then run `sonarsource/sonar-scanner-cli` on the files of the two workflows. Scope:
   - `pretix/base/services/cart.py`
   - `pretix/base/services/orders.py`
   - `pretix/base/models/items.py`
   - `pretix/control/views/item.py`
2. Report in `sonarqube_metrics.md`: bugs, vulnerabilities, code smells, duplication, cognitive complexity and the top 5 issues. Add a screenshot of the dashboard.
3. Choose one decision-heavy function, for example `Quota.availability` / `_compute` or `CartManager._check_max_per_item`. Draw its control flow graph (Mermaid) in `cfg_cyclomatic.md`.
4. Calculate V(G) **by hand** in three ways, which must agree:
   - E − N + 2
   - number of decisions + 1
   - number of regions
5. List the independent paths and map each path to an existing team test, or write the missing test.
6. **Viva:** be able to recount V(G) live after a small change to the code.

## 2. Task 3.1: Use cases and Playwright end-to-end tests (3 + 6 marks)

**Folder:** `usecases/` | **Branch:** `tawassul/feat-playwright-usecases`

1. In `use_case_spec.md`, write UC-1 to UC-6. Each needs actor, preconditions, main success scenario (numbered steps), at least 2 alternative flows, at least 2 exception flows, postconditions, and the business rule it touches. The brief asks for 2 use cases per member; record who owns which in the table.

| UC | Title | Example alternative flows | Example exception flows |
| :-: | :--- | :--- | :--- |
| 1 | Organizer configures item and quota | quota without limit; item with variations | negative price rejected; quota name empty |
| 2 | Organizer publishes event and sets sale window | presale start in future; end date edited | end before start rejected; publish without quota warned |
| 3 | Customer buys ticket (checkout) | 2 tickets; change attendee name before confirm | invalid email; cart expired before confirm |
| 4 | Customer applies voucher | percentage voucher; fixed-price voucher | unknown code; voucher already redeemed / max usages reached |
| 5 | Customer tries sold-out category | waiting list offered; other category still bookable | last ticket taken by someone else during checkout; quota closed |
| 6 | Customer cancels pending order | cancel from order page link; organizer cancels | paid order cannot be self-cancelled (if disabled); wrong secret returns 404 |

2. In `test_e2e_usecases.py`, use one Playwright test per flow (about 30 tests, Chromium). Each test asserts:
   - the **UI** (URL redirect, alert or banner text, page heading), and
   - the **database** (`Order.status`, `CartPosition` count, `Quota.availability()`, `Voucher.redeemed`).
3. Set up with the `live_server` and team fixtures. The organizer logs in with a test user created in the fixture (`User.objects.create_user`).
4. Record a short trace or video of UC-3 (`--tracing on`) for the report.

## 3. Task 3.2: Usability, keyboard navigation and accessibility (5 marks)

**Folder:** `usability_a11y/` | **Branch:** `tawassul/feat-a11y-lighthouse-fix`

1. In `test_keyboard_nav.py`, drive checkout with **only** `keyboard.press("Tab" / "Shift+Tab" / "Enter" / "Space")`.
   - Record `document.activeElement` after each Tab and assert the order: quantity, add to cart, email, name, terms checkbox, submit.
   - Assert the order is created in the database.
2. Run axe on two screens with `axe-playwright-python`, WCAG 2.1 AA tags. The screens are the organizer item-create page and the customer checkout page.
   - Save the JSON report.
   - Remove duplicate findings and list each one with: DOM element, WCAG criterion, user impact and fix.
3. Run Lighthouse on the same screens: `npx lighthouse <url> --only-categories=accessibility,best-practices --output html`. For the logged-in organizer page, pass the session cookie with `--extra-headers`. Save `lighthouse_report_before.html`.
4. **Fix one screen** in pretix templates under `src/pretix/presale/templates/`, for example missing labels, contrast or ARIA.
   - Keep the change minimal and inside one commit, so it is clear what changed.
   - Re-run axe and Lighthouse, and save `lighthouse_report_after.html`.
   - Put the before/after scores and violation counts in `a11y_findings.md`.
   - Add a test asserting zero violations of the fixed rule.

## 4. Task 3.3: Defensive security (6 marks)

**Folder:** `security/` | **Branch:** `tawassul/feat-security-rbac-zap`

1. In `rbac_access_matrix.md`, build the matrix of roles (anonymous, customer, organizer team member without permission, organizer with permission) against routes (`/control/`, `/control/event/.../items/`, `/control/event/.../orders/`, shop, order page with correct secret, order page with wrong secret, API).
2. Automate at least 4 decisions in `test_rbac_decisions.py`; aim for about 8:

| Who | Route | Expected |
| :--- | :--- | :--- |
| Organizer | `/control/` | 200 |
| Customer | shop | 200 |
| Customer | `/control/` | redirect to `/control/login` |
| Anyone | order page with wrong secret | 404 |
| Team member without `event.items:write` | item create | 403 |
| Anonymous | API | 401 (already covered in Sami's API tests; reference it) |

3. **ZAP passive scan:** run `docker run -p 8090:8090 zaproxy/zap-stable zap.sh -daemon -port 8090 -config api.disablekey=true`.
   - Point Playwright's `proxy={"server": "http://localhost:8090"}` at it and walk UC-3.
   - Export the alerts.
   - In `zap_passive_scan_report.md`, report `Content-Security-Policy`, `X-Frame-Options` (pretix sets `DENY`), `X-Content-Type-Options`, and the cookie flags: `HttpOnly` (pretix sets it), `SameSite` and `Secure`. `Secure` will be off on http localhost; say so.
   - Add `test_security_headers.py` that asserts the headers directly.
4. **Dependency audit:** run `pip-audit -r` on pretix's dependencies, or `pip-audit` inside `.venv`. In `dependency_audit_pip.md`, give the package, version, CVE/GHSA id, CVSS severity, fixed version and the upgrade path. A run with no findings must also be recorded, with the date and the command.

## 5. Task 3.4: Performance (k6) and failure recovery (5 marks)

**Folder:** `performance/` | **Branch:** `tawassul/feat-k6-perf-recovery`

1. Add a seed command `seed_perf_event.py` that resets the data. It creates the organizer and event, an item and a quota of size 100000, and an API token, so every run starts from identical data.
2. Write `k6_workload.js`.
   - Each iteration runs the W2 checkout through the REST API: `POST cartpositions/`, `POST orders/`, `GET orders/{code}/`. It reuses the routes in Sami's OpenAPI spec.
   - Thresholds: `http_req_duration: ['p(95)<500']`, `http_req_failed: ['rate<0.01']`.
3. Do 4 runs with `docker run --rm -i grafana/k6 run - < k6_workload.js`. Reseed before each run.

| Run | Virtual users | Steady state | Repeat |
| :-: | :-: | :-: | :-: |
| 1a, 1b | 1 VU | 60 s | twice |
| 2a, 2b | 5 VUs | 60 s | twice |

4. In `k6_metrics_report.md`, record p95 (ms), requests per second and error %, with the k6 summary output and whether each SLA was met. Note that this is a dev server on a laptop, which is a threat to validity.
5. `test_failure_recovery.py`:
   - Patch the database write in `pretix.base.services.orders._create_order` (or the `OrderPosition` save) to raise `OperationalError` once.
   - Assert there is no `Order` or `OrderPosition` left over and the quota availability is unchanged.
   - Remove the patch and retry the same request with the same `X-Idempotency-Key`. Assert exactly one order exists.
   - Repeat with a cache outage (patch `django.core.cache`) to show checkout still works or fails cleanly.

---

## 6. Shared management (all members; Tawassul's rows)

- Risk register: risks for accessibility, security headers, performance SLA and dependency CVEs.
- Traceability matrix: UC-1..6, then flows, then test ids.
- Three-point estimates against actual effort for Area 3.
- Defects as GitHub Issues: every confirmed finding (a11y violation, missing header, SLA miss).
- AI-use log rows: one per AI-assisted deliverable, including this plan.

## 7. Order of work and estimate

| Step | Work | Estimate (h) |
| :-: | :--- | :-: |
| 1 | Environment: `playwright install chromium`, pull Docker images, seed command | 2 |
| 2 | Use case spec | 3 |
| 3 | E2E tests UC-1..6 | 8 |
| 4 | Keyboard test, axe, Lighthouse before | 3 |
| 5 | Screen fix and after reports | 2 |
| 6 | RBAC matrix and tests, headers test | 3 |
| 7 | ZAP scan and pip-audit reports | 2 |
| 8 | k6 script, 4 runs, report | 3 |
| 9 | Failure-recovery test | 2 |
| 10 | SonarQube and hand-calculated CFG/V(G) | 3 |
| 11 | Shared rows, PR from `member/tawassul` into `main` | 2 |
| | **Total** | **≈ 33** |

## 8. Viva preparation (Tawassul)

- Run any E2E test live and point to both the UI assertion and the database assertion.
- Name the exact WCAG criterion of the fixed defect and show the score before and after.
- Live task "customer opens `/control/`": run `test_rbac_decisions.py -k control` and show the redirect to login.
- Explain p95 against the average, and why 5 VUs changed it.
- Recount V(G) for the chosen function after a code change.
