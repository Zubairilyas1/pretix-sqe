# SE3002 SQE: Requirements Traceability Matrix (RTM)

**Course:** SE3002 – Software Quality Engineering  
**Target MIS:** `pretix` at upstream baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`  
**Team Members:** Zubair (Area 1), Sami (Area 2), Tawassul (Area 3)  
**Location:** `src/tests/team/shared_management/REQUIREMENTS_TRACEABILITY_MATRIX_RTM.md`

---

## 1. System Requirements & Business Rules Summary

- **Workflow 1 (W1): Event Organizer Setup**
  - **FR-01:** Organizer creates ticket items with price, description, and sale dates.
  - **FR-02:** Organizer creates capacity pools (Quotas) linked to items.
  - **FR-03:** Organizer modifies Quota size (capacity expansion or contraction).
  - **FR-04:** Organizer publishes event and controls presale opening/closing.
- **Workflow 2 (W2): Customer Ticket Purchase & Checkout**
  - **FR-05:** Customer selects items and reserves positions in a shopping cart.
  - **FR-06:** System places an Order from cart positions within reservation TTL.
  - **FR-07:** Customer applies discount/promotional Vouchers to order.
  - **FR-08:** Customer or Organizer triggers Order state transitions (Pending $\to$ Paid, Canceled, Expired, Refunded).
- **Cross-Workflow Dependency:**
  - Shared record: `Quota`. Capacity pool created and resized by W1, consumed by W2 cart positions and orders, and released back to the pool upon cart expiry or order cancellation.
- **Business Rules:**
  - **BR-1 (Boundary / Numerical Limit):** Quota capacity limit. Available slots = `size - (paid_orders + pending_orders + active_cart_positions)`. An order/cart request exceeding available quota must be rejected. Per-order min/max quantity limits enforced.
  - **BR-2 (Decision with Multiple Conditions):** Item Purchasability. An item is purchasable if and only if:
    $$\text{Active} \land (\text{Now} \ge \text{AvailableFrom}) \land (\text{Now} \le \text{AvailableUntil}) \land (\text{QuotaStock} > 0)$$
  - **BR-3 (State Change Rule):** Order State Machine. Allowed transitions: Pending $\to$ Paid, Pending $\to$ Canceled, Pending $\to$ Expired, Paid $\to$ Refunded, Paid $\to$ Canceled, Expired $\to$ Paid, Canceled $\to$ Reactivated. All other transitions (e.g., Canceled $\to$ Paid, Refunded $\to$ Paid) are strictly rejected.
  - **BR-4 (Domain-Specific Business Rule):** Cart Reservation Expiry & Quota Restoration. Cart reservations hold quota slots strictly until `expires` timestamp. Once expired, slots are released instantly to other buyers without manual intervention.

---

## 2. Complete Forward & Backward Traceability Matrix

| Req ID | Description | Rule / Use Case | Test ID / Scenario | Automated Test Script | Method / Function Tested | Outcome |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **FR-01** | Create ticket item with price | BR-1, BR-2 | WB-ITEM-01<br>API-ITEM-01<br>UC1-MAIN | `tests/team/zubair/test_whitebox_quota_rules.py`<br>`tests/team/sami/api/test_api_ep_bva.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `ItemSerializer.create`<br>`Item.objects.create`<br>`test_uc1_main_create_item_with_new_quota` | ✅ PASS<br>⚠️ XFAIL (W-01) |
| **FR-02** | Create capacity pool (Quota) | BR-1 | WB-QUOTA-01<br>API-QUOTA-01<br>UC1-ALT2 | `tests/team/zubair/test_whitebox_quota_rules.py`<br>`tests/team/sami/api/test_api_ep_bva.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `Quota.availability()`<br>`POST /quotas/`<br>`test_uc1_alt_create_quota_from_quota_page` | ✅ PASS |
| **FR-03** | Patch/resize Quota capacity | BR-1, Cross-WF | WB-QUOTA-02<br>API-XWF-02<br>API-QUOTA-PATCH | `tests/team/zubair/test_whitebox_quota_rules.py`<br>`tests/team/sami/api/test_cross_workflow.py`<br>`tests/team/sami/api/test_api_ep_bva.py` | `Quota.size`<br>`PATCH /quotas/{id}/`<br>`test_w1_shrinking_capacity_blocks_w2` | ✅ PASS |
| **FR-04** | Presale live window control | BR-2 | WB-MCDC-01<br>API-RULE2-01<br>UC2-ALL | `tests/team/zubair/test_mcc_mcdc.py`<br>`tests/team/sami/api/test_negative_rules.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `Item.is_available()`<br>`test_rule2_item_sale_ended_rejected`<br>`test_uc2_*` (5 flows) | ✅ PASS<br>⚠️ XFAIL (W-07) |
| **FR-05** | Reserve seat in shopping cart | BR-1, BR-4 | WB-CART-01<br>API-CART-01<br>UC3-MAIN | `tests/team/zubair/test_whitebox_cart_rules.py`<br>`tests/team/sami/api/test_api_ep_bva.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `CartPosition.objects.create`<br>`POST /cartpositions/`<br>`test_uc3_main_checkout_one_ticket` | ✅ PASS |
| **FR-06** | Place Order from cart/direct | BR-1, BR-3 | WB-ORDER-01<br>API-ORDER-01<br>UC3-ALT1 | `tests/team/zubair/test_whitebox_order_rules.py`<br>`tests/team/sami/api/test_api_ep_bva.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `OrderCreateSerializer.create`<br>`POST /orders/`<br>`test_uc3_alt_two_tickets` | ✅ PASS |
| **FR-07** | Apply voucher discounts | BR-4 | UC4-ALL | `tests/team/tawassul/usecases/test_e2e_usecases.py` | `test_uc4_*` (5 flows: percentage, fixed, shop page, unknown, already used) | ✅ PASS |
| **FR-08** | Order state transitions | BR-3 | WB-STATE-01<br>API-TRANS-01<br>UC6-ALL | `tests/team/zubair/test_whitebox_order_rules.py`<br>`tests/team/sami/api/test_negative_rules.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | `Order.transition_to()`<br>`POST /orders/{code}/mark_*`<br>`test_uc6_*` (5 flows) | ✅ PASS |

---

## 3. Business Rule Verification Traceability

| Business Rule | Testing Technique | Coverage Target | Automated Verification File | Test Function / Count | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **BR-1 (Quota Boundary)** | 3-point BVA, White-Box Boundary, API Tests | $min-1, min, min+1$<br>$max-1, max, max+1$ | `tests/team/zubair/test_whitebox_quota_rules.py`<br>`tests/team/sami/api/test_api_ep_bva.py`<br>`tests/team/tawassul/static_analysis/test_cfg_paths.py` | 12 tests in Zubair<br>63 BVA cases in Sami<br>5 CFG basis paths in Tawassul | ✅ **100% Verified** |
| **BR-2 (Item Purchasability)** | Multiple Condition Coverage (MCC) & MC/DC | All 16 combinations ($2^4$)<br>4 independence pairs | `tests/team/zubair/test_mcc_mcdc.py`<br>`tests/team/sami/api/test_negative_rules.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | 16 MCC tests + 4 MCDC tests (Zubair)<br>Rule 2 API tests (Sami)<br>UC-2 Playwright flows (Tawassul) | ✅ **100% Verified** |
| **BR-3 (Order State Machine)** | State Transition Testing, AST Mutation | 9 allowed transitions<br>11 disallowed transitions | `tests/team/zubair/test_whitebox_order_rules.py`<br>`tests/team/sami/api/test_negative_rules.py`<br>`tests/team/zubair/mutation_runner.py` | 8 state tests in Zubair<br>20 transition tests in Sami<br>OrderStateMachineBypassMutator | ✅ **100% Verified** |
| **BR-4 (Cart TTL & Restoration)** | Temporal Invariant, Cross-Workflow Integration | Instant release upon TTL expiry; clear cart; remove item | `tests/team/zubair/test_whitebox_cart_rules.py`<br>`tests/team/sami/api/test_cross_workflow.py`<br>`tests/team/tawassul/usecases/test_e2e_usecases.py` | 6 cart tests in Zubair<br>Cross-workflow suite in Sami<br>UC3 & UC5 Playwright tests | ✅ **100% Verified** |

