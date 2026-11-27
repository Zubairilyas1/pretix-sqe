# Zubair - Area 1 task tracker

**Area:** white-box unit testing (100 % statement + branch, MCC, MC/DC), mutation testing, CI quality gate (incl. SonarQube gate).
**Branch:** `zubair`. Reports: `docs/sqe/zubair/`. Last update: 2026-11-27.

| # | Milestone | Status | Evidence |
| :-: | :--- | :--- | :--- |
| M1 | Shared team fixtures + smoke test | Done 25 Nov | `src/tests/team/conftest.py`, `zubair/test_fixtures_smoke.py` |
| M2 | White-box suite for `QuotaAvailability` - 100 % statements, 143/144 branches (1 infeasible) | Done 27 Nov (redo) | `zubair/test_quota_availability_whitebox.py`, `COVERAGE_REPORT.md` |
| M3 | BR-3: `_can_be_paid` branch coverage + state transitions through the real services (8 allowed, 6 disallowed) | Done 27 Nov (redo) | `test_whitebox_order_rules.py`, `test_order_state_transitions.py` |
| M4 | MCC (58 rows) + MC/DC (23 pairs) on real pretix decisions; pairs validated by a test | Done 27 Nov (redo) | `test_mcc_mcdc.py`, `MCC_MCDC_TABLES.md` |
| M5 | BR-4 cart expiry BVA, cart services | Done | `test_whitebox_cart_rules.py`, `TestCartsBR4` |
| M6 | Mutation testing with Cosmic Ray, 2 custom operators as plug-in, >= 15 survivors analysed, killable ones killed | Done 27 Nov (redo) | `zubair/mutation/`, `MUTATION_REPORT.md` |
| M7 | CI gate: all suites, coverage gate, SonarQube gate, mutation gate, gated deploy | Done 27 Nov (redo) | `.github/workflows/sqe_quality_gate.yml`, `CI_QUALITY_GATE_REPORT.md` |
| M8 | Blocked PR + documented fix PR (D-Z01) | Branches ready (`demo/ci-blocked-oversell`, `fix/dz01-waitinglist-now-dt`); PRs to be opened on GitHub | `CI_QUALITY_GATE_REPORT.md` |
| M9 | Shared management: plan, register, RTM, defects, progress, completion report, AI record | Done 27 Nov | `src/tests/team/shared_management/` |

## History note
The first version of M2, M4, M6 and M7 (25 Nov) was not valid: coverage was 61 %, the MCC table was applied to a
helper inside the test, the mutation script printed fixed numbers and the blocked PR never ran. These were withdrawn on
27 Nov and redone with real runs (see AI-use record, correction note, and risk PJ-INT-01).

## Viva preparation
* Re-run: `cd src && ../.venv/bin/python -m pytest tests/team/zubair -q` and the coverage gate (README section 5).
* Explain: the infeasible branch 361->363; MCC table Q3 and its MC/DC pairs; why I1 has 18 feasible rows.
* Mutation: show a survivor with `cosmic-ray apply`/the HTML report, explain one equivalent and one killed mutant.
* Live task: for a rule change (e.g. cart reservations counted only while `expires > now`), predict which tests fail
  (`TestCartsBR4::test_cart_expiry_bva[0-True]`, MCC Q6) and which gate turns red (Gate 1, then Gate 5).
