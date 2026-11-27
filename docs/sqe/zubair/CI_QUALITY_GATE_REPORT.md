# CI quality gate (Area 1, Zubair)

Workflow: `.github/workflows/sqe_quality_gate.yml`. Trigger: **every pull request**, pushes to `main` and the member
branches, manual dispatch. Runner: GitHub Actions `ubuntu-latest`, Python 3.11.

## 1. Gates
| # | Job | Blocks when | Evidence uploaded |
| :-: | :--- | :--- | :--- |
| 1 | Unit tests + 100 % business-rule coverage | any Area 1 test fails, or `coverage_gate.py` finds an uncovered statement/branch in the business-rule scope (except the one documented infeasible branch) | JUnit XML, coverage JSON/XML/HTML |
| 2 | API and integration tests | any Area 2 test fails, or a strict xfail unexpectedly passes (a tracked defect changed behaviour) | JUnit XML |
| 3 | Playwright E2E, accessibility, RBAC, recovery | any Area 3 test fails | JUnit XML, Playwright HTML report |
| 4 | SonarQube quality gate | SonarQube project gate is ERROR (`sonar.qualitygate.wait=true` makes the scanner exit non-zero) | measures JSON |
| 5 | Mutation score | Cosmic Ray mutation score on `quotas.py` < threshold | session DB, text and HTML report, summary, survivors |
| - | Deploy release candidate | runs **only** on `main` and **only** if gates 1-5 succeeded (`needs:`); packages the source archive + SHA256 | release-candidate artifact |

**No escape hatches:** the workflow contains no `continue-on-error`, no `|| true`, no `exit 0` fallback and no
`if: always()` on a gate step (`always()` is used only on artifact uploads, which cannot turn a failed job green).
Check: `grep -nE "continue-on-error|\|\| *true|exit 0" .github/workflows/sqe_quality_gate.yml` returns nothing.

**Merge blocking:** branch protection on `main` requires the five gate checks to pass before a pull request can be merged
(Settings -> Branches -> `main` -> "Require status checks to pass": `Gate 1 ...` to `Gate 5 ...`).

## 2. Thresholds and why
| Gate | Threshold | Justification from the evidence |
| :--- | :--- | :--- |
| Coverage (gate 1) | **100 %** statement and branch on the scope, 1 allowed branch | The brief requires 100 %; measured 239/239 statements and 143/144 branches. The only gap is infeasible and named in `coverage_gate.py`, so any new gap fails. |
| SonarQube coverage (gate 4) | **>= 99 %** on `quotas.py` | SonarQube mixes line and condition coverage; with the infeasible branch the best possible value is just under 100 %. 99 % catches a regression of several lines; single-line regressions are already caught by gate 1. |
| SonarQube ratings (gate 4) | reliability **A** (no bug), security **A** (no vulnerability), maintainability **A** (debt ratio <= 5 %), duplication **<= 3 %** | The team scan of the W1/W2 files measured 1.2 % duplication, security A and maintainability A (`tawassul/static_analysis/evidence/sonar_measures.json`); `quotas.py` passed all four on the first CI run. A new bug or vulnerability in the critical module must stop the merge. |
| Mutation (gate 5) | **>= 85 %** | Measured 90.91 % before and 96.78 % after the survivor analysis (`MUTATION_REPORT.md`). The remaining survivors are equivalent mutants, so 100 % is impossible; 85 % keeps a margin for new code while still failing if a substantial part of the tests is removed or weakened. |

## 3. Blocked pull request (pipeline stops a defect)
Branch `demo/ci-blocked-oversell`, commit "demo(ci): change sold-out check in quota orders stage from <= 0 to < 0".
The change makes a quota with exactly `size` sold tickets look available (off-by-one oversell, risk PR-WB-01).

| Expected gate result | Tests that must fail |
| :--- | :--- |
| Gate 1 **fails** | `TestOrdersBoundary::test_paid_orders_bva[5-expected1]`, `test_pending_orders_reaching_limit_are_ordered_not_gone`, MCC `test_mcc_q5_orders_verdict[Q5-1]`, state transition `test_t4_paid_to_canceled` (quota read-back) and others |
| Gate 5 skipped (needs gate 1) | - |
| Merge button | blocked by branch protection |

Evidence: pull request link and run link: _filled in after the PR has run_ (section 5).

## 4. Documented fix through a pull request (fails before, passes after)
Defect **D-Z01** (GitHub Issue, see defect log): `QuotaAvailability` ignored `now_dt` for the waiting-list auto-disable date.
Branch `fix/dz01-waitinglist-now-dt`:
1. commit `test(quota): add regression test for D-Z01 ...` - adds `test_dz01_waitinglist_now_dt.py`; **gate 1 fails** (`assert 1 == 0` for the day-after-tomorrow case);
2. commit `fix(quota): evaluate waiting-list auto-disable at now_dt (D-Z01)` - passes `now_dt` to `_compute_waitinglist`; **all gates pass**; the PR closes the issue.

Locally verified: before the fix `1 failed, 1 passed`; after the fix the Area 1 suite and pretix's own `tests/base/test_models.py` pass (408 passed).

## 5. Evidence links
| Item | Link |
| :--- | :--- |
| First run of the new workflow (push to `zubair`) | https://github.com/Zubairilyas1/pretix-sqe/actions/runs/45969206974 - gate 1 and gate 4 passed; gates 2 and 3 failed with pytest exit code 2 because the team's extra packages were not installed. Fixed in commit "ci(sqe): install the pinned extra packages ..." |
| Blocked PR | _to be added_ |
| Fix PR (red run, green run) | _to be added_ |
| Branch protection screenshot | _to be added (real screenshot of the GitHub settings page)_ |
