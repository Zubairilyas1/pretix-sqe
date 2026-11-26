# Sami's SQE Task Tracker (Area 2)

**Owner:** Sami (Member 2)
**Member branch:** `member/sami`
**Plan:** `docs/sqe/SAMI_MASTER_EXECUTION_PLAN.md`

| # | Milestone | Branch | Status | Evidence |
| :-: | :--- | :--- | :-: | :--- |
| S1 | Master plan and tracker | `member/sami` | ✅ Done | `b7550d351` |
| S2 | OpenAPI 3.0 spec (19 operations) | `sami/feat-openapi-spec` | ✅ Done | `62d788f11`, `8661e5022`; `test_openapi_spec.py` |
| S3 | EP/BVA test data generator (167 cases) | `sami/feat-test-data-generator` | ✅ Done | `566481031`; `test_generator.py` |
| S4 | API EP/BVA tests + API coverage | `sami/feat-api-ep-bva` | ✅ Done | `144d2a040` |
| S5 | Rules, transitions, duplicates, auth | `sami/feat-api-negative-rules` | ✅ Done | `2f5d96ef8` |
| S6 | Cross-workflow test + weaknesses report | `sami/feat-cross-workflow` | ✅ Done | `ab3c5deca`; `endpoint_weaknesses.md` |
| S7 | Constraint-change regeneration demo | `sami/feat-regeneration-demo` | ✅ Done | `d36eee675`; `REGENERATION_REPORT.md` |
| S8 | Shared management inputs (risks, RTM rows, estimates, defects as Issues) | `sami/docs-shared-management` | ⏳ In progress | `bbd29933a` (AI log rows); risk/RTM/estimates pending |
| S9 | Push branches, open PRs into `member/sami`, then `main` | — | ⏳ PR open into `main` | see PR |

## Current results
`cd src && ../.venv/Scripts/python -m pytest tests/team/sami -n 4`
→ **243 passed, 17 xfailed (strict)**. The xfails are the confirmed weaknesses W-01, W-02, W-04 to W-08.

## Log
- 2026-11-25: Read project brief, team docs and pretix API source. Found that the planned `cart/add/` and `order/create/` routes do not exist; plan rebased on the real routes (`cartpositions/`, `orders/`, state actions). Created venv.
- 2026-11-25: First full run: 58 failures. Triage:
  - 35 were my test error: reading availability from the quota detail endpoint, which ignores `with_availability`. Switched to `quotas/{id}/availability/` and logged it as W-06.
  - 6 were spec errors where pretix deliberately allows the value (quota without items; null `cart_id`/`locale`/`send_email`; string item name); spec corrected.
  - 2 were a generator bug (type classes on the synthetic quantity field); fixed.
  - 3 were missing fixtures in my tests; fixed.
  - The rest are real weaknesses: W-01, W-02, W-04, W-05, then W-07 and W-08 from the new Rule 2 and per-order limit tests.
- 2026-11-25: Regeneration demo: changed `code.maxLength` 16→12 and `size.maximum` →1000. 9 cases changed. The predicted failure (`code.BVA.len_max+1`) was observed; the size cases show as the known W-05 xfail.
