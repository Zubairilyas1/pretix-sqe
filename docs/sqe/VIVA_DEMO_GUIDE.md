# Viva demo guide: showing every tool live

All commands are run in PowerShell from the repository folder `D:\5th Semester\4.SQE\Project\pretix` unless the
line starts with `cd src`. Docker Desktop must be running for SonarQube and ZAP.

## Logins (local test data only)
| Where | User | Password | Created by |
| :--- | :--- | :--- | :--- |
| pretix back office (organizer, full rights) | `organizer@sqe.test` | `Sqe-Organizer-2026!` | `seed_perf_event.py` (port 8000) and `capture/seed_screens.py` (port 8001) |
| pretix back office (viewer, read-only orders) | `viewer@sqe.test` | `Sqe-Viewer-2026!` | `capture/seed_screens.py` |
| pretix admin of a fresh database | `admin@localhost` | `admin` | `manage.py migrate` |
| SonarQube (local Docker) | `admin` | `Sqe-Ci-Only-Password-1` | `src/tests/team/zubair/ci/sonar_setup.py` (changes the default `admin`/`admin`) |
| Customer | no account; any e-mail at checkout, e.g. `customer@sqe.test` | | |

## 1. pretix in the browser (W1 and W2)
```powershell
cd src
$env:PRETIX_CONFIG_FILE = "tests/team/tawassul/performance/perf_pretix.cfg"
../.venv/Scripts/python manage.py migrate
../.venv/Scripts/python manage.py shell -c "exec(open('tests/team/tawassul/performance/seed_perf_event.py').read())"
../.venv/Scripts/python tests/team/tawassul/performance/perf_server.py
```
* Back office: http://localhost:8000/control/ (organizer login above) -> event *Perf Conference* -> Products / Quotas.
* Shop (customer): http://localhost:8000/perf-org/perf-conf/
* Stop with Ctrl+C. The seed script resets the event, so it can be run again before every demo.

## 2. Automated tests (watch the browser with `--headed`)
```powershell
cd src
../.venv/Scripts/python -m pytest tests/team/zubair -q                                  # Area 1 (218 tests, ~15 s)
../.venv/Scripts/python -m pytest tests/team/sami -q                                    # Area 2 (~2 min)
../.venv/Scripts/python -m pytest tests/team/tawassul/usecases -k uc3_main --headed --slowmo 500   # one use case, visible
../.venv/Scripts/python -m pytest tests/team/tawassul -q                                # Area 3 (~6 min)
```

## 3. Coverage (Area 1)
```powershell
cd src
../.venv/Scripts/python -m pytest tests/team/zubair --cov=pretix.base.services.quotas --cov-branch --cov-report=html:../htmlcov --cov-report=json:../coverage-area1.json -q
../.venv/Scripts/python tests/team/zubair/coverage_gate.py ../coverage-area1.json
start ../htmlcov/index.html
```

## 4. Mutation testing (Cosmic Ray, custom operators)
A full run takes about an hour locally; for a live demo run one slice (about 18 mutants, 2-3 minutes):
```powershell
.venv/Scripts/python src/tests/team/zubair/mutation/run_mutation.py --workers 4 --shard 0/40 --out mutation-demo
start mutation-demo/report.html
```
Committed full results: `src/tests/team/zubair/mutation/results/run2_after_kills/report.html` (96.78 %).

## 5. SonarQube
```powershell
docker run -d --name sqe-sonar -p 9000:9000 sonarqube:25.1.0.102122-community
.venv/Scripts/python src/tests/team/zubair/ci/sonar_setup.py --coverage-threshold 99    # wait ~2 min; prints SONAR_TOKEN=...
cd src; ../.venv/Scripts/python -m pytest tests/team/zubair -q --ignore=tests/team/zubair/test_custom_mutation_operators.py --cov=pretix.base.services.quotas --cov-branch --cov-report=xml:../coverage-sonar.xml; cd ..
.venv/Scripts/pysonar --sonar-host-url=http://localhost:9000 --sonar-token=<SONAR_TOKEN> --sonar-project-key=pretix-sqe-quotas -Dsonar.sources=src/pretix/base/services/quotas.py -Dsonar.python.coverage.reportPaths=coverage-sonar.xml -Dsonar.scm.disabled=true
```
Open http://localhost:9000 (login above). If the coverage shows 0 %, replace the `<source>` line in
`coverage-sonar.xml` with `<source>src</source>` (as `docs/sqe/final_report/capture/capture_sonar.py` does) and scan again.
Remove afterwards: `docker rm -f sqe-sonar`. One command that does all of this and takes screenshots:
`.venv/Scripts/python docs/sqe/final_report/capture/capture_sonar.py`.

## 6. Lighthouse and axe (pretix running as in section 1)
```powershell
npx lighthouse http://localhost:8000/perf-org/perf-conf/ --only-categories=accessibility,best-practices,seo --view
cd src; ../.venv/Scripts/python -m pytest tests/team/tawassul/usability_a11y/test_axe_scan.py -q
```
Saved reports: `src/tests/team/tawassul/usability_a11y/reports/*.report.html` (before/after and UC1-UC6).

## 7. OWASP ZAP (pretix running as in section 1, Docker running)
```powershell
cd src; ../.venv/Scripts/python tests/team/tawassul/security/zap_scan.py
```
Report: `src/tests/team/tawassul/security/evidence/zap_report.html`.

## 8. k6 load test (pretix running and seeded as in section 1)
k6 v0.57.0 for Windows: https://github.com/grafana/k6/releases/tag/v0.57.0 (zip, contains `k6.exe`).
The seed script prints `item=<id>` and writes the API token to `src/tests/team/tawassul/performance/.perf_token`.
```powershell
cd src/tests/team/tawassul/performance
k6.exe run -e BASE=http://localhost:8000 -e VUS=1 -e P95=500 -e TOKEN=(Get-Content .perf_token) -e ITEM=<id> k6_order_create.js
```
Saved outputs: `results_v2/wl1a.txt` ... `wl5b.txt`.

## 9. API spec (Swagger UI) and test-data generator
```powershell
start docs/sqe/final_report/evidence_html/swagger_ui.html
cd src; ../.venv/Scripts/python tests/team/sami/generator/generate_test_data.py
```

## 10. GitHub (CI, blocked PR, fix PR, issues)
* Workflow runs: https://github.com/Zubairilyas1/pretix-sqe/actions
* Green pull request with all gates: https://github.com/Zubairilyas1/pretix-sqe/pull/15
* Blocked pull request: https://github.com/Zubairilyas1/pretix-sqe/pull/35
* Fix pull request (red, then green): https://github.com/Zubairilyas1/pretix-sqe/pull/36
* Defects: https://github.com/Zubairilyas1/pretix-sqe/issues
* Branch protection (admin only): repository Settings -> Branches -> `main`
