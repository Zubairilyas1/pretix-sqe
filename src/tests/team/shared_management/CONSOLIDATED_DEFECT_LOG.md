# Defect Log, Root Cause Analysis and Pareto

**System:** pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`. Every defect below has a reproducing
automated test or tool output. Each defect is filed as a GitHub Issue in `Zubairilyas1/pretix-sqe` (labels: `defect`,
`severity:*`, `priority:*`, `area:*`); the issue texts are in `github_issues/` and are created with `github_issues/create_issues.py`.

Severity: Critical / Major / Minor. Priority: P1 (fix before release) / P2 (fix in next iteration) / P3 (backlog).
Triage decisions: **Fix** (we fix it in this repository), **Report upstream** (defect in pretix we do not patch),
**Accept** (documented, risk accepted), **Fixed**.

## 1. Defects
| ID | Title | Severity | Priority | Status | Triage | Found by (evidence) | Risk | Issue |
| :--- | :--- | :-: | :-: | :-: | :--- | :--- | :-: | :-: |
| D-Z01 | Waiting-list auto-disable compared with real `now()` instead of `now_dt` in `QuotaAvailability` | Minor | P2 | Fixed (PR [#36](https://github.com/Zubairilyas1/pretix-sqe/pull/36) merged 28 Nov) | Fix: pass `now_dt` to `_compute_waitinglist` | White-box review of `quotas.py` L461; `zubair/test_dz01_waitinglist_now_dt.py` | PR-WB-01 | [#16](https://github.com/Zubairilyas1/pretix-sqe/issues/16) |
| W-01 | Negative item price accepted by `POST items/` | Major | P1 | Open | Report upstream; blocks release (EC-1 risk) | `sami/api/test_api_ep_bva.py` BVA min-1 (strict xfail) | PR-API-01 || [#17](https://github.com/Zubairilyas1/pretix-sqe/issues/17) |
| W-02 | Negative cart-position price accepted | Major | P1 | Open | Report upstream | `test_api_ep_bva.py` (strict xfail) | PR-API-01 || [#18](https://github.com/Zubairilyas1/pretix-sqe/issues/18) |
| W-03 | Retry without idempotency key creates a duplicate order | Major | P2 | Open | Accept for trusted clients + document header | `test_negative_rules.py` characterisation test | PR-API-02 || [#19](https://github.com/Zubairilyas1/pretix-sqe/issues/19) |
| W-04 | Empty / over-long item name accepted | Minor | P3 | Open | Report upstream | `test_api_ep_bva.py` (strict xfail) | PR-API-03 || [#20](https://github.com/Zubairilyas1/pretix-sqe/issues/20) |
| W-05 | Quota size above 32-bit range accepted | Major | P2 | Open | Report upstream | `test_api_ep_bva.py` (strict xfail) | PR-API-04 || [#21](https://github.com/Zubairilyas1/pretix-sqe/issues/21) |
| W-06 | `with_availability` ignored on quota detail | Minor | P3 | Open | Accept (workaround: `/availability/`) | `test_negative_rules.py` (strict xfail) | PR-API-05 || [#22](https://github.com/Zubairilyas1/pretix-sqe/issues/22) |
| W-07 | Order API ignores item sale window | Major | P1 | Open | Report upstream (document or enforce unless `force`) | `test_negative_rules.py` rule 2 (strict xfail) | PR-API-06 || [#23](https://github.com/Zubairilyas1/pretix-sqe/issues/23) |
| W-08 | Order API ignores min/max per order | Major | P1 | Open | Report upstream | `test_negative_rules.py` rule 1 BVA (strict xfail) | PR-API-06 || [#24](https://github.com/Zubairilyas1/pretix-sqe/issues/24) |
| W-09 | Negative order-position price accepted by `POST orders/` | Major | P1 | Open | Report upstream (same family as W-01) | `test_api_ep_bva.py` positions[].price BVA min-1 (strict xfail) | PR-API-01 || [#31](https://github.com/Zubairilyas1/pretix-sqe/issues/31) |
| W-10 | `X-Idempotency-Key` longer than 190 characters accepted | Minor | P3 | Open | Report upstream | `test_api_parameters.py` header BVA len_max+1 (strict xfail) | PR-API-02 || [#32](https://github.com/Zubairilyas1/pretix-sqe/issues/32) |
| W-11 | `attendee_name` longer than 255 characters accepted | Minor | P3 | Open | Report upstream | `test_api_ep_bva.py` positions[].attendee_name BVA len_max+1 (strict xfail) | PR-API-03 || [#33](https://github.com/Zubairilyas1/pretix-sqe/issues/33) |
| W-12 | Order action endpoints do not validate their body (`send_email` by truthiness) | Minor | P2 | Open | Report upstream | `test_api_ep_bva.py::test_order_action_body` (strict xfail) | PR-API-07 || [#34](https://github.com/Zubairilyas1/pretix-sqe/issues/34) |
| A3-D01 | Back office saves a negative item price | Major | P1 | Open | Report upstream (same root cause as W-01) | `tawassul/usecases` UC1-E1 (strict xfail) | PR-VAL-01 || [#25](https://github.com/Zubairilyas1/pretix-sqe/issues/25) |
| A3-D02 | `X-Content-Type-Options` / `Referrer-Policy` not sent | Minor | P2 | Open | Fix in deployment config | `tawassul/security/test_security_headers.py`, ZAP 10021 | PR-SEC-02 || [#26](https://github.com/Zubairilyas1/pretix-sqe/issues/26) |
| A3-D03 | Back office fails WCAG 2.1 A (lang, alt, link names) | Major | P1 | Fixed | Fixed in `pretixcontrol/base.html` (commit `dc2e75a6e`) | axe + Lighthouse before/after | PR-A11Y-01 || [#27](https://github.com/Zubairilyas1/pretix-sqe/issues/27) |
| A3-D04 | `oauthlib 3.3.1` with known CVEs | Major | P1 | Open | Upgrade dependency | pip-audit JSON | PR-SEC-01 || [#28](https://github.com/Zubairilyas1/pretix-sqe/issues/28) |
| A3-D05 | Bootstrap 3.4.1 end-of-life (XSS advisories) | Minor | P3 | Open | Accept (CSP mitigates), report upstream | ZAP 10003 | PR-SEC-03 || [#29](https://github.com/Zubairilyas1/pretix-sqe/issues/29) |
| A3-D06 | Add-on price correction is a self-assignment | Major | P2 | Open | Report upstream | SonarQube S1656, `cart.py:1059-1065` | PR-CODE-01 || [#30](https://github.com/Zubairilyas1/pretix-sqe/issues/30) |

**Withdrawn:** D-01..D-08 (listed until 27 Nov 2026) had no reproduction, test or code change behind them; D-02 described
a method `Order.transition_to()` that does not exist in pretix. They were removed (see AI-use record, correction note).

## 2. Root cause analysis

### RCA-1: W-01 / W-02 / A3-D01 - negative prices are stored (Major)
**Problem.** `POST items/` with `default_price: "-0.01"`, `POST cartpositions/` with `price: "-1.00"` and
`POST orders/` with `positions[].price: "-0.01"` (W-09) return 201; the back-office form also saves `-5.00`. Four entry
points, one cause.

**5 Whys**
1. Why is a negative price stored? Neither the serializers nor the form reject it.
2. Why do they not reject it? They rely on the model field, and `Item.default_price` (`items.py:508`) is a `DecimalField(max_digits=13, decimal_places=2)` with no `MinValueValidator`.
3. Why is there no validator? Price rules are enforced in the price calculation of the shop (customers never type a price), not on the stored configuration.
4. Why does that not protect the API and the back office? These paths write the configuration directly and do not go through the shop's price logic.
5. Why was this not caught? No negative boundary (min-1) was tested on these inputs before our generator produced it.

**Fishbone**
```
 Method                         Machine / Data
 price rule lives in the shop   DecimalField without lower bound
 not in the model               no DB CHECK constraint
          \                         /
           +-----> NEGATIVE PRICE STORED <-----+
          /                         \
 People                          Measurement
 assumption: only organizers     no min-1 boundary test on
 edit prices, they are trusted   item / cart price inputs
