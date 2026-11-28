# SonarQube analysis of the critical module `quotas.py` (Area 1)

Measured 27 Nov 2026 with SonarQube Community Build 25.1.0.102122 and pysonar 1.11.0 (official scanner), coverage
imported from the Area 1 suite. Evidence: `src/tests/team/tawassul/static_analysis/evidence/sonar_function_complexity.json`
(script `sonar_function_complexity.py`). The same analysis runs in CI as gate 4 (`.github/workflows/sqe_quality_gate.yml`).
The W1/W2 view files (`cart.py`, `items.py`, `orders.py`, `control/views/item.py`) are analysed by Area 3 in
`src/tests/team/tawassul/static_analysis/sonar_findings.md`.

| Metric | Value | What it shows |
| :--- | :-: | :--- |
| Lines of code (ncloc) | 357 | small module, but it decides availability for every sale |
| Cyclomatic complexity | 111 (12 functions) | about 9 decision points per function on average: many paths, which is why branch coverage and MCC were needed |
| Cognitive complexity | 174 | hard to read; `compute()` alone scores 42, `_compute_orders()` 36, `_compute()` 29 (limit 15) |
| Duplicated lines | 0.0 % | the four counting stages repeat a pattern but not literal code |
| Code smells | 7 | 5 x S3776 (cognitive complexity above 15), 1 x S1172 (unused parameter `now_dt` in `_write_cache`), 1 x S1066 (nested `if` that could be merged) |
| Bugs | 0 | reliability rating **A** |
| Vulnerabilities / security hotspots | 0 / 0 | security rating **A** |
| Technical debt | 102 min, debt ratio 1.0 % | maintainability rating **A** (A = ratio <= 5 %) |
| Coverage | 99.7 % (line 100 %, branch 99.3 %) | the only uncovered branch is the infeasible 361->363 (`COVERAGE_REPORT.md`) |

**What this means for quality and risk.**
* SonarQube finds no bug, but the high cognitive complexity of `compute()` and `_compute_orders()` is exactly where a
  defect can hide unnoticed: the white-box suite therefore targets these functions with MCC (Q1, Q2, Q5) and with the mutation run.
* Static analysis did **not** see D-Z01 (the waiting-list stage ignoring `now_dt`): the parameter was simply not passed,
  which is not a rule violation. It was found by white-box review - static analysis and testing complement each other.
* S1172 (unused `now_dt` in `_write_cache`) is the same kind of design smell as D-Z01; it is harmless there because the
  cache stores the computation time, but it points at an inconsistent use of "now" in the module.

**Hand calculation vs SonarQube.** The CFG of `Quota.availability()` (the shared-record entry point) was calculated by hand
in `src/tests/team/tawassul/static_analysis/cfg_cyclomatic.md` (V(G) = 6, three methods). SonarQube, run on that function
alone, reports **6** as well; both count the two `and` operators as decisions.
