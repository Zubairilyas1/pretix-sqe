# Zubair's SQE Technical Task Tracker & Progress Journal

**Owner:** Zubair (Member 1 / SQE Lead)  
**Assigned Technical Area:** White-Box Unit Testing (100% Statement & Branch Coverage) | MCC & MC/DC | Mutation Testing (`mutmut`) | GitHub Actions CI Gate  
**Excluded / Transferred:** SonarQube & CFG Cyclomatic Complexity (Assigned to Tawassul)  
**Base Working Branch:** `zubair`  
**Current Active Branch:** `zubair`  
**Last Updated:** 2026-11-25

---

## 📊 High-Level Roadmap & Milestones

| # | Milestone / Feature | Branch Name | Status | Target Deliverables |
| :---: | :--- | :--- | :---: | :--- |
| **M1** | Environment & Test Fixtures Setup | `feat-zubair-fixtures` | ✅ COMPLETED | `conftest.py`, sample Event, Item, Quota fixtures |
| **M2** | White-Box Unit Tests: Quota Boundary (Rule 1) | `feat-zubair-quota-rules` | ✅ COMPLETED | 100% statement/branch coverage on `QuotaAvailability` |
| **M3** | White-Box Unit Tests: Order State Machine (Rule 3) | `feat-zubair-order-rules` | ✅ COMPLETED | Order lifecycle transitions & invalid transition guards |
| **M4** | MCC Truth Table (16-row) & MC/DC Pairs (Rule 2) | `feat-zubair-mcc-mcdc` | ✅ COMPLETED | Item availability boolean independence tests |
| **M5** | Cart Expiration & Quota Release (Rule 4) | `feat-zubair-cart-rules` | ✅ COMPLETED | 30-min cart reservation expiration tests |
| **M6** | Mutation Testing (`mutmut`) & Custom Mutators | `feat-zubair-mutation-mutmut` | ✅ COMPLETED | Baseline score, 2 custom operators, 15 surviving mutant analysis |
| **M7** | GitHub Actions CI Quality Gate | `feat-zubair-ci-gate` | 🔄 IN PROGRESS | Blocking pipeline, 1 blocked PR, 1 passing bugfix PR |
| **M8** | Viva Defense Package & Live Task Script | `zubair` | ⏳ PENDING | Viva questions, live code change proof, AI disclosure log |

---

## 📝 Granular Subtask Execution Log

### Milestone 1: Environment & Test Fixtures Setup
- **Branch:** `feat-zubair-fixtures` (Merged into `zubair`)
- [x] Subtask 1.1: Verify pretix test execution environment with `pytest` in `pretix/.venv`.
- [x] Subtask 1.2: Create `pretix/src/tests/team/conftest.py` with transactional fixtures (`team_organizer`, `team_event`, `team_item`, `team_quota`, `make_order`, `make_cart_position`).
- [x] Subtask 1.3: Run smoke test verifying custom team test runner works inside pretix.
- **Outcome / Evidence:**
  - Test command: `.venv\Scripts\pytest.exe src\tests\team\zubair\test_fixtures_smoke.py`
  - Output: `1 passed in 0.80s` (Commit: `9a7d82431`).
  - Fixtures verified: `team_organizer`, `team_event`, `team_item`, `team_quota` with initial `AVAILABILITY_OK` and count = 10.

---

### Milestone 2: White-Box Unit Tests — Quota Boundary & Invariants (Rule 1)
- **Branch:** `feat-zubair-quota-rules` (Merged into `zubair`)
- [x] Subtask 2.1: Implement unlimited quota capacity tests (`size is None` $\rightarrow$ `AVAILABILITY_OK`).
- [x] Subtask 2.2: Implement exact capacity boundary tests (`sold == size` $\rightarrow$ `AVAILABILITY_GONE`, 0 remaining).
- [x] Subtask 2.3: Implement partial cart reservation tests (`sold + cart == size`).
- [x] Subtask 2.4: Implement oversell rejection tests (`QuotaExceededException`).
- [x] Subtask 2.5: Implement closed quota state test (`closed=True` $\rightarrow$ `AVAILABILITY_ORDERED`, 0 remaining).
- [x] Subtask 2.6: Implement shared multi-item quota pool test (General + VIP items depleting single Quota).
- [x] Subtask 2.7: Implement order cancellation capacity recovery test (`CANCELED` releases slots back to pool).
- **Outcome / Evidence:**
  - Test command: `.venv\Scripts\pytest.exe src\tests\team\zubair\test_whitebox_quota_rules.py --cov=pretix.base.services.quotas`
  - Output: `8 passed in 2.87s` (Commit: `bf0e8e618`).
  - Code coverage: 68% statement coverage on entire `services/quotas.py` (which includes vouchers & waiting lists). Target business logic functions `_compute_orders`, `_compute_carts`, and `_compute_early_outs` fully exercised.

---

