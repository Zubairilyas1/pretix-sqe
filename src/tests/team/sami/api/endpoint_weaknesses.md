# Endpoint Weaknesses Found by API Testing (Area 2, Sami)

System: pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`, SQLite test database, API token auth.
Every weakness below is reproduced by an automated test. Tests that assert the
expected (spec) behaviour are marked `xfail(strict=True)` with the weakness id,
so the suite fails loudly if the behaviour ever changes.

Risk ids (`PR-API-xx`) are proposed entries for the shared risk register
(`shared_management/RISK_REGISTER_5x5.md`). L = likelihood, I = impact (1-5).

| ID | Weakness | Severity | Risk (L×I) |
| :-: | :--- | :-: | :-: |
| W-01 | Negative item price accepted | Major | PR-API-01 (3×4 = 12) |
| W-02 | Negative cart-position price accepted | Major | PR-API-01 |
| W-03 | Retry without idempotency key creates a duplicate order | Major | PR-API-02 (3×4 = 12) |
| W-04 | Item name not validated (empty, missing locale, > 255 chars) | Minor | PR-API-03 (3×2 = 6) |
| W-05 | Quota size above 32-bit range accepted | Major | PR-API-04 (2×4 = 8) |
| W-06 | `with_availability` silently ignored on quota detail | Minor | PR-API-05 (4×2 = 8) |
| W-07 | Order API ignores item sale window (Rule 2) | Major | PR-API-06 (3×4 = 12) |
| W-08 | Order API ignores min/max per order (Rule 1) | Major | PR-API-06 |
| W-09 | Negative order-position price accepted by `POST orders/` | Major | PR-API-01 |
| W-10 | `X-Idempotency-Key` longer than 190 characters accepted | Minor | PR-API-02 |
| W-11 | `positions[].attendee_name` longer than 255 characters accepted | Minor | PR-API-03 |
| W-12 | Order action endpoints do not validate their body (`send_email` by truthiness) | Minor | PR-API-07 (3×2 = 6) |

---

### W-01 Negative item price accepted
- **Evidence:** `test_api_ep_bva.py::test_create_item[createItem.default_price.BVA.min-1]` and `[...EP.below_min]`. `POST items/` with `default_price: "-0.01"` returns **201** and stores -0.01.
- **Root cause:** `Item.default_price` (`src/pretix/base/models/items.py:508`) is a `DecimalField` with no `MinValueValidator`; `ItemSerializer.validate` does not check the sign.
- **Impact:** a misconfigured product pays money *to* the buyer, and order totals and reports become negative.
- **Fix:** add `validators=[MinValueValidator(Decimal("0.00"))]` to the field, or check it in `ItemSerializer.validate`.

### W-02 Negative cart-position price accepted
- **Evidence:** `test_create_cart_position[createCartPosition.price.BVA.min-1]` and `[...EP.below_min]`. `POST cartpositions/` with `price: "-1.00"` returns **201**.
- **Root cause:** `BaseCartPositionCreateSerializer` (`src/pretix/api/serializers/cart.py:57`) takes `price` straight from the client and copies it into `custom_price_input` without a bound check.
- **Impact:** an API integration can reserve seats with a negative price, which is carried into checkout.
- **Fix:** validate `price >= 0` in `BaseCartPositionCreateSerializer.validate`.

### W-03 Retry without idempotency key creates a duplicate order
- **Evidence:** `test_negative_rules.py::test_repeat_without_idempotency_key_creates_second_order`: two identical `POST orders/` produce 2 orders and consume 2 seats. With `X-Idempotency-Key` (`test_repeat_with_same_idempotency_key_returns_first_response`) or an explicit `code` (`test_repeat_with_same_order_code_is_rejected`) there is no duplicate.
- **Root cause:** `IdempotencyMiddleware` (`src/pretix/api/middleware.py:52`) only deduplicates when the client sends the header; the key is optional.
- **Impact:** a client retry after a network timeout double-books and double-charges.
- **Fix:** document the header as mandatory for `POST orders/` in client integrations, or require it (400 when missing) for order creation.

### W-04 Item name not validated
- **Evidence:** `test_create_item[createItem.name.en.BVA.len_min-1]` (empty name), `[...EP.missing]` (`name: {}`), `[...BVA.len_max+1]` and `[...EP.too_long]` (256+ chars). All return **201**.
- **Root cause:** `Item.name` is an `I18nCharField(max_length=255)` (`items.py:490`); the i18n serializer field does not enforce the length or a non-empty default locale.
- **Impact:** nameless products in the shop, tickets and invoices; inconsistent with the presale form, which rejects them.
- **Fix:** validate the default-locale text for non-empty and length ≤ 255 in `ItemSerializer`.

### W-05 Quota size above 32-bit range accepted
- **Evidence:** `test_create_quota[createQuota.size.BVA.max+1]` / `[...EP.above_max]` and `test_patch_quota[...]`: `size: 2147483648` returns **201/200** on SQLite.
- **Root cause:** `Quota.size` is a `PositiveIntegerField` (`items.py:2076`). Django documents 0..2147483647 as the safe range, but the serializer adds no `max_value`, and SQLite does not enforce the column width.
- **Impact:** on PostgreSQL (the production database) the same request should fail at the database instead of the serializer, so the client gets **500** instead of a 400 explaining the field. (Not run on PostgreSQL in this environment; this is a stated assumption.)
- **Fix:** add `max_value=2147483647` to the serializer field (or a `MaxValueValidator` on the model).

### W-06 `with_availability` ignored on quota detail
- **Evidence:** `test_negative_rules.py::test_quota_detail_honours_with_availability`: the list endpoint returns `available_number`, but the detail endpoint with the same flag silently omits it.
- **Root cause:** `QuotaViewSet.list` (`src/pretix/api/views/item.py:605`) computes availability; `retrieve` does not, and the serializer drops the missing fields without an error.
- **Impact:** clients read `null`/missing capacity and may assume "unlimited". Our own first test run fell into this trap (35 failures).
- **Fix:** compute availability in `retrieve` too, or reject the flag there. The correct read-back is `GET quotas/{id}/availability/`, which the tests now use.

### W-07 Order API ignores item sale window (Business Rule 2)
- **Evidence:** `test_rule2_item_sale_ended_rejected` and `test_rule2_item_sale_not_started_rejected`: an item whose `available_until` is in the past (or `available_from` in the future) can still be ordered through `POST orders/` (**201**).
- **Root cause:** `OrderCreateSerializer.create` (`src/pretix/api/serializers/order.py:1327`) checks `active`, quota and vouchers, but not `available_from`/`available_until`. Only the presale checkout enforces the window.
- **Impact:** Rule 2 holds in the shop but not for API sales (box office, resellers). Tickets sold after sales closed.
- **Note:** this is probably intentional (the API is for trusted, privileged integrations), but it is not documented in the response, and it breaks our business rule as written. Triage: *document, then decide*.
- **Fix:** enforce the window unless `force: true` is sent, mirroring how quota is handled.

### W-08 Order API ignores min/max per order (Business Rule 1)
- **Evidence:** `test_rule1_max_per_order_bva[max+1]` (4 positions with `max_per_order=3`) and `test_rule1_min_per_order_bva[min-1]` (1 position with `min_per_order=2`) both return **201**. The in-range cases (max-1, max, min, min+1) pass.
- **Root cause:** same place as W-07: `OrderCreateSerializer` does not read `min_per_order`/`max_per_order` (only `Item.clean_per_order` validates the configuration itself).
- **Impact:** per-customer purchase limits (anti-scalping) can be bypassed via the API.
- **Fix:** count positions per item in `OrderCreateSerializer.create` and reject outside the limits unless `force: true`.

### W-09 Negative order-position price accepted
- **Evidence:** `test_api_ep_bva.py::test_create_order[createOrder.positions[].price.BVA.min-1]` and `[...EP.below_min]` (generator cases on the array items). `POST orders/` with `positions: [{item, price: "-0.01"}]` returns **201**.
- **Root cause:** the position serializer of `OrderCreateSerializer` accepts a custom `price` without a lower bound (same missing bound as W-01/W-02).
- **Impact:** an API client can create an order with a negative total; refunds/payouts and reports are wrong.
- **Fix:** `min_value=Decimal("0.00")` on the position price field.

### W-10 Idempotency key longer than the stored column accepted
- **Evidence:** `test_api_parameters.py::test_header_parameter[createOrder.header:X-Idempotency-Key.BVA.len_max+1]` and `[...EP.too_long]`: a 191-character key returns **201** and the key is stored.
- **Root cause:** `IdempotencyMiddleware` stores the header in `ApiCall.idempotency_key = CharField(max_length=190)` (`src/pretix/api/models.py:173`) without checking the length; SQLite does not enforce it.
- **Impact:** on PostgreSQL the insert fails, so the client gets **500** instead of a 400 (assumption, not run on PostgreSQL), and retry protection is lost for long keys.
- **Fix:** reject keys longer than 190 characters with 400 in the middleware.

### W-11 Attendee name longer than 255 characters accepted
- **Evidence:** `test_create_order[createOrder.positions[].attendee_name.BVA.len_max+1]` and `[...EP.too_long]` return **201**.
- **Root cause:** `OrderPosition.attendee_name_cached` is `CharField(max_length=255)` (`src/pretix/base/models/orders.py:1514`); the API does not validate the length and SQLite does not enforce it.
- **Impact:** database error (500) on PostgreSQL; names cut or lost on tickets.
- **Fix:** `max_length=255` on the serializer field.

### W-12 Order actions do not validate their body
- **Evidence:** `test_api_ep_bva.py::test_order_action_body[markOrderPaid.send_email.EP.wrong_type]` (and null, and the same for `mark_canceled`): `{"send_email": "maybe"}` returns **200** and the action is executed.
- **Root cause:** the action views read `request.data.get('send_email', True)` without a serializer (`src/pretix/api/views/order.py:397, 454, 512, 530`), so any value is used by truthiness: the string `"false"` *sends* the e-mail.
- **Impact:** clients that send `"false"` as a string notify customers unintentionally; invalid input is not reported.
- **Fix:** validate the body with a small serializer (`send_email = BooleanField(default=True)`).

### Observed behaviour documented in the spec (not a weakness)
- An unknown organizer or event slug returns **403**, not 404: pretix checks the token's permission on the organizer/event before the lookup, which avoids revealing which organizers exist (`x-reject-status: 403` in the spec; tested by `test_api_parameters.py`).
- `?with_availability=` is only switched on by the exact value `true`; any other value is ignored (tested by `test_query_parameter`).

---

## Verified controls (no weakness found)

| Control | Test |
| :--- | :--- |
| Quota cannot be oversold via orders (Rule 1, BVA 9/10/11 on size 10) | `test_rule1_order_quantity_vs_available` |
| Quota cannot be oversold via cart reservations | `test_rule1_cart_reservation_vs_available` |
| Rejected requests leave the shared record unchanged | `test_cross_workflow.py`, `test_rule3_disallowed_transition` |
| Inactive item / item without quota refused | `test_rule2_*` |
| All 9 allowed and 11 disallowed order transitions behave as specified | `test_rule3_*` |
| Reactivating a canceled order re-checks capacity | `test_rule3_paying_canceled_order_after_quota_sold_out_is_refused` |
| Same idempotency key and same order code do not duplicate | `test_repeat_*` |
| Double `mark_paid` creates one confirmed payment | `test_repeat_mark_paid_creates_one_payment` |
| Read-only token cannot write on any of the 12 write operations (403, or 404 for a non-existent target); anonymous gets 401 on all 19 operations; every documented status code (incl. 409) is produced | `test_api_status_coverage.py` (`test_anonymous_is_refused_on_every_operation`, `test_readonly_token_cannot_write_on_any_write_operation`, `test_documented_status`) |
| Non-JSON bodies are refused with 415 on all write operations with a body | `test_non_json_body_is_rejected_with_415` |
| Order code length 5..16 and charset enforced; positions 1..500 enforced | `test_create_order[...]` |
