# Part A. How to use this guide and prepare

## A.1 What the viva checks
The brief gives 20 marks to "Viva, live task and AI-use record" and says: *any component can be reduced or set to zero
if you cannot explain it in the viva*. Each member explains **their own area**, performs a **live task**, and must be
able to explain the **AI-use record**. Everything you show must be reproducible from the repository; every number in
this guide comes from a committed result.

How to read this guide: Part B is the 2-minute project pitch (all three learn it). Part C is the live demo of each
member, step by step (command, what to say, what you should see). Part D lists likely live tasks with solutions.
Part E is the question bank. Part F is the one-page number sheet. Part G covers troubleshooting and the honesty rules.

## A.2 The day before (do it once on the laptop you bring)
1. `cd "D:\5th Semester\4.SQE\Project\pretix"` and `git pull` on `main`.
2. Check the venv: `.venv\Scripts\python -m pytest src/tests/team/zubair -q` (from `src`, see C.1) must print `218 passed`.
3. Start Docker Desktop, then pull the images once (they are large):
   `docker pull sonarqube:25.1.0.102122-community` and `docker pull zaproxy/zap-stable:2.17.0`.
4. Run Lighthouse once so `npx` caches it: `npx lighthouse --version`.
5. Download k6 v0.57.0 for Windows (github.com/grafana/k6/releases/tag/v0.57.0), put `k6.exe` in
   `src/tests/team/tawassul/performance/`.
6. Start pretix once (section C.0) and log in as the organizer.
7. Open the report PDF `docs/sqe/final_report/Project_24I-3142_24I-3070_24I-3100_B.pdf` and this guide.

## A.3 Ten minutes before the viva

* Terminal 1: pretix running (C.0). Terminal 2: in `src`, ready for pytest.
* Browser tabs: http://localhost:8000/control/ (logged in), http://localhost:8000/perf-org/perf-conf/,
  https://github.com/Zubairilyas1/pretix-sqe/actions, `/pull/15`, `/pull/35`, `/pull/36`, `/issues`.
* Docker Desktop running. SonarQube only if you will show it (it needs about 2 minutes to start).
* Phone silent; the final report PDF open at the table of contents.

## A.4 Logins (local test data only)
| Where | User | Password |
| :--- | :--- | :--- |
| pretix back office, organizer (full rights) | `organizer@sqe.test` | `Sqe-Organizer-2026!` |
| pretix back office, viewer (read-only orders) | `viewer@sqe.test` | `Sqe-Viewer-2026!` (exists in the screenshot instance, `docs/sqe/final_report/capture/seed_screens.py`) |
| pretix admin of a fresh database | `admin@localhost` | `admin` |
| SonarQube (local Docker) | `admin` | `Sqe-Ci-Only-Password-1` (set by `sonar_setup.py`) |
| Customer | no account; any e-mail at checkout, e.g. `customer@sqe.test` | |

## A.5 Fallback rule
If a tool is slow or the network fails, do not panic and do not improvise numbers: open the **saved real output**
listed in each demo step (HTML reports, JSON, the CI run on GitHub, the figure in the final report). Say: "This is
the saved output of the same command from <date>; the command is in the repository and can be re-run."

# Part B. The project in two minutes (all three members)

**Say this (adapt the words, keep the facts):**

"We tested **pretix**, an open-source event ticketing system (Django, AGPL), at baseline commit `c0d887738b6c`.
We chose two related workflows in the ticketing module. **W1**: the organizer creates a product and a **quota**,
the number of seats. **W2**: a customer puts tickets in the cart, checks out and pays. The shared record is the
`Quota`: W1 writes its size, W2 consumes it. We wrote eight functional requirements FR-01 to FR-08 and four business
rules: **BR-1** capacity limit (a boundary), **BR-2** purchasability (a decision with several Boolean conditions),
**BR-3** the order state machine (a change of state), **BR-4** cart reservations expire. The two roles are organizer
and customer, plus a read-only viewer for access tests.

Zubair owns **Area 1**: white-box unit tests with 100 % statement and branch coverage of the capacity module
`quotas.py`, MCC and MC/DC tables, mutation testing with Cosmic Ray and two custom operators (96.78 %), and the
GitHub Actions quality gate with five gates including SonarQube. Sami owns **Area 2**: an OpenAPI spec of the
endpoints and a generator that derives equivalence-partition and three-point boundary test data from it, 490 API
tests, and twelve logged API weaknesses. Tawassul owns **Area 3**: six use cases with automated main, alternative
and exception flows in Playwright, usability and accessibility (Lighthouse, axe, a fix from 81 to 93), security
(RBAC, ZAP, pip-audit) and performance with k6 plus a failure-recovery test.

We logged 19 defects as GitHub Issues with root cause analysis and Pareto. Our release decision is **HOLD**:
exit criteria EC-1 (coverage) and EC-2 (mutation) are met, but EC-3 (performance) is not: with five concurrent users
72 % of orders fail with 'database is locked' on SQLite."

# Part C. Live demo script for each member

## C.0 Start pretix (anyone; takes about 1 minute)
```powershell
cd "D:\5th Semester\4.SQE\Project\pretix\src"
$env:PRETIX_CONFIG_FILE = "tests/team/tawassul/performance/perf_pretix.cfg"
../.venv/Scripts/python manage.py migrate
../.venv/Scripts/python manage.py shell -c "exec(open('tests/team/tawassul/performance/seed_perf_event.py').read())"
../.venv/Scripts/python tests/team/tawassul/performance/perf_server.py
```
**Expect:** the seed prints `seeded: event=perf-org/perf-conf item=<id> quota=<id> size=1000000 ...`, the server
prints `pretix perf server on http://0.0.0.0:8000`. Open http://localhost:8000/control/ and log in as the organizer.
**Say:** "This is pretix with DEBUG off behind a production WSGI server (waitress), with synthetic data. The seed
script resets the event so every run starts from the same state."