```
**Corrective action:** add `MinValueValidator(Decimal("0.00"))` to `Item.default_price` and `ItemVariation.default_price`, and validate `price >= 0` in `BaseCartPositionCreateSerializer.validate`.
**Preventive action:** the OpenAPI generator emits min-1 for every numeric input, and the strict-xfail tests turn red (XPASS) as soon as a fix lands, so the fix is noticed and the test is converted.

### RCA-2: W-07 / W-08 - Order API bypasses the sale window and per-order limits (Major)
**Problem.** Through `POST orders/` an item can be bought after `available_until`, before `available_from`, and in quantities outside `min_per_order..max_per_order`; the shop rejects the same requests.

**5 Whys**
1. Why is the order accepted? `OrderCreateSerializer.create` (`api/serializers/order.py:1327`) checks `active`, quota and vouchers, but not the time window or the per-order limits.
2. Why are those checks missing there? The shop enforces them in the cart service (`services/cart.py`), which the API order endpoint does not use.
3. Why does the API not use the cart service? It was designed for trusted integrations (box office, imports) that create finished orders directly.
4. Why is that a problem? Resellers and other API clients are not always trusted, and nothing in the API response or docs says the rules are skipped.
5. Why was it not noticed? Rule-level tests existed only for the shop flow; the API had no business-rule tests before Area 2.

**Fishbone**
```
 Method                               Machine
 rules implemented in cart service    two code paths for one rule
 API bypasses cart service            (cart.py vs order serializer)
            \                           /
             +--> RULE NOT ENFORCED IN API <--+
            /                           \
 People                               Measurement
 API assumed "trusted only"           no API business-rule tests;
 not documented                       only shop-flow tests
```
**Corrective action:** enforce the sale window and per-order limits in `OrderCreateSerializer` unless `force: true` (the same pattern already used for quota).
**Preventive action:** one shared validation function for BR-1/BR-2 used by both the cart service and the API; API rule tests (`test_negative_rules.py`) run in the CI gate.

## 3. Pareto analysis by category
| Category | Defects | Count | % | Cumulative % |
| :--- | :--- | :-: | :-: | :-: |
| Input validation | W-01, W-02, W-04, W-05, W-09, W-10, W-11, A3-D01 | 8 | 42.1 | 42.1 |
| Business rule not enforced / API contract | W-03, W-06, W-07, W-08, W-12 | 5 | 26.3 | 68.4 |
| Security configuration and dependencies | A3-D02, A3-D04, A3-D05 | 3 | 15.8 | 84.2 |
| Logic error in code | A3-D06, D-Z01 | 2 | 10.5 | 94.7 |
| Accessibility | A3-D03 | 1 | 5.3 | 100.0 |
| **Total** | | **19** | **100** | |

Chart: `docs/sqe/figures/pareto_defects.png` (generated from this table by `docs/sqe/figures/make_pareto.py`).

**Reading.** Three categories (input validation, rules not enforced in the API, security configuration) hold 84 % of the
defects; the first two alone hold 68 %. Two of them come from the same pattern: a rule is checked in one entry point (the shop) but not in the others
(API, back office). The most effective preventive action is therefore one shared validation per rule, tested through
every entry point (EP/BVA at API level, use cases at UI level).
