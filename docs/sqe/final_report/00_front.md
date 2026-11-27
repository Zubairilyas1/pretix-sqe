# SE3002 Software Quality Engineering - Final Project Report

## Automated testing of the pretix ticketing MIS: ticket capacity and order workflows

| | |
| :--- | :--- |
| Team | Zubair (roll no. `ROLL_ZUBAIR`), Sami (roll no. `ROLL_SAMI`), Tawassul (roll no. `ROLL_TAWASSUL`) - Section `SECTION` |
| Public repository | https://github.com/Zubairilyas1/pretix-sqe |
| Upstream | https://github.com/pretix/pretix, licence AGPL-3.0 with pretix additional terms |
| Baseline commit | `c0d887738b6cd97f724b926718c55e2ae87c9901` |
| Report built from | repository commit `BUILD_COMMIT` on `BUILD_DATE` by `docs/sqe/final_report/build_final_report.py` |

## Area ownership
| Member | Area (brief section 6) | Main evidence |
| :--- | :--- | :--- |
| Zubair | (1) white-box unit testing, MCC/MC-DC, mutation testing, CI quality gate incl. SonarQube gate | `src/tests/team/zubair/`, `docs/sqe/zubair/`, `.github/workflows/sqe_quality_gate.yml` |
| Sami | (2) API testing and automated test-data generation | `src/tests/team/sami/` |
| Tawassul | (3) use cases, usability/accessibility, security, performance; SonarQube analysis of the W1/W2 files and the CFG calculation | `src/tests/team/tawassul/` |
| All | Test management (plan, estimation, risk register, RTM, defects/RCA/Pareto, progress, completion report, AI-use record) | `src/tests/team/shared_management/` |

## Release decision (summary)
**HOLD.** Actual vs target for the three release (exit) criteria - details in the Test Completion Report section:

| Criterion | Target | Actual | Met |
| :--- | :--- | :--- | :-: |
| EC-1 business-rule coverage, failing tests | 100 % statement + branch on scope; 0 failing | 100 % statements, 143/144 branches (1 infeasible, justified); 0 failing | Yes |
| EC-2 mutation score `quotas.py` | >= 85 % | RUN2_SCORE | Yes |
| EC-3 order performance | 1 user p95 <= 500 ms, 5 users p95 <= 1000 ms, < 1 % failures | 1 user 133 ms / 0 %; 5 users 527 ms / **72 % failures** | No |

Each later section is the corresponding document of the repository, included unchanged, so the report and the
repository cannot disagree. Paths in `code` font are relative to the repository root unless they start with
`zubair/`, `sami/`, `tawassul/` (= `src/tests/team/...`).