**Show W1 by hand:** Products -> Create a new product (name, price, *Create a new quota*, size 10) -> Save ->
Quotas -> open the quota: *Total 10, available 10*.
**Show W2 by hand:** open the shop http://localhost:8000/perf-org/perf-conf/, add 2 tickets, checkout with any
e-mail, bank transfer, confirm. Back in the quota: *pending orders 2, available 8*. **Say:** "That is the shared
record: W2 consumed what W1 created." (Same screens are Figures 9.2-9.17 in the report.)

## C.1 Zubair: Area 1 (white-box, MCC/MC-DC, mutation, CI)

### Step 1: the unit tests and the coverage gate
```powershell
cd "D:\5th Semester\4.SQE\Project\pretix\src"
../.venv/Scripts/python -m pytest tests/team/zubair -q
../.venv/Scripts/python -m pytest tests/team/zubair --cov=pretix.base.services.quotas --cov-branch --cov-report=html:../htmlcov --cov-report=json:../coverage-area1.json -q
../.venv/Scripts/python tests/team/zubair/coverage_gate.py ../coverage-area1.json
start ../htmlcov/index.html
```
**Expect:** `218 passed`; coverage report `quotas.py` 239/239 statements, 143/144 branches; the gate passes.
**Say:** "The scope is the business-rule code. `coverage_gate.py` reads coverage.py's JSON per function and fails
if any statement or branch in the scope is missed. Exactly one branch is allowed, line 361 to 363, and it is
documented as infeasible: the query at L304-305 only returns order lines with status PAID or PENDING, so after `if status == PAID` the `elif status == PENDING` can never be false."
**Key files:** `test_quota_availability_whitebox.py` (70 tests), `test_whitebox_order_rules.py`,
`test_order_state_transitions.py`, `test_mutation_killers.py`, `coverage_gate.py`.
**Techniques to name:** fakeredis replaces Redis (cache paths), a `GREATEST` SQL function is registered for SQLite,
the `quota_availability` signal is patched, time is frozen for the cache-age boundary.

### Step 2: MCC and MC/DC
```powershell
../.venv/Scripts/python -m pytest tests/team/zubair/test_mcc_mcdc.py -q
```
Open `docs/sqe/zubair/MCC_MCDC_TABLES.md`. **Explain one decision (Q5, `quotas.py` L367):**
`if size_left[q] <= 0 and q not in self.results:` has conditions A (capacity exhausted) and B (quota not yet
decided). MCC = all 4 combinations (rows Q5-1..Q5-4). MC/DC pairs: A -> (Q5-1, Q5-3) because only A changes and the
outcome changes; B -> (Q5-1, Q5-2). "MC/DC needs n+1 = 3 tests for 2 conditions, MCC needs 2^n = 4."
**Mention:** decisions Q1-Q7 in `quotas.py`, I1 (BR-2 `Item.is_available`, 18 feasible rows) and O1 (BR-3 late
payment). `test_mcdc_pairs_are_valid` checks automatically that every listed pair differs in exactly one condition
and in the outcome. Coupled conditions are marked with a third element `"C"` (e.g. I1 pair B).

### Step 3: state transitions (BR-3)
`test_order_state_transitions.py`: allowed transitions T1-T8 (n->p, n->e, n->c, p->c, e->p, e->c, c->n, approval)
through the real services (`OrderPayment.confirm`, `mark_order_expired`, `_cancel_order`, `reactivate_order`,
`approve_order`) and disallowed transitions X1-X6 (e.g. paying a canceled order raises). After each transition the
quota is read back, because a state change frees or consumes capacity.

### Step 4: mutation testing
```powershell
cd ..
.venv/Scripts/python src/tests/team/zubair/mutation/run_mutation.py --workers 4 --shard 0/40 --out mutation-demo
start mutation-demo/report.html
```
**Expect:** about 18 mutants in 2-3 minutes, report with KILLED/SURVIVED per mutant. (Full run: about an hour
locally; saved: `src/tests/team/zubair/mutation/results/run2_after_kills/report.html`.)
**Say:** "Cosmic Ray 8.9 mutates `quotas.py` with its core operators and our two custom operators, then runs the
Area 1 tests against every mutant. Run 1: 715 mutants, 650 killed, 90.91 %. We analysed all 65 survivors: 23 are
equivalent (cannot change behaviour), 42 showed missing or weak tests, and we wrote `test_mutation_killers.py`
for them. Run 2: 692 killed, 23 survived, **96.78 %**; all 23 survivors are equivalent."
**Custom operators** (`mutation/sqe_mutation_operators/`, plugin entry point `cosmic_ray.operator_providers: sqe`):

* `sqe/SwapAvailabilityVerdict` swaps the verdict constants `Quota.AVAILABILITY_GONE/ORDERED/RESERVED/OK`, i.e. a
  domain fault "report the wrong reason for unavailability" that no core operator produces. 30 mutants, 30 killed.
* `sqe/SwapOrderStatus` swaps `Order.STATUS_PAID/PENDING/EXPIRED/CANCELED`, i.e. counting the wrong orders against
  capacity. 15 mutants, 15 killed.

**One equivalent mutant to explain:** `time.time() - int(data[2]) < 120` mutated to `time.time() % int(data[2]) < 120`
at L151: for every real cache timestamp `ts` (> now/2) `now % ts == now - ts`, so behaviour is identical.

