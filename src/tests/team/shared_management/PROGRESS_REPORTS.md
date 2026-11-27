# Progress Reports against the Test Plan (with GQM metrics)

All team work took place in **calendar week 48 (23-29 Nov 2026)**, so there is one weekly report, tracked at
daily checkpoints. Every number below was measured from the repository at the checkpoint commit on `main`
(test counts with `pytest --collect-only` on a worktree of that commit; defects from the defect logs of that commit).

## GQM model
| Goal | Question | Metric | Definition |
| :--- | :--- | :--- | :--- |
| G1 Decide whether W1/W2 can be released | Q1 How defective is the code under test? | **Defect density** | confirmed product defects / KLOC of the analysed W1/W2 code (8.11 KLOC = 7,701 ncloc of `cart.py`, `items.py`, `orders.py`, `control/views/item.py` from SonarQube + 409 lines of `quotas.py`) |
| | Q2 How much of the agreed requirements has been tested? | **Requirements coverage** | functional requirements FR-01..FR-08 with at least one passing automated test that exercises pretix code / 8 |
| | Q3 Are fixes reliable? | **Reopen rate** | issues reopened / issues closed (GitHub Issues) |
| | Q4 Is the plan on track? | Tests automated vs planned, open control actions | collected tests per area |

## Week 48 report

### Checkpoint data
| Checkpoint | Commit (`main`) | Area 1 tests | Area 2 tests | Area 3 tests | Confirmed defects | Defect density (/KLOC) | Req. coverage | Reopen rate |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| CP1 Wed 25 Nov, end of day | `8d2853623` | 42 | 0 | 0 | 0 | 0.00 | 4/8 = 50 % | n/a (no issues) |
| CP2 Thu 26 Nov, end of day | `c1ce6c2be` | 42 | 260 | 0 | 8 (W-01..W-08) | 0.99 | 7/8 = 87.5 % | n/a (no issues) |
| CP3 Fri 27 Nov, 09:39 (before audit) | `f8b19f3f7` | 42 | 260 | 65 | 14 (+A3-D01..D06) | 1.73 | 8/8 = 100 % | n/a (no issues) |
| CP4 Fri 27 Nov, after rework | `zubair` branch head | 218 | 520 | 68 | 19 (+D-Z01, W-09..W-12) | 2.34 | 8/8 = 100 % | 0 / 2 closed = 0 % |

Notes on the measurements:
* CP1 requirements coverage counts FR-02, FR-03, FR-05, FR-08. The Area 1 MCC tests of that date evaluated a helper written inside the test file, so FR-04 was **not** counted as covered by them.
* The defect log of CP3 also listed D-01..D-08. They had no reproduction, test or code change behind them, so they are not counted (see CP3 control action).

### Planned vs actual
| Plan item (Test Plan section 6) | Planned | Actual | Variance |
| :--- | :--- | :--- | :--- |
| Area 1 white-box + MCC | by CP2 | 42 tests at CP1, but coverage only 61 % on `quotas.py` and MCC not on pretix code | Behind on quality, ahead on date |
| Area 2 API + generator | by CP2 | 260 tests (243 pass, 17 strict xfail) at CP2 | On plan |
| Area 3 E2E, a11y, security, performance | by CP3 | 65 tests at CP3 | On plan |
| Defects as GitHub Issues | as found | none filed by CP3 | Behind |
| Mutation + CI gate with blocked PR | by CP3 | not real at CP3 (fixed numbers, PR never ran) | Behind |

### Control actions
| # | Checkpoint | Observation | Control action | Owner | Status |
| :-: | :--- | :--- | :--- | :--- | :--- |
| CA-1 | CP1 | API and E2E work not started; Area 1 done early | Sami starts API work on 25 Nov evening, Tawassul on 26 Nov; shared fixtures reused | Team | Done (CP2/CP3) |
| CA-2 | CP2 | 8 API weaknesses found but only tracked as strict xfail | File every confirmed defect as a GitHub Issue with severity, priority, triage | Sami | Open at CP3, done at CP4 |
| CA-3 | CP2 | Exit criteria not measurable for Area 1 ("high coverage") | Make EC-1/EC-2 numeric and tie them to the top risks | Zubair | Done at CP4 (Test Plan 7.2) |
| CA-4 | CP3 | Audit: Area 1 coverage 61 %, mutation numbers hard-coded, blocked PR never ran, D-01..D-08 unverified, terminal images drawn by a script | Freeze the reports; remove the unsupported artefacts; redo coverage, MCC, mutation and CI with real runs; risk PJ-INT-01 raised to 20 | Zubair | Done at CP4 |
| CA-5 | CP3 | No test plan, progress or completion report documents | Write them from measured data | Zubair (shared) | Done at CP4 |
| CA-6 | CP4 | Area 2/3 gaps found in the audit (API error codes, parameter EP/BVA, decision tables, regeneration verify, usability task tests, SEO audit, k6 ramp-up and pre-set limits, SonarQube V(G) measurement, RBAC evidence) | Closed on the `zubair` branch at the team's request; owners review before the viva | Zubair (Sami, Tawassul review) | Done |

### Reading the metrics
* **Defect density** rose from 0 to 2.34 per KLOC because the API and E2E levels started finding real defects (the extended generator found four more, W-09..W-12); Area 1 white-box testing found one (D-Z01). The density is high for a mature project but most defects are input-validation gaps in the REST API (Pareto, defect log).
* **Requirements coverage** reached 100 % at CP3, but only 7/8 requirements are tested at all three levels (FR-07 has no API test).
* **Reopen rate** could not be measured before CP4 because no issue tracker was used (CA-2). This is itself a process finding.
