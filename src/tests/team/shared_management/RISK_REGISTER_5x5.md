# SE3002 SQE: Consolidated 5×5 Risk Register & Exit Criteria

**Course:** SE3002 – Software Quality Engineering  
**Target MIS:** `pretix` at upstream baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`  
**Team Members:** Zubair (Area 1), Sami (Area 2), Tawassul (Area 3)  
**Location:** `src/tests/team/shared_management/RISK_REGISTER_5x5.md`

---

## 1. Risk Scoring Methodology

Risks are assessed on a standard **$5 \times 5$ Risk Matrix**:
$$\text{Risk Score} = \text{Likelihood (1–5)} \times \text{Impact (1–5)}$$

- **Likelihood ($L$):** 1 = Rare, 2 = Unlikely, 3 = Moderate, 4 = Likely, 5 = Almost Certain
- **Impact ($I$):** 1 = Negligible, 2 = Minor, 3 = Moderate, 4 = Major, 5 = Critical
- **Severity Levels:**
  - **Critical (Red, Score 15–25):** Must be mitigated immediately; directly dictates blocking CI quality gates and comprehensive white-box/integration suites.
  - **High / Major (Orange, Score 10–14):** Extensive testing required; automated regression suites must cover edge conditions.
  - **Medium (Yellow, Score 5–9):** Automated detection via static analysis, linters, or scheduled scanning.
  - **Low (Green, Score 1–4):** Monitored, documented as residual risk or known architectural behavior.

---

## 2. 5×5 Risk Matrix Visualization

```
Impact (I) ->
           1 (Negligible)   2 (Minor)       3 (Moderate)    4 (Major)       5 (Critical)
Likelihood (L)
5 (Certain)   [ 5 ]           [ 10 ]          [ 15 ]          [ 20 ]          [ 25 ]
4 (Likely)    [ 4 ]           [  8 ] PR-API-05[ 12 ] PR-PERF-01 [ 16 ]        [ 20 ]
                              PJ-ENV-01       PR-A11Y-01
3 (Moderate)  [ 3 ]           [  6 ] PR-API-03[ 9 ] PR-CODE-01 [ 12 ] PR-WB-01 [ 15 ]
                              PR-SEC-02       PJ-SCH-01       PR-API-01, 02
                                                              PR-API-06, VAL-01
2 (Unlikely)  [ 2 ]           [  4 ]          [ 6 ] PR-SEC-03 [  8 ] PR-API-04 [ 10 ] PR-WB-02
                                                              PR-SEC-01, CI-01PR-DATA-01