### Step 5: the CI quality gate
Open `.github/workflows/sqe_quality_gate.yml` and https://github.com/Zubairilyas1/pretix-sqe/pull/15.
**Say:** "Every pull request runs five gates. Gate 1: Area 1 tests and the 100 % coverage gate. Gate 2: Area 2 API
tests. Gate 3: Area 3 Playwright tests. Gate 4: SonarQube in a service container with our quality gate (coverage >= 99 %, reliability, security and maintainability rating A, duplication <= 3 %), the scanner waits for the gate.
Gate 5: Cosmic Ray mutation score >= 85 %. The deploy job needs all five and runs only on a push to main. There is
no `continue-on-error` and no `|| true`. Branch protection on main requires the five checks."
**Why Gate 5 is split into 8 shards:** on GitHub's runner one job reached only 338 of 715 mutants in 120 minutes.
`run_mutation.py --shard i/8` gives each job every 8th mutant in a stable order; the Gate 5 job `--merge`s them,
checks that every mutant was executed exactly once, and applies the threshold (run 46131379965: 715/715, 96.78 %).
**Thresholds and why** (MUTATION_REPORT.md section 5): run 2 measured 96.78 % with 23 equivalent mutants left, so
100 % is impossible; 85 % leaves room for new code in the module while still failing if a substantial part of the
tests is removed or weakened. Coverage is 100 % on the scope because the module is small and business-critical.

### Step 6: blocked PR and fix PR

* **PR #35** changes L367 `<= 0` to `< 0` (oversell by one). Result: Gate 1 19 failed, Gate 2 4 failed, Gate 3 1
  failed, Gate 4 failed, merge **BLOCKED**. "The bug is caught by all three test areas."
* **PR #36** fixes **D-Z01**: the waiting-list auto-disable date was compared with the real `now()` instead of the
  `now_dt` passed to `QuotaAvailability`, so evaluating availability for a future moment was wrong. Commit 1 adds
  the regression test (`test_dz01_waitinglist_now_dt.py`): CI red, `assert 1 == 0`. Commit 2 passes `now_dt` to
  `_compute_waitinglist`: CI green. It closes issue #16.

### Step 7: SonarQube (optional, 5 minutes)
```powershell
.venv/Scripts/python docs/sqe/final_report/capture/capture_sonar.py
```
This starts SonarQube in Docker, sets it up exactly like CI (`sonar_setup.py`), scans and takes screenshots. To
browse yourself, run the commands in `docs/sqe/VIVA_DEMO_GUIDE.md` section 5 and open http://localhost:9000.
Results for `quotas.py`: coverage 99.7 % (line 100 %, branch 99.3 %), 0 bugs, 0 vulnerabilities, all ratings A,
7 code smells, debt 102 min (1.0 %), complexity 111, cognitive complexity 174.

## C.2 Sami: Area 2 (API testing and test-data generation)

### Step 1: the specification
```powershell
start ..\docs\sqe\final_report\evidence_html\swagger_ui.html
```
(or open `src/tests/team/sami/openapi/pretix_orders_api.yaml`). **Say:** "OpenAPI 3 description of 19 pretix API
operations used by W1 and W2 (items, quotas, cart positions, orders and order actions), with constraints:
`minimum`/`maximum`, `minLength`/`maxLength`, required fields, enums, path/query/header parameters. Two extensions:
`x-runtime-ref` marks parameters that must reference existing objects (existing/unknown cases),
`x-reject-status` gives the status a rejected value must produce (e.g. 200 for an ignored query flag)."
`tests/team/sami/openapi/test_openapi_spec.py` validates the spec itself with openapi-spec-validator.

### Step 2: the generator (EP + 3-point BVA)
```powershell
cd src
../.venv/Scripts/python tests/team/sami/generator/generate_test_data.py
```
**Expect:** 322 cases (234 equivalence-partition, 88 boundary). **Say:** "For every constrained field the generator
derives EP classes (valid, below minimum, above maximum, wrong type, missing, null...) and three-point boundaries
min-1, min, min+1 and max-1, max, max+1. It walks nested objects and array items, e.g. `positions[].price`, and
path, query and header parameters. Each case says which status is expected. The tests read the generated JSON, so
the tests change when the spec changes."

### Step 3: the API tests
```powershell
../.venv/Scripts/python -m pytest tests/team/sami -q
```
**Expect:** `490 passed, 30 xfailed`. **Say:** "The 30 xfails are **strict**: each is a confirmed weakness
(W-01 to W-12) and if pretix ever fixes it, the test turns into XPASS and fails, so we notice."
Files: `test_api_ep_bva.py` (generated cases), `test_api_status_coverage.py` (all 47 documented status codes,
including 401 on every operation, 403/404 for read-only tokens, 409 via a locked `ApiCall`, 415),
`test_api_parameters.py`, `test_api_decision_tables.py` (DT-1 eight rules for order creation, DT-2),
`test_negative_rules.py` (BR-1 to BR-3 through the API), cross-workflow test (W1 quota via API -> W2 order -> quota
read back, including "rejected order does not consume capacity").

### Step 4: the regeneration live task (rehearse this one)
See Part D task 1. Already done once: `src/tests/team/sami/generator/regeneration_demo/REGENERATION_REPORT.md`
(changed `code.maxLength` 16 -> 12 and `size.maximum`; the predicted case `createOrder.code.BVA.len_max+1` failed).

### Step 5: the weaknesses
| ID | What | Why it matters |
| :--- | :--- | :--- |
| W-01, W-02, W-09 | negative item / cart / order-position price accepted | revenue and invoice integrity |
| W-03 | retry without idempotency key creates a duplicate order | double charge, double capacity |
| W-04 | empty / over-long item name accepted | data quality |
| W-05 | quota size above 32-bit range accepted | crashes on PostgreSQL |
| W-06 | `with_availability` ignored on quota detail | misleading client data |
| W-07 | order API ignores the sale window | BR-2 bypass |
| W-08 | order API ignores min/max per order | BR-1 bypass |
| W-10, W-11 | idempotency key > 190 chars, attendee name > 255 chars accepted | input validation |
| W-12 | order action endpoints do not validate their body (`send_email` by truthiness) | API contract |

