# Requirements Traceability Matrix (RTM)

**System:** pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`. Requirements and rules are defined in `TEST_PLAN.md` section 1.2.
All paths are relative to `src/tests/team/`. Test counts are from `pytest --collect-only` on 2026-11-27.

## 1. Forward traceability (requirement -> tests)
| Req | Requirement | Rules | Unit / white-box (Area 1) | API / integration (Area 2) | E2E use case (Area 3) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FR-01 | Create product with price and sale window | BR-2 | `zubair/test_mcc_mcdc.py::test_mcc_i1_*`, `test_bva_i1_*` | `sami/api/test_api_ep_bva.py` (items) | UC-1 `test_uc1_*` | Pass; W-01, A3-D01 open (xfail) |
| FR-02 | Create quota and link products | BR-1 | `zubair/test_quota_availability_whitebox.py::TestVouchers`, `TestOrdersBoundary` (incl. variation quotas) | `test_api_ep_bva.py` (quotas) | UC-1 alt 2 | Pass |
| FR-03 | Change quota size | BR-1, cross-workflow | `test_quota_availability_whitebox.py::TestEarlyOuts` (size 0 / None), BVA size-1/size/size+1 | `sami/api/test_cross_workflow.py` | UC-2 | Pass; W-05 open |
| FR-04 | Control sale window / active flag | BR-2 | MCC I1 (18 feasible rows), BVA on both window ends | `test_negative_rules.py` rule 2 | UC-2 | Pass; W-07 open |
| FR-05 | Reserve tickets in a cart | BR-1, BR-4 | `TestCartsBR4` (expiry BVA now-1s/now/now+1s), `test_whitebox_cart_rules.py` | `test_api_ep_bva.py` (cartpositions) | UC-3 | Pass; W-02 open |
| FR-06 | Create order from cart | BR-1, BR-3 | `test_order_state_transitions.py`, `TestOrdersBoundary` | `test_api_ep_bva.py` (orders), `test_negative_rules.py` | UC-3 alt 1 | Pass; W-08 open |
| FR-07 | Redeem voucher | BR-1 | `TestVouchers` (blocking, quota-bound, variation, redeemed > max, GREATEST/MAX) | - | UC-4 | Pass |
| FR-08 | Order state changes | BR-3 | `test_order_state_transitions.py` (T1-T8, X1-X6), `test_whitebox_order_rules.py`, MCC O1 | `test_negative_rules.py` (9 allowed, 11 disallowed) | UC-6 | Pass |

## 2. Business rules
| Rule | Techniques | Area 1 evidence | Other areas | Status |
| :--- | :--- | :--- | :--- | :--- |
| BR-1 Capacity limit | BVA, statement/branch coverage, MCC Q3-Q7, mutation | `test_quota_availability_whitebox.py`, coverage gate, `mutation/results/` | API BVA on quota size, cross-workflow read-back; E2E UC-3 sold-out flow | Verified |
| BR-2 Purchasability | MCC (18 rows) + MC/DC (5 pairs), BVA | `test_mcc_mcdc.py` I1 | API rule 2 (W-07); UC-2 | Verified at unit level; API defect W-07 open |
| BR-3 Order state machine | State transition, MCC O1, branch coverage, custom operator `SwapOrderStatus` | `test_order_state_transitions.py`, `test_whitebox_order_rules.py` | API transitions; UC-6 | Verified |
| BR-4 Cart reservation | BVA on `expires`, MCC Q6 | `TestCartsBR4`, `test_whitebox_cart_rules.py` | cross-workflow; UC-3/UC-5 | Verified |

## 3. Backward traceability (test file -> requirement)
| Test file | Requirements / rules |
| :--- | :--- |
| `zubair/test_quota_availability_whitebox.py` | FR-02, FR-03, FR-05, FR-07; BR-1, BR-4 |
| `zubair/test_mcc_mcdc.py` | FR-01, FR-04, FR-08; BR-1..BR-4 (decisions Q1-Q7, I1, O1) |
| `zubair/test_order_state_transitions.py` | FR-06, FR-08; BR-3 |
| `zubair/test_whitebox_order_rules.py` | FR-08; BR-3 |
| `zubair/test_whitebox_quota_rules.py`, `test_whitebox_cart_rules.py` | FR-03, FR-05; BR-1, BR-4 |
| `zubair/test_custom_mutation_operators.py` | Mutation tooling (supports EC-2) |
| `sami/api/*.py` | FR-01..FR-08 at API level |
| `tawassul/usecases/test_e2e_usecases.py` | FR-01..FR-08 through UC-1..UC-6 |

## 4. Non-functional
| Area | Target | Evidence |
| :--- | :--- | :--- |
| Accessibility | 0 critical/serious axe violations on the fixed screen; Lighthouse accessibility >= 90 | `tawassul/usability_a11y/` |
| Security | Access decisions for 2+ roles, passive scan, dependency audit | `tawassul/security/` |
| Performance (EC-3) | p95 <= 500 ms, < 1 % failures, 1 and 5 VUs | `tawassul/performance/` |
| Recovery | No partial data after a failed write; retry gives exactly one order | `tawassul/performance/test_failure_recovery.py` |
| Test strength (EC-2) | Mutation score >= 85 % on `quotas.py` | `zubair/mutation/results/summary.json` |

## 5. Requirements coverage (GQM metric)
| Measure | Value |
| :--- | :--- |
| Functional requirements with at least one passing automated test | 8 / 8 = **100 %** |
| Functional requirements tested at all three levels (unit, API, E2E) | 7 / 8 = **87.5 %** (FR-07 vouchers has no API test) |
| Business rules verified at unit level | 4 / 4 = **100 %** |
| Requirements with an open defect | FR-01, FR-03, FR-04, FR-05, FR-06 (see defect log) |