1 (Rare)      [ 1 ]           [  2 ]          [ 3 ]           [  4 ]          [  5 ]
```

---

## 3. Product Risks (16 Risks)

| Risk ID | Area | Product Risk Description | L | I | Score | Category | Automated Test / Mitigation Strategy |
| :--- | :---: | :--- | :-: | :-: | :-: | :---: | :--- |
| **PR-WB-01** | Area 1 | **Quota Boundary Off-by-One:** Concurrency race or strict `<` vs `<=` check in `Quota.availability()` permits overselling or premature rejection. | 3 | 4 | **12** | Major | White-box 3-point boundary suite (`test_whitebox_quota_rules.py`) & MCDC condition D coverage. |
| **PR-WB-02** | Area 1 | **Order State Transition Bypass:** Unapproved or expired order forced into `PAID` state, bypassing approval validation. | 2 | 5 | **10** | Major | Exhaustive state transition tests (`test_whitebox_order_rules.py`) exercising all 9 valid and 11 invalid transitions. |
| **PR-API-01** | Area 2 | **Negative Item/Cart Price Accepted:** Negative ticket prices (`-0.01`) stored via REST API, creating negative revenue totals. | 3 | 4 | **12** | Major | Generator-derived BVA test (`min-1`); tracked as defect `W-01` / `W-02` with `xfail(strict=True)`. |
| **PR-API-02** | Area 2 | **Duplicate Order Creation on Retry:** Network retry without explicit idempotency header books multiple tickets and double-charges. | 3 | 4 | **12** | Major | Idempotency and duplicate order tests in `test_negative_rules.py` verifying `X-Idempotency-Key` requirement (`W-03`). |
| **PR-API-03** | Area 2 | **Unvalidated Item Name:** Empty strings or names exceeding 255 characters accepted by the API without rejection. | 3 | 2 | **6** | Medium | String length BVA boundary tests (`test_api_ep_bva.py`, `W-04`). |
| **PR-API-04** | Area 2 | **Quota Size 32-bit Integer Overflow:** Quota size $> 2^{31}-1$ accepted on SQLite, leading to database crashes on PostgreSQL. | 2 | 4 | **8** | Medium | BVA boundary tests (`test_create_quota[size.BVA.max+1]`, `W-05`). |
| **PR-API-05** | Area 2 | **Quota Availability Silently Dropped:** Detail endpoint `/quotas/{id}/` ignores `?with_availability=true`, misleading clients into assuming unlimited capacity. | 4 | 2 | **8** | Medium | Detail vs list availability test (`test_negative_rules.py`, `W-06`). Read-back redirected to `/availability/`. |
| **PR-API-06** | Area 2 | **Order API Bypasses Sale Window & Order Limits:** API creates orders outside `available_from`/`until` and ignores `max_per_order` constraints. | 3 | 4 | **12** | Major | API Business Rule 1 & Rule 2 tests (`test_negative_rules.py`, `W-07`, `W-08`). |
| **PR-SEC-01** | Area 3 | **Known Dependency CVEs in `oauthlib 3.3.1`:** High-severity vulnerabilities CVE-2026-49272 (8.5) and CVE-2026-49265 (6.8). | 2 | 4 | **8** | Medium | Automated dependency auditing via `pip-audit` (`dependency_audit_pip.md`). Recommend upgrade to `oauthlib >= 4.0.1`. |
| **PR-SEC-02** | Area 3 | **Sensitive Order Secret Leakage:** Missing `Referrer-Policy` allows private order URLs to leak in outbound referrer headers; MIME sniffing enabled. | 3 | 2 | **6** | Medium | Playwright header assertions in `test_security_headers.py` and OWASP ZAP passive scan (`zap_report.html`). |
| **PR-SEC-03** | Area 3 | **End-of-Life Bootstrap 3.4.1 XSS Vulnerabilities:** Unpatched XSS advisories (CVE-2024-6485, CVE-2025-1647) in frontend UI. | 2 | 3 | **6** | Medium | OWASP ZAP rule 10003 audit; CSP enforcement verification. |
| **PR-A11Y-01**| Area 3 | **Organizer Back-Office Accessibility Failures:** Missing page `lang`, missing image `alt` attributes, and non-descriptive links block screen readers. | 4 | 3 | **12** | Major | Automated axe-core scanning (`test_axe_scan.py`) & Lighthouse audit. Remediated in `pretixcontrol/base.html` (Lighthouse score 81 $\to$ 93). |
| **PR-CODE-01**| Area 3 | **Dead Add-On Price Correction Code:** Self-assignments in `cart.py:1056-1066` leave stale prices uncorrected. | 3 | 3 | **9** | Medium | Detected via SonarQube static analysis (Rule S1656); logged as defect `A3-D06`. |
| **PR-PERF-01**| Area 3 | **Checkout API Latency & Lock Contention:** High concurrency causes SQLite lock contention, pushing p95 latency to 1.5s with 24% HTTP 500 error spikes. | 4 | 3 | **12** | Major | k6 OSS load testing (1 VU baseline vs 5 VUs concurrent across 4 runs). SLA documented in `k6_metrics_report.md`. |
| **PR-DATA-01**| Area 3 | **Database Crash Mid-Checkout Data Corruption:** Unhandled crash during order insertion leaves orphaned reservations or lost quota seats. | 2 | 5 | **10** | Major | Controlled transaction fault injection and recovery test (`test_failure_recovery.py`) proving atomic rollback. |
| **PR-VAL-01** | Area 3 | **Back-Office Negative Price Submission:** Web UI allows entering and saving negative ticket prices. | 3 | 4 | **12** | Major | Playwright E2E exception flow (`test_uc1_exc_negative_price_rejected_in_backoffice`, defect `A3-D01`). |

---

## 4. Project Risks (3 Risks)

| Risk ID | Project Risk Description | L | I | Score | Category | Mitigation Strategy |
| :--- | :--- | :-: | :-: | :-: | :-: | :--- |
| **PJ-ENV-01** | **Local Windows/SQLite vs Production Parity:** File locking issues and SQLite concurrency locks differ from production Linux/PostgreSQL deployments. | 4 | 3 | **12** | Major | Containerized testing environment setup; isolated transactional test database runner; explicit documentation of environment boundaries. |
| **PJ-SCH-01** | **Multi-Member Git Branch Integration Latency:** Disconnected member branches lead to merge conflicts, duplicate test helpers, or late-stage API breakage. | 3 | 3 | **9** | Medium | Modular directory structure (`tests/team/{zubair,sami,tawassul}`); standardized shared fixture naming (`conftest.py`); GitHub PR-based reviews. |
| **PJ-CI-01** | **CI Quality Gate Blocking Flakiness:** Long test execution times or mutation runner timeouts in GitHub Actions block PR merges. | 2 | 4 | **8** | Medium | High-speed `uv` dependency caching; parallel pytest-xdist execution; strict mutation runner targeting critical logic only. |

---

## 5. Formal Measurable Exit Criteria

Per the course requirements, at least **3 measurable exit criteria** are defined, with at least **2 strictly tied to the highest-scoring risks**:

1. **Exit Criterion 1 (Tied to PR-WB-01 & PR-WB-02 - Score 12 & 10): Functional & Structural Coverage Threshold**
   - **Target:** Server-side business logic for Quotas, Cart reservations, and Orders must achieve **100% statement coverage** and **100% branch coverage** across all decision paths.
   - **Quality Gate:** Multiple Condition Coverage (MCC) must evaluate all 16 truth-table combinations, and Modified Condition/Decision Coverage (MC/DC) must prove condition independence for all 4 primary conditions with zero failures.
   - **Status:** ✅ **MET.** 42/42 tests pass; 100% MCC and MCDC achieved.

2. **Exit Criterion 2 (Tied to PR-API-01, PR-API-02, PR-API-06 - Score 12): API Invariant & Zero-Regression Gate**
   - **Target:** All 19 OpenAPI operations must be validated. Generated Equivalence Partitions and 3-point BVA test suites must pass 100% with zero unacknowledged failures. All confirmed weaknesses must be strictly tracked as `xfail(strict=True)` to prevent silent behavioral drift.
   - **Cross-Workflow Invariant:** Shared quota availability must remain perfectly consistent across Workflow 1 (Organizer) and Workflow 2 (Customer checkout), with zero partial seat leakage on failed orders.
   - **Status:** ✅ **MET.** 243 passed, 17 strict xfail out of 260 tests. Cross-workflow invariant passes.

3. **Exit Criterion 3 (Tied to PR-A11Y-01 & PR-PERF-01 - Score 12): Non-Functional Quality, Security & Mutation Gate**
   - **Target:**
     - **Accessibility:** Zero critical or serious WCAG 2.1 AA violations on remediated pages; Lighthouse accessibility score on organizer screens must exceed **90**.
     - **Performance & Recovery:** Mid-checkout database failure injection must result in 100% rollback without orphaned records or locked seats.
     - **Mutation Testing:** AST Mutation runner across business logic must achieve a Mutation Score $\ge \mathbf{80\%}$ with all surviving mutants documented and classified.
   - **Status:** ✅ **MET.** Lighthouse score increased from 81 $\to$ 93; database recovery test passes; mutation score achieved is **88.0%** (above 80% threshold).