---

## 4. Non-Functional Requirements (NFR) Traceability

| NFR Area | Standard / SLA | Tool Used | Automated Test / Evidence Artifact | Result / Metrics Observed |
| :--- | :--- | :--- | :--- | :--- |
| **Usability & A11y** | WCAG 2.1 AA, Keyboard Focus, Screen Reader | Playwright, axe-core, Google Lighthouse | `tests/team/tawassul/usability_a11y/test_keyboard_nav.py`<br>`test_axe_scan.py`<br>`pretixcontrol/base.html` remediation | Keyboard navigation passes without mouse.<br>Lighthouse accessibility score increased from **81 to 93** on organizer screens. |
| **Defensive Security** | RBAC, OWASP Top 10, Secure Headers, Clean Dependencies | Playwright, OWASP ZAP, `pip-audit` | `tests/team/tawassul/security/test_rbac_decisions.py`<br>`test_security_headers.py`<br>`zap_report.html`<br>`dependency_audit_pip.md` | 10 RBAC decisions verified (organizer write vs read-only vs anon).<br>ZAP passive scan triaged.<br>Identified `oauthlib 3.3.1` CVEs and missing `nosniff`/`Referrer-Policy`. |
| **Performance & SLA** | p95 latency $\le 500\text{ms}$ under load; Error rate $< 1\%$ | Grafana k6 OSS | `tests/team/tawassul/performance/k6_workload.js`<br>`k6_metrics_report.md`<br>Runs: `k6_run_1a`, `1b`, `2a`, `2b` | 1 VU Baseline: p95 = 250ms, 0% error.<br>5 VUs Concurrent: p95 = 1.48s, 24% SQLite lock timeouts.<br>Identifies production PostgreSQL requirement. |
| **Reliability & Recovery** | Atomic rollback on crash; zero corrupted/orphaned records | Fault Injection / Pytest | `tests/team/tawassul/performance/test_failure_recovery.py` | Simulated database failure mid-checkout.<br>100% transaction rollback confirmed; seat released; retry succeeds. |
| **Mutation Testing** | Mutation Score $\ge 80\%$; 15 surviving mutants analyzed | Python AST Mutator | `src/tests/team/zubair/mutation_runner.py`<br>`custom_operators.py`<br>`SURVIVING_MUTANTS_ANALYSIS.md` | Baseline mutants: 125.<br>Killed: 110.<br>Score: **88.0%**.<br>15 surviving mutants cataloged and justified. |
| **CI Quality Gate** | Zero escape hatches; blocking pull request gate | GitHub Actions | `.github/workflows/sqe_quality_gate.yml`<br>`CI_QUALITY_GATE_REPORT.md` | Automated PR check blocks failing tests, coverage drops, or mutation degradation with no `continue-on-error`. |
