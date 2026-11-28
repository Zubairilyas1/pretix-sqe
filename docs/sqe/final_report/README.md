# Final report: how it is built and where the evidence comes from

The PDF `Project_24I-3142_24I-3070_24I-3100_B.pdf` is generated from the documents in this repository:

```bash
python docs/sqe/final_report/build_final_report.py --rolls 24I-3142,24I-3070,24I-3100 --section B
```

Each chapter is a repository document (included unchanged), followed by the evidence figures listed in
`figures_manifest.py`. Screenshots are embedded exactly as they were captured: no cropping, retouching or drawing.

## Evidence capture (all scripts run from the repository root)

| Figures | Script | What it does |
| :--- | :--- | :--- |
| `figures/pretix_*.png` | `capture/capture_pretix.py` | Starts a fresh local pretix (DEBUG off, waitress + whitenoise, own data folder `capture/.screens_data`, config `capture/screens_pretix.cfg`), seeds only the organizer, event and roles (`capture/seed_screens.py`), then performs W1 (product and quota) and W2 (purchase) and the back-office and access-control steps through the real web UI with Playwright/Chromium. |
| `figures/raw_tests/test_*.png` | Area 3 test suite with `SQE_SCREENSHOT_DIR=../docs/sqe/final_report/figures/raw_tests` | The hook in `src/tests/team/tawassul/conftest.py` saves the browser page at the end of every Playwright test, i.e. the screen on which the test's assertions were made. Off by default and in CI. |
| `figures/cov_*`, `mut_*`, `pytest_*`, `lh_*`, `zap_*`, `api_*` | `capture/capture_reports.py` | Opens the HTML reports written by coverage.py, Cosmic Ray, pytest-html, Lighthouse and OWASP ZAP in Chromium and takes screenshots; renders our OpenAPI spec with Swagger UI. The pytest-html reports are in `evidence_html/`. |
| `figures/sonar_*` | `capture/capture_sonar.py` | Starts SonarQube Community Build 25.1 in Docker, configures it exactly like CI Gate 4 (`src/tests/team/zubair/ci/sonar_setup.py`), analyses `quotas.py` with the Area 1 coverage report and the four W1/W2 files with pysonar, logs in and takes screenshots. |
| `figures/gh_*` | `capture/capture_github.py` | Screenshots of the public GitHub pages of the repository (logged-out browser, i.e. what any reviewer sees). |
| `figures/console_*` | `capture/capture_console.py` | Commands that only print text (GitHub CLI, pip-audit, git, the saved k6 summaries). The output is written unchanged to `console_<name>.txt` and rendered as an image whose frame shows the command, the working directory, the capture time and the repository commit. These figures are captioned "Console output". |

Run date of the captures: 28 Nov 2026, repository commits on branch `zubair` (shown in each console frame).