## C.3 Tawassul: Area 3 (use cases, usability, security, performance)

### Step 1: use cases and their tests
Open `src/tests/team/tawassul/usecases/use_case_spec.md`. Six use cases: UC-1 organizer configures item and quota,
UC-2 publishes event and sales window, UC-3 customer checkout, UC-4 voucher, UC-5 sold-out category, UC-6 customer
cancels a pending order. Each has preconditions, postconditions, main flow, alternative flows A1/A2 and exception
flows E1/E2, and every flow has a test named after it.
```powershell
cd src
../.venv/Scripts/python -m pytest tests/team/tawassul/usecases -k uc3_main --headed --slowmo 500
```
**Say while the browser runs:** "The test starts a real pretix (live server), buys a ticket like a customer, then
checks the **postconditions in the database**: one order, status pending, quota availability reduced by one."
Full suite: `../.venv/Scripts/python -m pytest tests/team/tawassul -q` -> `64 passed, 4 xfailed` (about 6 min).
The 4 xfails are strict and documented: A3-D01 negative price stored (UC1-E1) and A3-D02 missing headers:
`test_no_mime_sniffing` on the shop and on the login page, and `test_referrer_policy_protects_order_secret`.

### Step 2: usability and keyboard tests
`usability_a11y/test_usability_tasks.py`: W1 task "quota rejected with -5, then corrected", W1 keyboard-only quota
form, W2 "max-per-order error, then corrected purchase". `test_keyboard_nav.py`: the whole checkout with Tab/Enter
only; it records the focus path and asserts the order of fields. **Story:** on GitHub's runner this test once
failed because pretix's address script disables street/zipcode/city while it fetches country rules; we reproduced
it locally by holding that request open and fixed the test to wait like a user would.

### Step 3: Lighthouse and axe, the fix
```powershell
npx lighthouse http://localhost:8000/perf-org/perf-conf/ --only-categories=accessibility,best-practices,seo --view
../.venv/Scripts/python -m pytest tests/team/tawassul/usability_a11y/test_axe_scan.py -q
```
**Result to explain:** organizer product form Lighthouse accessibility **81 -> 93** after the fix; failed audits
5 -> 2; shop page 100. Fix in `pretixcontrol/base.html` (applies to every back-office page): `html-has-lang`
(WCAG 3.1.1, added `lang`), `image-alt` (1.1.1, logo `alt=""` as decorative), `link-name` (2.4.4/4.1.2, six sidebar
arrow links got `aria-label`). Regression test `test_remediated_rule_stays_fixed_on_organizer_page`.
Lighthouse vs axe: Lighthouse uses axe-core inside plus best-practice/SEO checks and a score; axe gives the raw rule
violations per element. Findings were de-duplicated by rule and selector.

### Step 4: security

* **RBAC** (`security/rbac_access_matrix.md`, `test_rbac_decisions.py`, 10 tests): organizer / viewer / customer
  against 11 resources; viewer gets 403 on the product editor and cannot cancel orders; customer needs the order
  secret (wrong secret -> 404, not 403, so order codes cannot be probed); API without token -> 401.
* **ZAP** (`security/zap_scan.py`): passive scan through a proxy while Playwright walks W1 and W2 to the order
  confirmation. 186 alerts, 14 rules. New 10020 on order pages (no anti-clickjacking header) is by design: pretix
  exempts them so the shop widget can show them in an iframe; risk linked to PR-SEC-04, fix suggestion
  `frame-ancestors`. Passive = only observes traffic, no attacks.
* **pip-audit**: `oauthlib 3.3.1` with CVE-2026-49272 (High 8.5, fixed in 4.0.1) and CVE-2026-49265 (Medium 6.8).
```powershell
../.venv/Scripts/python tests/team/tawassul/security/zap_scan.py      # needs pretix running and Docker
```

### Step 5: performance and recovery
```powershell
cd tests/team/tawassul/performance
.\k6.exe run -e BASE=http://localhost:8000 -e VUS=1 -e P95=500 -e TOKEN=(Get-Content .perf_token) -e ITEM=<id> k6_order_create.js
```
**Results (saved in `results_v2/`):** WL-1, 1 user: p95 133 ms and 129 ms, 0 % failures (limit 500 ms, < 1 %): met.
WL-2, 5 users: p95 492 ms and 527 ms (limit 1000 ms) but 72.85 % and 71.99 % failures: **not met**. Cause: HTTP 500
"database is locked", SQLite allows one writer at a time; production pretix uses PostgreSQL. Two runs each, limits
fixed in `PERF_TEST_PLAN.md` **before** the runs, 15 s warm-up excluded.
**Recovery test** (`test_failure_recovery.py`): a database failure is injected inside `_create_order` during a real
checkout; asserts a graceful error page, no partial Order/Position/Payment, quota not consumed, and after recovery
exactly one order on retry.

### Step 6: CFG and cyclomatic complexity
Open `static_analysis/cfg_cyclomatic.md`. `Quota.availability`: 5 decision nodes D1-D5, so
**V(G) = P + 1 = 6**; also V(G) = E - N + 2 on the drawn graph. SonarQube reports complexity 6 for the function
(evidence `sonar_function_complexity.json`); our older note that said 4 was wrong and corrected. Six basis paths
P1-P6; P6 is infeasible (D1 true means the cache is a non-empty dict, so D3 "cache is None" cannot be false at
the same time), so five paths are tested in `test_cfg_paths.py`.

## C.4 Shared test management (anyone may be asked)

