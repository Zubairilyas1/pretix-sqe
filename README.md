# pretix-sqe: Software Quality Engineering Final Project (SE3002, Fall 2026)

Automated testing of the open-source MIS **pretix** (event ticketing): two related workflows
(organizer sets up ticket capacity, customer buys tickets) that share the `Quota` record.

| | |
| :--- | :--- |
| Upstream | https://github.com/pretix/pretix (AGPL-3.0 with pretix additional terms, see `LICENSE`) |
| Baseline commit | `c0d887738b6cd97f724b926718c55e2ae87c9901` |
| Team repository | https://github.com/Zubairilyas1/pretix-sqe |
| Our work | `src/tests/team/` (tests, tools, test management) and `docs/sqe/` (reports). Upstream tests are untouched and not part of our results. |

## Team and area ownership
| Member | Area (as defined in the brief) | Folder |
| :--- | :--- | :--- |
| Zubair | Area 1: white-box unit testing (100 % statement/branch, MCC, MC/DC), mutation testing (Cosmic Ray + 2 custom operators), CI quality gate incl. SonarQube gate | `src/tests/team/zubair/`, `docs/sqe/zubair/`, `.github/workflows/sqe_quality_gate.yml` |
| Sami | Area 2: OpenAPI spec, EP/BVA test-data generator, API and integration tests | `src/tests/team/sami/` |
| Tawassul | Area 3: use cases + Playwright, usability/accessibility, security, performance/recovery; SonarQube analysis of the W1/W2 files and the CFG hand calculation | `src/tests/team/tawassul/` |
| All | Test management: plan, estimation, risk register, RTM, defects + RCA + Pareto, progress, completion report, AI-use record | `src/tests/team/shared_management/` |

Workflows, requirements (FR-01..08), business rules (BR-1..4) and roles: `src/tests/team/shared_management/TEST_PLAN.md`.

## Reproduce

### 1. Install (Python 3.11; Node 24 only needed for Lighthouse)
```bash
git clone https://github.com/Zubairilyas1/pretix-sqe.git && cd pretix-sqe
git log --oneline | grep -m1 c0d887738          # baseline commit is in the history
uv venv --python 3.11                            # or: python -m venv .venv
uv pip install -e ".[dev]" -r src/tests/team/requirements-sqe.txt \
    -e src/tests/team/zubair/mutation/sqe_mutation_operators
.venv/bin/python -m playwright install chromium  # Windows: .venv\Scripts\python
```

### 2. Start the application (manual exploration)
```bash
cd src
../.venv/bin/python manage.py collectstatic --noinput
../.venv/bin/python manage.py migrate            # creates admin@localhost / admin
../.venv/bin/python manage.py runserver          # http://localhost:8000/control/
```

### 3. Seed test data
* Automated tests create their own synthetic data with fixtures (`src/tests/team/conftest.py`: organizer `sqe-org`, event `sqe-conf`, product "General Admission Ticket", quota 10). Nothing to seed.
* API test data is generated from the OpenAPI spec: `../.venv/bin/python tests/team/sami/generator/generate_test_data.py`.
* Data for manual runs and k6: `../.venv/bin/python manage.py shell -c "exec(open('tests/team/tawassul/performance/seed_perf_event.py').read())"`.

### 4. Reset between runs
* pytest-django recreates the test database for every test: no manual reset.
* Manual/k6 database: stop the server, delete `src/data/db.sqlite3`, run `migrate` again; the seed script also deletes and recreates its event.
* Mutation testing restores the source file after every mutant; `git status` must be clean afterwards.

### 5. Run the tests (from `src/`)
```bash
../.venv/bin/python -m pytest tests/team/zubair -q        # Area 1 (unit, MCC/MC-DC, state transitions)
../.venv/bin/python -m pytest tests/team/sami -q          # Area 2 (API + integration)
../.venv/bin/python -m pytest tests/team/tawassul -q      # Area 3 (Playwright E2E, a11y, RBAC, recovery)

# Area 1 coverage gate (100 % statement + branch on the business-rule scope)
../.venv/bin/python -m pytest tests/team/zubair --cov=pretix.base.services.quotas --cov=pretix.base.models.orders \
    --cov=pretix.base.models.items --cov-branch --cov-report=json:coverage-area1.json
../.venv/bin/python tests/team/zubair/coverage_gate.py coverage-area1.json
```
Mutation testing (from the repository root): `python src/tests/team/zubair/mutation/run_mutation.py --workers 6 --fail-under 85`

## Tool versions
Python 3.11.15, Django 5.2.19, pytest 9.2.0, pytest-django 4.14.0, pytest-cov 7.1.0, coverage.py 7.17.5, fakeredis 2.40.0,
Cosmic Ray 8.9.0, Playwright 1.65.2 (Chromium), axe-playwright-python 0.1.9, Lighthouse 12.8.2, OWASP ZAP 2.17.0, pip-audit,
Grafana k6 OSS v0.57.0, SonarQube Community Build 25.1.0.102122 + sonar-scanner-cli 11.1 (CI) / pysonar 1.11.0 (local),
pytest-html 4.1.1, waitress 3.0.2 + whitenoise 6.9.0 (perf server), Node 24.18.0 + Lighthouse 12, GitHub Actions `ubuntu-latest`.
All extra Python packages are pinned in `src/tests/team/requirements-sqe.txt`.

## CI quality gate
`.github/workflows/sqe_quality_gate.yml` runs on every pull request: Area 1 tests + coverage gate, Area 2 tests, Area 3 Playwright tests,
SonarQube quality gate, Cosmic Ray mutation gate; the release-candidate "deploy" job runs only on `main` after all gates pass.
There is no `continue-on-error` and no `|| true`. Thresholds, the blocked pull request and the documented fix pull request:
`docs/sqe/zubair/CI_QUALITY_GATE_REPORT.md`.

## Where to find things
| Deliverable | Location |
| :--- | :--- |
| Test plan, risk register, RTM, estimation | `src/tests/team/shared_management/` |
| Defect log, RCA, Pareto, GitHub Issues | `shared_management/CONSOLIDATED_DEFECT_LOG.md`, repository Issues tab |
| Progress and completion reports | `shared_management/PROGRESS_REPORTS.md`, `TEST_COMPLETION_REPORT.md` |
| AI-use record and prompts | `shared_management/AI_USE_DISCLOSURE_LOG.md`, `shared_management/ai_prompts/` |
| Area 1 reports (coverage, MCC/MC-DC, mutation, CI) | `docs/sqe/zubair/` |
| Area 2 / Area 3 reports | `src/tests/team/sami/`, `src/tests/team/tawassul/`, `docs/sqe/reports/` |
