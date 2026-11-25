# SE3002 SQE: Sami's Master Execution Plan (Area 2)

**Owner:** Sami (Member 2)
**Area:** OpenAPI specification, automated test data generator (EP + 3-point BVA), API and integration testing, cross-workflow shared-state verification, endpoint weakness report
**Marks owned:** Automated test data generation (7) + API and integration testing (10) + shared test management + viva (20)
**System under test:** pretix at upstream baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`
**Work folder:** `src/tests/team/sami/`
**Git:** member branch `member/sami`; feature branches `sami/feat-*` merged into `member/sami` by PR, then `member/sami` into `main` by PR.

---

## 0. Correction to the original partition plan (test basis)

The partition guide named endpoints such as `cart/add/` and `order/create/`. **They do not exist in pretix.** This plan is based on the real routes, read from `src/pretix/api/urls.py`, `src/pretix/api/views/{item,cart,order}.py` and `src/pretix/api/serializers/{item,cart,order}.py`.

Base path: `/api/v1/organizers/{organizer}/events/{event}/`

| Workflow | Method and path | Purpose | Source of truth |
| :--- | :--- | :--- | :--- |
| W1 Organizer | `POST items/` | Create ticket product | `ItemSerializer.validate` |
| W1 Organizer | `POST quotas/` | Create capacity pool (shared record) | `QuotaSerializer`, `Quota.size` |
| W1 Organizer | `PATCH quotas/{id}/` | Change capacity | `QuotaSerializer` |
| W1 / W2 read-back | `GET quotas/{id}/?with_availability=true` | Read `available`, `available_number` | `QuotaSerializer.__init__` |
| W2 Customer (via API) | `POST cartpositions/` | Reserve one seat of quota | `CartPositionViewSet._create` |
| W2 | `DELETE cartpositions/{id}/` | Release reservation | `perform_destroy` |
| W2 | `POST orders/` | Place order (consumes quota) | `OrderCreateSerializer.create` |
| W2 | `GET orders/{code}/` | Read order back | `EventOrderViewSet` |
| W2 state | `POST orders/{code}/mark_paid/` | PENDING/EXPIRED → PAID | `views/order.py:395` |
| W2 state | `POST orders/{code}/mark_canceled/` | PENDING/PAID/EXPIRED → CANCELED | `Order.cancel_allowed()` |
| W2 state | `POST orders/{code}/mark_expired/` | PENDING → EXPIRED | `views/order.py:566` |
| W2 state | `POST orders/{code}/mark_refunded/` | PAID → refunded | `views/order.py:583` |
| W2 state | `POST orders/{code}/mark_pending/` | PAID → PENDING | `views/order.py:547` |
| W2 state | `POST orders/{code}/reactivate/` | CANCELED → PENDING/PAID | `views/order.py:488` |

**Shared record:** `Quota` (`size` written by W1; `available_number` consumed by W2 cart positions and orders; released by cancel and cart delete).

**API roles (for authorisation and coverage):**
- *Organizer token:* team with `all_event_permissions=True` (read and write).
- *Read-only token:* team limited to `event.orders:read` and `event.items:read`. Writes must be refused with 403.
- *Anonymous:* no token. Must be refused with 401.

---

## 1. Inputs identified for EP and BVA (from source code)

| # | Endpoint | Field | Constraint in source | Valid EP | Invalid EP classes | BVA (3-point) |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| I1 | quotas | `size` | `PositiveIntegerField`, nullable | 0..2147483647, null = unlimited | negative, non-integer string, float, above int32 | -1, 0, 1 / 2147483646, 2147483647, 2147483648 |
| I2 | quotas | `name` | `CharField(max_length=200)`, required | 1..200 chars | missing, empty, 201 chars | 199, 200, 201 |
| I3 | items | `default_price` | Decimal(13,2), required, not null | 0.00..99999999999.99 | missing, null, 3 decimals, non-numeric | -0.01, 0.00, 0.01 / max-0.01, max, max+0.01 |
| I4 | items | `min_per_order` / `max_per_order` | int ≥ 0, min ≤ max | 0..n | -1, min > max | -1, 0, 1 and min = max-1, max, max+1 |
| I5 | items | `available_from` / `available_until` | from ≤ until | from ≤ until | from > until | until-1s, until, until+1s |
| I6 | orders | `positions` | list, 1..`PRETIX_MAX_ORDER_SIZE` (500) | 1..500 | empty list, 501 | 0, 1, 2 / 499, 500, 501 |
| I7 | orders | `code` | 5..16 chars, charset `A-Z` (no I, O) + digits, unique | `ABCDE` | 4 chars, 17 chars, invalid char, duplicate | 4, 5, 6 / 15, 16, 17 |
| I8 | orders | `email` | `EmailField` | valid address | malformed | n/a (format class) |
| I9 | orders | `status` | choice `n` / `p` | n, p | `c`, `x`, empty | n/a (enum class) |
| I10 | cartpositions | `cart_id` | must end with `@api` or be empty | `abc@api` | `abc`, `abc@web` | n/a (format class) |
| I11 | orders / cart | quantity vs quota (business BVA, Rule 1) | positions ≤ `available_number` | k ≤ available | k > available | available-1, available, available+1 |

The generator reads these limits **from the OpenAPI spec**, not from this table, so a spec change flows through automatically.

---

## 2. Feature breakdown, branches and deliverables

### F1. OpenAPI 3.0 specification (branch `sami/feat-openapi-spec`)
- `src/tests/team/sami/openapi/pretix_orders_api.yaml`
- Every endpoint from section 0, request and response schemas, `minimum`/`maximum`/`minLength`/`maxLength`/`pattern`/`enum`/`nullable`, status codes 200/201/400/401/403/404/409.
- A vendor extension `x-business-limit` on fields whose limit comes from configuration (e.g. quota `size` for Rule 1).
- Validated with `openapi-spec-validator` (a test asserts the spec is valid).

### F2. Test data generator (branch `sami/feat-test-data-generator`)
- `src/tests/team/sami/generator/generate_test_data.py`
  - Input: the spec. Output: `generator/test_data.json`.
  - For each constrained field in each request schema it emits:
    - **EP classes:** `valid`, `below_min`, `above_max`, `wrong_type`, `null` (if not nullable), `missing` (if required), `too_short`/`too_long`, `pattern_mismatch`, `not_in_enum`.
    - **3-point BVA:** `min-1, min, min+1` and `max-1, max, max+1` (numbers), and the equivalent lengths for strings. For decimals, the step is `10^-decimals` (`multipleOf`).
  - Each case: `id`, `endpoint`, `field`, `technique`, `class`, `value`, `expected` (`accept` / `reject`).
  - Deterministic (no randomness), so the output can be diffed after a spec change.
- `generator/README.md`: how to run, and how to change a constraint and regenerate.
- Unit tests for the generator itself (`test_generator.py`).
- **Constraint-change demo (required by the brief):** change two constraints (e.g. quota `size.maximum`, order `code.maxLength`), regenerate, commit the before/after JSON diff to `generator/regeneration_demo/`.

### F3. API tests: EP and BVA (branch `sami/feat-api-ep-bva`)
- `src/tests/team/sami/api/conftest.py`: organizer, event, item, quota, organizer token client, read-only token client, anonymous client.
- `api/test_api_ep_bva.py`: parametrised from `test_data.json`. One invalid value per test. Asserts:
  - status code (201/200 vs 400),
  - error body names the offending field,
  - on accept: response echoes the stored value; on reject: no record created (DB count unchanged).

### F4. API tests: rules, state transitions, duplicates, authorisation (branch `sami/feat-api-negative-rules`)
- `api/test_negative_rules.py`:
  - Rule 1: order more positions than `available_number` → 400 *"not enough quota"*; inactive item → 400.
  - Rule 3: every allowed transition (n→p, n→c, n→e, p→c, p→n, p→refunded, e→p, c→reactivate) and at least one disallowed transition from each state (n→refund, p→mark_paid, p→expire, c→mark_paid, e→refund) → 400 with unchanged status.
  - Repeated requests: same `X-Idempotency-Key` twice → one order; same explicit `code` twice → second is 400; `mark_paid` twice → second is 400 and only one confirmed payment.
  - Authorisation: read-only token POST → 403; anonymous → 401; unknown order code → 404.
- `api/test_api_coverage.py`: API coverage criteria. Every endpoint and method in the spec is exercised, plus a response-schema check of each 2xx body against the spec.

### F5. Cross-workflow integration (branch `sami/feat-cross-workflow`)
- `api/test_cross_workflow.py`:
  1. W1 `POST quotas` size 5 → read back `available_number == 5`.
  2. W2 order 3 → 201 → read back 2.
  3. W2 order 3 → 400 → read back **still 2** (no partial decrement).
  4. W2 cart position → read back 1; delete cart position → 2.
  5. Cancel the order → read back 5.
  6. W1 `PATCH` size 5 → 3 while 3 sold → read back 0, and the next order is rejected.
- `api/endpoint_weaknesses.md`: each weakness with evidence, root cause, severity, risk link and fix. Candidates to verify by test:
  - The order-create API does **not** enforce `max_per_order` / `min_per_order` (the presale UI does).
  - The order-create API does **not** enforce `available_from` / `available_until`.
  - No idempotency without an explicit `X-Idempotency-Key` (two identical POSTs make two orders).
  - Whether a negative `default_price` is accepted.

### F6. Shared test management contribution (branch `sami/docs-shared-management`)
- Area 2 rows in: risk register (API-specific product risks), RTM (FR → rule → test ID → script), three-point estimate vs actual, defect log (GitHub Issues for each confirmed weakness), GQM inputs.
- AI-use log rows for all of Sami's AI usage, including this session.

---

## 3. Order of execution

| Step | Branch | Deliverable | Exit check |
| :-: | :--- | :--- | :--- |
| 1 | `member/sami` | This plan and tracker | committed |
| 2 | `sami/feat-openapi-spec` | YAML spec + validity test | spec validator passes |
| 3 | `sami/feat-test-data-generator` | generator + JSON + generator tests | deterministic output, tests pass |
| 4 | `sami/feat-api-ep-bva` | EP/BVA API tests from JSON | all pass, or a failure is logged as a defect |
| 5 | `sami/feat-api-negative-rules` | rules, transitions, duplicates, auth | all pass / defects logged |
| 6 | `sami/feat-cross-workflow` | cross-workflow test + weaknesses report | invariants hold |
| 7 | `sami/feat-test-data-generator` | constraint-change regeneration demo | diff committed |
| 8 | `sami/docs-shared-management` | RTM, risks, estimates, AI log | reviewed by team |

## 4. How to run (once set up)
```bash
cd pretix-sqe
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" pyyaml openapi-spec-validator
cd src
../.venv/Scripts/python ../src/tests/team/sami/generator/generate_test_data.py   # regenerate data
../.venv/Scripts/python -m pytest tests/team/sami -v
```
Tests use pytest-django with a fresh test database per run, so no manual reset is needed.

## 5. Viva preparation (Sami)
- **Live task, spec change:** edit `maximum`/`maxLength` in the YAML → run the generator → show the new BVA triple in the JSON → rerun the API tests and predict which will fail (the "at max" case flips to reject if the server limit is unchanged; that is a spec/implementation mismatch, which is the point of the exercise).
- **Explain EP vs BVA:** partitions are classes of equivalent behaviour; BVA probes the edges of the ordered partitions at min-1/min/min+1.
- **Explain the cross-workflow invariant:** `available_number` = size − paid/pending positions − active cart positions; it must be unchanged after a rejected request.
- **Explain each weakness** and the evidence test that proves it.