* **Test plan** `shared_management/TEST_PLAN.md`: scope W1/W2, FR-01..08, BR-1..4, risk-based approach, levels,
  environment, data, schedule, exit criteria EC-1..3.
* **Risk register 5x5** (`RISK_REGISTER_5x5.md`): risk = likelihood x impact (1-5 each). Highest: PJ-INT-01 (20),
  PR-WB-01 (12), PR-API-01/02/06 (12), PR-PERF-01 (12). Each risk lists the test technique and depth.
* **RTM**: FR -> rule -> test IDs -> scripts; requirements coverage 8/8 = 100 %.
* **PERT** `E = (O + 4M + P) / 6`, sigma `(P - O) / 6`. Team total: O 64.5 h, M 106 h, P 186 h -> E 112.43 h;
  actual 103.0 h (-8.4 %).
* **Defects** (`CONSOLIDATED_DEFECT_LOG.md`, issues #16-#34): 19 defects with severity, priority, status, triage.
  RCA-1 (negative prices) and RCA-2 (API bypasses sale window and limits) with 5 Whys and fishbone, corrective and
  preventive actions. Pareto: input validation 8, rule not enforced 5, security config 3, logic 2, accessibility 1;
  the first three categories hold 84 %.
* **GQM metrics** (`PROGRESS_REPORTS.md`, checkpoints CP1-CP4): defect density 19 / 8.11 KLOC = **2.34 per KLOC**,
  requirements coverage 100 %, reopen rate 0 / 1 closed = 0 %.
* **Completion report**: what was / was not tested, deviations DV-1..DV-5, open defects by priority, residual risk
  per risk, **HOLD** with actual vs target for EC-1..3.

# Part D. Likely live tasks and how to solve them

**General method for any live task:** (1) repeat the task in your words, (2) find the file (`git grep -n <name>`),
(3) write the smallest test first and show it fail (red), (4) change, (5) run, show green, (6) say which rule /
requirement / risk it belongs to.

**Task 1 (Sami) - "Change a constraint in the spec and show the tests adapt".**
1. In `src/tests/team/sami/openapi/pretix_orders_api.yaml` find the field (e.g. order `code`: `maxLength: 16`) and
   change it to 12.
2. `../.venv/Scripts/python tests/team/sami/generator/generate_test_data.py` -> the generated cases for that field
   change: the boundary values are now 11, 12, 13.
3. `../.venv/Scripts/python -m pytest tests/team/sami -q -k code` -> the case `len_max+1` (13 characters) now
   expects a rejection that pretix does not give, so that test fails: "the spec and the system now disagree,
   exactly at the boundary we predicted" (this is what REGENERATION_REPORT.md recorded).
4. Revert: `git checkout -- src/tests/team/sami/openapi/pretix_orders_api.yaml` and regenerate.
The script `generator/regeneration_demo/` with `--verify` automates this (see REGENERATION_REPORT.md).

**Task 2 (Zubair) - "Break the capacity rule and show the tests catch it".** In `src/pretix/base/services/quotas.py`
L367 change `size_left[q] <= 0` to `< 0`, run `pytest tests/team/zubair -q` -> 19 failures (same as PR #35), revert
with `git checkout -- src/pretix/base/services/quotas.py`.

**Task 3 (Zubair) - "Add a boundary test for a quota of size N".** In a new test: create a quota of size 3, create
paid orders of 2, 3 and 4 positions in separate tests, compute `QuotaAvailability`, assert `(OK, 1)`, `(GONE, 0)`
and the oversell case. Copy the pattern of `TestOrdersBoundary.test_paid_orders_bva` in
`test_quota_availability_whitebox.py` (parametrize with `size-1, size, size+1`).

**Task 4 (Zubair) - "Is this surviving mutant equivalent? Kill it if not."** Read the diff in the Cosmic Ray
report. Ask: is there any input where original and mutant behave differently? If yes, write a test with exactly that
input (red on the mutant, green on the original); if no, give the argument (e.g. the `%` example in C.1 step 4).
Re-run one shard to show it killed.

**Task 5 (Zubair) - "Show that CI blocks a bad change".** Show PR #35 (red, blocked) or make a branch with a
one-line bug, push, open a PR; Gate 1 goes red within about 2 minutes.

**Task 6 (Tawassul) - "Add/modify a use-case test".** Copy a test in `usecases/test_e2e_usecases.py`, change one
step (e.g. quantity 3 instead of 1), add a postcondition (`available(team_quota) == 7`), run it with `--headed`.

**Task 7 (Tawassul) - "Fix another accessibility issue and verify".** Pick a remaining Lighthouse audit (e.g. a
contrast or ARIA name issue on the product form), change the template, restart pretix, re-run Lighthouse on the
same URL and compare the score and the failed audits; add a case to `test_axe_scan.py`.

**Task 8 (Tawassul) - "Run a load test with a different number of users".** Same k6 command with `-e VUS=3 -e
P95=800`; read p95 (`http_req_duration{phase:measure}` p(95)), requests per second (`http_reqs` rate) and failure
rate (`http_req_failed`). Reseed between runs (C.0 seed command).

**Task 9 (Tawassul) - "Calculate V(G) for another function".** Count decision points (if, elif, for, while, and,
or, except, ternary): V(G) = decisions + 1. Draw nodes and edges: V(G) = E - N + 2. Compare with SonarQube's
complexity of the function (`sonar_function_complexity.py` shows how it was measured).

**Task 10 (any) - "Show the quota changing across both workflows".** Do W1 and W2 by hand (C.0) and open the quota
page before and after; or run the cross-workflow API test in `tests/team/sami`.

**Task 11 (any) - "Show a defect from report to fix".** Issue #16 (D-Z01) -> PR #36 -> red run -> green run ->
issue closed. Or an open one: issue #17 (W-01) -> strict xfail test -> RCA-1.

**Task 12 (any) - "Show your commits".** `git log --author="Zubairilyas1" --oneline` (Sami: `i243070-beep`,
Tawassul: `Tawassul Akbar`), then explain two commits of your own.

# Part E. Question bank with model answers

## E.1 Zubair - Area 1
1. **What is the difference between statement and branch coverage?** Statement coverage counts executed lines;
   branch coverage requires every decision outcome (true and false of every `if`, loop entered and skipped). 100 %
   statements can still miss the false branch of an `if` without `else`.
2. **Why is one branch not covered?** L361 -> L363 in `quotas.py`: the query at L304-305 returns only PAID or PENDING
   order lines, so after `if status == PAID` the `elif status == PENDING` is never false. The gate allows exactly
   that one branch (`JUSTIFIED_BRANCHES` in `coverage_gate.py`) and nothing else.
3. **MCC vs MC/DC?** MCC tests all 2^n combinations of the conditions. MC/DC requires, for each condition, a pair of
   tests that differ only in that condition and in the outcome, so each condition independently affects the
   result; typically n+1 tests.
4. **What are masked/coupled conditions?** With short-circuit `and`, if A is false B is not evaluated (masked); coupled
   conditions cannot vary independently, so we used a unique-cause or masking pair and marked it `"C"`.
5. **What is mutation testing?** Make small faults (mutants) in the code, run the tests; a mutant is killed if a test
   fails. Score = killed / (killed + survived). It measures how well tests detect faults, not just execute code.
6. **What is an equivalent mutant?** A mutant whose behaviour is identical to the original for all inputs, so no test
   can kill it; it lowers the score without showing a weakness. 23 of ours are equivalent.
7. **Why custom operators?** Core operators change syntax (`<` to `<=`, `+` to `-`). Ours model domain faults: the
   wrong availability verdict and the wrong order status counted against capacity.
8. **How are custom operators registered?** As a Python package with an entry point in group
   `cosmic_ray.operator_providers` (name `sqe`); Cosmic Ray then lists `sqe/SwapAvailabilityVerdict` etc.
9. **Why 85 %?** Run 2 reached 96.78 % and 23 survivors are equivalent, so 100 % is impossible; 85 % leaves room
   for new code but fails if a substantial part of the tests is removed or weakened.
10. **What happens if a mutant hangs?** The session timeout (300 s) marks it; the gate also fails if any mutant was
    not executed.
11. **Why was Gate 5 sharded?** One runner did 338/715 in 120 min; 8 shards cover the same 715 mutants (checked
    exactly once) and finish in about 40 min.
12. **What does SonarQube measure?** Bugs (reliability), vulnerabilities (security), code smells (maintainability),
    coverage, duplication, technical debt (time to fix smells), ratings A-E, cyclomatic and cognitive complexity.
13. **Cyclomatic vs cognitive complexity?** Cyclomatic counts independent paths (decisions + 1); cognitive weights
    nesting and breaks in linear flow, closer to how hard code is to read. `quotas.py`: 111 vs 174.
14. **What is a quality gate?** A set of conditions on measures; the analysis passes only if all hold. Ours: coverage
    >= 99 %, ratings A, duplication <= 3 % on overall code.
15. **Why fakeredis?** `quotas.py` caches availability in Redis; fakeredis is an in-memory Redis, so cache read/write,
    TTL and freshness paths run without a real server.
16. **What is D-Z01?** See C.1 step 6; minor severity, P2, found by white-box review, fixed by PR #36.
17. **Why does PR #35 also fail Gate 2 and 3?** Off-by-one oversell changes availability seen by the API and the shop,
    so API and E2E tests that buy the last seat fail too: defence in depth.
18. **What is branch protection?** Repository rule: main can only be updated through a PR whose required checks
    (Gate 1-5) pass; force pushes and deletion disabled.
19. **You bypassed the rule to merge PR #15, why?** The rule also needs one approving review and GitHub does not
    allow approving your own PR; the admin bypass was used only after all five gates were green.
20. **What does the deploy job do?** Runs only on push to main after all gates; builds a release-candidate archive
    (`git archive`) with SHA-256, uploaded as an artifact.
21. **State transition testing?** Model states (n, p, e, c) and events; test every allowed transition and that
    forbidden ones are rejected, and check side effects (capacity).
22. **Which BR does Q5 implement?** BR-1: when capacity reaches zero in the order stage the quota is GONE (paid) or
    ORDERED (pending).
23. **How did you test time-dependent code?** Frozen `time` in the module (cache age 119/120/121 s) and `now_dt`
    arguments.
24. **What would you improve?** Run the same suite on PostgreSQL, add property-based tests for availability sums,
    mutate `models/orders.py` too.

## E.2 Sami - Area 2
1. **What is equivalence partitioning?** Split the input domain into classes the system should treat the same; test
   one value per class (valid and each invalid class).
2. **What is three-point BVA?** For each boundary test the value just below, on and just above: min-1, min, min+1
   and max-1, max, max+1.
3. **Why generate test data from the spec?** One source of truth; when a limit changes the tests change; no manual
   copying errors; coverage of every constrained field is systematic.
4. **What is `x-runtime-ref`?** Our extension: a parameter must reference an existing object (e.g. item id); the
   generator makes an existing and an unknown case (expect 404/400).
5. **Why strict xfail?** A known defect is documented as an expected failure; strict means if it starts passing the
   suite fails, so fixes are noticed and the defect log is updated.
6. **Which status codes did you cover?** All 47 documented pairs: 200/201/204, 400, 401 (every operation without
   token), 403 (read-only token on writes), 404, 409 (locked idempotent call), 415 (wrong content type).
7. **What is idempotency and W-03?** Repeating a request with the same `X-Idempotency-Key` returns the first response;
   without the key a retry creates a second order (W-03, accepted for trusted clients, documented).
8. **What is a decision table?** Conditions x actions; each column is a rule. DT-1 (BR-2): a product may be ordered
   iff C1 active, C2 inside the sale window, C3 quota has capacity: 2^3 = 8 rules; rows where pretix deviates are
   strict xfail (W-07). DT-2 (BR-1 per-order limits with min 2, max 3): C1 n >= min, C2 n <= max; (F, F) is
   infeasible because min <= max, so 3 rules are tested (deviation W-08).
9. **API vs UI testing?** API tests are faster and reach validation directly; they found that rules enforced in the
   shop (cart service) are missing in the order API (RCA-2).
10. **How do you authenticate?** Team API token with/without write permission (`Authorization: Token <t>`).
11. **Cross-workflow test?** Create a quota by API (W1), order by API (W2), read the quota back; a rejected order must
    not change it.
12. **Regeneration demo?** See Part D task 1.
13. **What are W-07 and W-08 risks?** A reseller could sell outside the sale window or above per-order limits; risk
    PR-API-06 (12, High).
14. **Why 403 for unknown organizer?** pretix checks the token's organizer first, so an unknown slug is
    "not allowed" (403), not 404; documented in `endpoint_weaknesses.md`.
15. **What is OpenAPI?** A machine-readable REST API description: paths, operations, parameters, schemas, responses.

## E.3 Tawassul - Area 3
1. **Use case vs test case?** A use case describes actor goals and flows; a test case checks one flow with concrete
   data and expected postconditions. We have one test per flow.
2. **Pre/postconditions?** Precondition: state needed before (e.g. event live, quota free). Postcondition: state
   after (order exists, quota reduced); our tests assert it in the database.
3. **Why Playwright?** Required by the brief; real Chromium, auto-waiting, works with pytest and Django live server.
4. **What is WCAG?** Web Content Accessibility Guidelines; levels A/AA/AAA. Our fixes were level A criteria 1.1.1,
   2.4.4, 3.1.1, 4.1.2.
5. **Why keyboard tests?** Users of screen readers and motor-impaired users rely on Tab/Enter; all functions must be
   reachable in a logical order with visible focus.
6. **Lighthouse score meaning?** Weighted share of passed audits (0-100); not a full accessibility proof, manual
   checks still needed.
7. **What is RBAC?** Role-based access control: permissions are given to roles (teams) not users; we tested allow and
   deny decisions per role and resource.
8. **Passive vs active scan?** Passive only inspects traffic (headers, cookies); active sends attacks. We used passive
   because the brief asks for defensive testing on a local system.
9. **Why 404 not 403 for a wrong order secret?** Not revealing whether an order code exists prevents enumeration.
10. **What is p95?** 95 % of requests were faster than this value; better than average for user experience.
11. **Why did WL-2 fail?** SQLite has a single write lock; concurrent order writes get "database is locked" (HTTP 500).
    Root cause environment; recommendation PostgreSQL and re-test.
12. **What is warm-up and why exclude it?** First requests load code and caches; excluding 15 s makes runs comparable.
13. **What does the recovery test prove?** Atomicity: a failure during order creation leaves no partial data and the
    retry creates exactly one order.
14. **V(G) of `Quota.availability`?** 6 (5 decisions + 1); SonarQube agrees; one basis path infeasible.
15. **What is A3-D06?** SonarQube S1656 self-assignment in `cart.py` add-on price correction: a no-op that should
    probably assign another value; reported upstream.
16. **Clickjacking 10020?** Missing `X-Frame-Options`/`frame-ancestors` on order pages; by design for the widget;
    residual risk documented with a fix suggestion.

## E.4 Conceptual SQE questions (anyone)
1. **Verification vs validation?** Verification: built right (meets spec); validation: right product (meets need).
2. **Error, fault, failure?** Human mistake -> defect in code -> observable wrong behaviour.
3. **Test levels?** Unit, integration (API), system (E2E), acceptance; our mapping is in TEST_PLAN section 3.
4. **Black-box vs white-box?** Black-box from specification (EP, BVA, decision tables, use cases); white-box from code
   structure (coverage, MC/DC, paths).
5. **Severity vs priority?** Severity = impact on the system; priority = urgency to fix (business decision).
6. **Defect life cycle?** New -> triaged -> open/assigned -> fixed -> verified -> closed (or reopened / rejected).
7. **Risk exposure?** Likelihood x impact; drives test depth.
8. **Exit criteria?** Measurable conditions to stop testing / release; ours EC-1..3.
9. **RTM?** Maps requirements to tests (and back) to show coverage and impact of changes.
10. **PERT?** Three-point estimate E = (O + 4M + P)/6, sigma = (P - O)/6.
11. **GQM?** Goal -> Question -> Metric; e.g. goal "product quality", question "how many defects per size",
    metric defect density.
12. **Defect density?** Defects / KLOC: 19 / 8.11 = 2.34.
13. **Reopen rate?** Reopened / closed defects; measures fix quality.
14. **Pareto principle?** About 80 % of effects from 20 % of causes; focus prevention on top categories.
15. **5 Whys and fishbone?** 5 Whys drills to a root cause; fishbone groups causes (method, machine, people,
    material, measurement, environment).
16. **Corrective vs preventive action?** Fix this defect vs stop the class of defects (one shared validation per rule).
17. **Regression testing?** Re-running tests after change; our CI does it on every PR.
18. **CI vs CD?** CI merges and tests often; CD automatically delivers/deploys passing builds (our deploy job).
19. **Test double types?** Dummy, stub, fake (fakeredis), mock, spy; the recovery test patches a function to fail.
20. **Flaky test?** Passes and fails without code change; we found and fixed two (timing of an XHR, shared SQLite).
21. **Technical debt?** Estimated time to fix maintainability issues (SonarQube: 102 min for quotas.py).
22. **Code smell?** Maintainability issue that is not a bug (long method, duplicated literals).
23. **Static vs dynamic testing?** Without running (review, SonarQube) vs running the code (tests, k6).
24. **Load vs stress vs soak?** Expected load / beyond capacity / long duration.
25. **Throughput?** Requests completed per second (k6 `http_reqs` rate).

## E.5 Hard project questions
1. **Why HOLD and not RELEASE?** EC-3 is a defined exit criterion tied to a top risk and it failed (72 % failures with
   5 users). Releasing would ignore our own criteria. Re-test on PostgreSQL to release.
2. **Is the failure pretix's fault?** The failure comes from SQLite's single writer in our environment; pretix
   recommends PostgreSQL. We report it as an environment risk, not a pretix defect.
3. **Why should we trust your numbers?** Every number has a committed raw output (JUnit XML, JSON, HTML report, CI run
   link); the scripts regenerate them.
4. **Why did you choose pretix?** Web UI, REST API, persistent storage, testable Python code, clear shared record.
5. **What would you do with more time?** PostgreSQL runs, fix upstream issues (W-01, W-07/08), property-based tests,
   active ZAP scan in a sandbox.
6. **Where did AI help and how did you check it?** See Part G; every row in the AI-use record says what was checked.
7. **Why are some Area 2/3 fixes committed by Zubair?** Recorded as deviation DV-5 and AI rows 20-21: the team asked
   Zubair to close the remaining gaps. Sami and Tawassul must study those changes before the viva so that they can
   explain them as part of their area (see G.2).

# Part F. One-page number sheet

| Item | Value |
| :--- | :--- |
| System | pretix, baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`, repo github.com/Zubairilyas1/pretix-sqe |
| Requirements / rules | FR-01..FR-08, BR-1..BR-4, roles organizer / customer (+ viewer) |
| Area 1 tests | 218 passed |
| Coverage `quotas.py` | 239/239 statements, 143/144 branches (1 infeasible, justified) |
| Mutation | run 1: 715 mutants, 650 killed, 90.91 %; run 2: 692 killed, 23 survived (equivalent), **96.78 %**; custom operators 30/30 and 15/15 |
| SonarQube `quotas.py` | coverage 99.7 %, 0 bugs, 0 vulnerabilities, ratings A, 7 smells, debt 102 min, complexity 111, cognitive 174 |
| Area 2 | 322 generated cases (234 EP, 88 BVA); 490 passed, 30 xfailed (W-01..W-12) |
| Area 3 | 64 passed, 4 xfailed; 6 use cases, 30 flow tests |
| Accessibility | product form Lighthouse 81 -> 93, failed audits 5 -> 2; shop 100 |
| Security | ZAP 186 alerts, 14 rules; oauthlib 3.3.1 CVE-2026-49272 (High 8.5) |
| Performance | 1 user p95 133/129 ms, 0 %; 5 users p95 492/527 ms, 72.85/71.99 % failures |
| V(G) `Quota.availability` | 6 (hand) = 6 (SonarQube) |
| Defects | 19 (issues #16-#34); Pareto 8/5/3/2/1; density 2.34/KLOC; reopen 0 % |
| PERT | E 112.43 h, actual 103.0 h |
| CI | 5 gates + deploy; green PR #15 run 46131379965; blocked PR #35; fix PR #36 |
| Decision | HOLD: EC-1 met, EC-2 met, EC-3 not met |
| Commits since baseline on main | Zubair 50, Tawassul 12, Sami 11 (Sami's git name `i243070-beep`) |

# Part G. Troubleshooting and honesty

## G.1 If something goes wrong
| Problem | Fix |
| :--- | :--- |
| `PermissionError ... csp.log` after pytest | Windows cleanup message of the temp folder; the result line above it is what counts |
| port 8000 in use | close the old server (Ctrl+C) or `netstat -ano | findstr :8000` and end that process |
| pretix sends you back to the login page | the back-office session is tied to the browser's User-Agent; log in again in the same browser |
| `database is locked` in a manual run | stop parallel runs; SQLite allows one writer |
| Docker commands fail | start Docker Desktop and wait until it says running |
| SonarQube coverage 0 % | the coverage XML `<source>` must point at `src` (see C.1 step 7) |
| `git push` asks for login | `gh auth login` or sign in in the Git Credential Manager window |
| tests slow on battery | plug in the laptop; Area 3 needs about 6 minutes |

## G.2 Honesty rules for the viva

* Never claim a number you cannot show; open the saved output instead.
* AI use is allowed only if disclosed and checked. Our record: `src/tests/team/shared_management/AI_USE_DISCLOSURE_LOG.md`
  (rows 1-24) and prompts in `ai_prompts/`. Say what the tool produced and what **you checked** (runs, reading the
  code, comparing with pretix behaviour).
* The record also contains a correction note: unchecked evidence from 25-26 Nov (a mutation runner that printed fixed
  numbers, drawn screenshots, a pull request that never ran, defects D-01..D-08 never reproduced) was removed and
  replaced with real runs. If asked, explain this openly: it is in the git history.
* Each member must be able to explain every file in their area, including changes made by others (DV-5). Before the
  viva: Sami reads the Area 2 changes of 27 Nov (generator parameters, status coverage, decision tables, W-09..W-12);
  Tawassul reads the Area 3 changes (usability task tests, per-use-case Lighthouse, k6 re-run, RBAC log, the two CI
  fixes in `conftest.py` and `test_keyboard_nav.py`).