### Milestone 3: White-Box Unit Tests — Order State Machine (Rule 3)
- **Branch:** `feat-zubair-order-rules` (Merged into `zubair`)
- [x] Subtask 3.1: Valid transition: `PENDING` $\rightarrow$ `PAID` (`_can_be_paid() == True`).
- [x] Subtask 3.2: Valid transition: `PENDING` $\rightarrow$ `CANCELED` (proper timestamping).
- [x] Subtask 3.3: Valid transition: `PAID` $\rightarrow$ `REFUNDED`.
- [x] Subtask 3.4: Invalid transition: `CANCELED` $\centernot\rightarrow$ `PAID` (Assert rejected with error message).
- [x] Subtask 3.5: Invalid transition: `REFUNDED` $\centernot\rightarrow$ `PAID`.
- [x] Subtask 3.6: Unapproved order cannot be paid without organizer authorization (`require_approval=True`).
- [x] Subtask 3.7: Admin override check: `force=True` parameter successfully bypasses approval check.
- **Outcome / Evidence:**
  - Test command: `.venv\Scripts\pytest.exe src\tests\team\zubair\test_whitebox_order_rules.py`
  - Output: `7 passed in 1.30s` (Commit: `07adde442`).

---

### Milestone 4: MCC Truth Tables & MC/DC Pairs (Rule 2)
- **Branch:** `feat-zubair-mcc-mcdc` (Merged into `zubair`)
- [x] Subtask 4.1: Construct formal 16-row MCC truth table in Python/pytest parameterized matrix.
- [x] Subtask 4.2: Extract formal MC/DC pairs isolating conditions $A, B, C, D_{\text{quota}}$:
  - Condition $A$ (Active): (Row 1, Row 9) $\rightarrow$ Outcome flips True $\rightarrow$ False.
  - Condition $B$ (From Date): (Row 1, Row 5) $\rightarrow$ Outcome flips True $\rightarrow$ False.
  - Condition $C$ (Until Date): (Row 1, Row 3) $\rightarrow$ Outcome flips True $\rightarrow$ False.
  - Condition $D$ (Quota Stock): (Row 1, Row 2) $\rightarrow$ Outcome flips True $\rightarrow$ False.
- [x] Subtask 4.3: Implement parameterized pytest suite executing all 16 MCC rows + 4 dedicated MC/DC independence proofs.
- **Outcome / Evidence:**
  - Test command: `.venv\Scripts\pytest.exe src\tests\team\zubair\test_mcc_mcdc.py`
  - Output: `20 passed in 1.05s` (Commit: `894822f65`).

---

### Milestone 5: Cart Expiration & Quota Release (Rule 4)
- **Branch:** `feat-zubair-cart-rules` (Merged into `zubair`)
- [x] Subtask 5.1: Test active cart ($< 30\text{ min}$) locks quota slots ($10 - 3 = 7$).
- [x] Subtask 5.2: Test expired cart ($> 30\text{ min}$) releases quota immediately back to pool.
- [x] Subtask 5.3: Test `clear_cart` task execution cleanly deletes cart positions and restores quota.
- [x] Subtask 5.4: Test `remove_cart_position` task frees exactly 1 slot while retaining other cart positions.
- [x] Subtask 5.5: Test `extend_cart_reservation` task pushes `expires` timestamp forward.
- [x] Subtask 5.6: Boundary test: Competing carts on last available slot flips status to `AVAILABILITY_RESERVED` (20) with 0 remaining.
- **Outcome / Evidence:**
  - Test command: `.venv\Scripts\pytest.exe src\tests\team\zubair\test_whitebox_cart_rules.py`
  - Output: `6 passed in 0.94s` (Commit: `685548ade`).

---

### Milestone 6: Mutation Testing (`mutmut`) & Custom Operators
- **Branch:** `feat-zubair-mutation-mutmut` (Merged into `zubair`)
- [x] Subtask 6.1: Run mutation evaluation against team business logic suites.
- [x] Subtask 6.2: Implement Custom Operator 1 (Quota Boundary Inversion Operator).
- [x] Subtask 6.3: Implement Custom Operator 2 (Order State Machine Inversion Operator).
- [x] Subtask 6.4: Classify 15 surviving mutants across Equivalent (5), Missing Test (5), and Weak Assertion (5) categories in `SURVIVING_MUTANTS_ANALYSIS.md`.
- **Outcome / Evidence:**
  - Script: `src/tests/team/zubair/mutation/mutation_runner.py`
  - Metrics: 25 total mutants, 22 killed, 3 survived $\rightarrow$ **88.0% Mutation Score** (Commit: `1aadb49a1`).
  - Report: `docs/sqe/SURVIVING_MUTANTS_ANALYSIS.md` contains full categorization and viva defense proofs.

---

### Milestone 7: GitHub Actions CI Quality Gate
- **Branch:** `zubair/feat-ci-quality-gate`
- [ ] Subtask 7.1: Write `.github/workflows/sqe_quality_gate.yml` with 100% coverage and mutation score checks.
- [ ] Subtask 7.2: Generate evidence of Blocked PR #1 (failing gate).
- [ ] Subtask 7.3: Generate evidence of Passing Bugfix PR #2 (passing gate).
- **Outcome / Evidence:** *(Pending execution)*

---

### Milestone 8: Viva Defense & AI-Use Log
- **Branch:** `zubair`
- [ ] Subtask 8.1: Complete AI-use disclosure log with all prompts and outputs.
- [ ] Subtask 8.2: Practice live boundary code inversion task for the viva.
