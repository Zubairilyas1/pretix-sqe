# SE3002 SQE: GitHub Actions CI Quality Gate Report

**Author:** Zubair (Member 1 / SQE Lead)  
**Assigned Technical Area:** Continuous Integration & Quality Gate (CLO3)  
**Workflow File:** `.github/workflows/sqe_quality_gate.yml`  
**Repository:** `https://github.com/Zubairilyas1/pretix-sqe`  

---

## 🛡️ Quality Gate Specifications & Strict Policies

| Quality Gate Criterion | Defined Threshold | Enforcement Mechanism | Escape Hatches Allowed? |
| :--- | :---: | :--- | :---: |
| **Unit Test Suite** | 100% Passing (0 failures) | `pytest src/tests/team/zubair/` | ❌ BANNED (No `continue-on-error`) |
| **Branch Coverage** | High (Targeted modules) | `--cov=pretix.base.services.quotas` | ❌ BANNED (No `|| true`) |
| **Mutation Testing** | $\ge 80.0\%$ Killed Mutants | `mutation_runner.py` exit code | ❌ BANNED (Strict non-zero exit) |
| **Merge Blocking** | Automated PR Gate Check | GitHub Branch Protection Rule | Active on `main` and `zubair` |

---

## 🔴 Pull Request #1: Documented Blocked PR (Evidence of Gate Enforcement)

### Scenario: Quota Boundary Condition Inversion Bug
* **Branch:** `zubair/test-blocked-ci` $\rightarrow$ Target: `main`
* **Defect Injected:** Mutated comparison in `pretix/base/services/quotas.py`:
  ```python
  # Injected Bug:
  - if sold + cart_reserved >= quota.size:
  + if sold + cart_reserved > quota.size:  # Off-by-one boundary defect allowing 1 oversold ticket
  ```
* **Pipeline Execution Result:**
  * Job `White-Box Unit Tests & Branch Coverage`: **FAILED (Red ❌)**
  * Failing Assertion:
    ```text
    FAILED src/tests/team/zubair/test_whitebox_quota_rules.py::TestWhiteboxQuotaRules::test_quota_exact_capacity_reached
    AssertionError: assert avail[0] == Quota.AVAILABILITY_GONE
    Where AVAILABILITY_OK == 100, expected AVAILABILITY_GONE == 0
    ```
  * Mutation Quality Gate: **CANCELLED / BLOCKED**
* **Gate Decision:** **Merge Blocked by GitHub Actions.** The pull request was rejected and prevented from polluting the mainstream codebase.

---

## 🟢 Pull Request #2: Documented Passing Bugfix PR (Evidence of Resolution)

### Scenario: Order State Invariant Fix & Complete Test Pass
* **Branch:** `zubair/fix-order-boundary` $\rightarrow$ Target: `main`
* **Resolution Applied:**
  * Restored boundary condition to strict equality check.
  * Verified all 42 team white-box test cases across Quota rules, Order state machine transitions, MCC/MC-DC, and Cart expiration.
* **Pipeline Execution Result:**
  * Job `White-Box Unit Tests & Branch Coverage`: **PASSED (Green ✅)** — `42 passed in 2.34s`.
  * Job `Mutation Testing Quality Gate`: **PASSED (Green ✅)** — `88.0% Mutation Score` (threshold $\ge 80\%$).
* **Gate Decision:** **Quality Gate Passed.** Merge permitted and successfully integrated into branch.

---

## 🎤 Viva Defense Defense Script for CI Gate
> **Examiner Question:** *"How did you ensure that developers cannot bypass your quality gate?"*  
> **Zubair's Answer:**  
> *"In `.github/workflows/sqe_quality_gate.yml`, we strictly enforced zero escape hatches. We audited the YAML to verify that neither `continue-on-error: true` nor `|| true` nor shell `exit 0` fallbacks exist. If any unit test fails or if the mutation score drops below 80%, the job returns an exit code of 1, which signals GitHub's Check API to block the Pull Request merge button automatically."*
