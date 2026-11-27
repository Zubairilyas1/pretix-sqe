# Role-Based Access Control Matrix (W1 and W2)

**Roles**

| Role | Who | How the session is created in tests |
| :--- | :--- | :--- |
| **Organizer** | back-office user in a team with all event permissions | `control_login` fixture: real login form at `/control/login` |
| **Viewer** | back-office user whose team has only `event.orders:read` | `viewer_login` fixture |
| **Customer** | anonymous shop visitor; owns an order through its secret link | fresh browser context, no login |

**Legend:**
- ✅ allowed
- ⛔ denied (HTTP status or redirect in brackets)
- 🔑 allowed only with the order secret

## Matrix

| # | Resource (route) | Workflow | Organizer | Viewer | Customer | Automated test |
| :-: | :--- | :-: | :-: | :-: | :-: | :--- |
| 1 | Back office home `/control/` | W1 | ✅ 200 | ✅ 200 | ⛔ redirect `/control/login` | `test_rbac_organizer_can_open_control`, `test_rbac_customer_is_sent_to_login_for_control` |
| 2 | Create product `/control/event/{o}/{e}/items/add` | W1 | ✅ 200 | ⛔ 403 | ⛔ redirect login | `test_rbac_organizer_can_open_item_editor`, `test_rbac_viewer_cannot_create_items` |
| 3 | Order list `/control/event/{o}/{e}/orders/` | W2 | ✅ 200 | ✅ 200 | ⛔ redirect login | `test_rbac_viewer_can_list_orders`, `test_rbac_customer_cannot_open_event_backoffice` |
| 4 | Cancel order `/control/event/{o}/{e}/orders/{code}/transition?status=c` | W2 | ✅ | ⛔ 403, order unchanged | ⛔ redirect login | `test_uc6_alt_organizer_cancels_in_backoffice`, `test_rbac_viewer_cannot_cancel_orders` |
| 5 | Shop `/{o}/{e}/` | W2 | ✅ 200 | ✅ 200 | ✅ 200 | `test_rbac_customer_can_open_presale` |
| 6 | Own order `/{o}/{e}/order/{code}/{secret}/` | W2 | ✅ (via back office) | ✅ (via back office) | 🔑 200 | `test_uc3_main_checkout_one_ticket` |
| 7 | Order with wrong secret | W2 | — | — | ⛔ 404 | `test_rbac_customer_cannot_view_other_order_without_secret` |
| 8 | Order without secret `/{o}/{e}/order/{code}/` | W2 | — | — | ⛔ 404 | `test_rbac_customer_cannot_view_other_order_without_secret` |
| 9 | Wrong order code with a valid secret | W2 | — | — | ⛔ 404 | `test_rbac_customer_cannot_guess_order_with_wrong_code` |
| 10 | Self-cancel `/{o}/{e}/order/{code}/{secret}/cancel` | W2 | — | — | 🔑 only if the event allows it | `test_uc6_main_*`, `test_uc6_exc_wrong_secret_is_404`, `test_uc6_exc_self_cancel_disabled` |
| 11 | REST API `/api/v1/...` without token | W1/W2 | — | — | ⛔ 401 | Sami's Area 2 `test_auth_anonymous_is_refused` (referenced, not duplicated) |

**Access decisions automated in `test_rbac_decisions.py`: 10.** The brief requires at least 4. Rows 4, 6 and 10 are also covered by the use-case tests.

## Design observations
- **404 rather than 403 for foreign orders (rows 7–9).** pretix answers a wrong secret exactly like a non-existent order. An attacker therefore cannot tell whether an order code exists, which prevents order-code enumeration.
- **Redirect rather than 403 for anonymous back-office access (rows 1–4).** Anonymous users are sent to the login page with `?next=`, and the protected page content is never rendered.
- **Least privilege works (rows 2 and 4).** A viewer with `event.orders:read` can read orders but gets 403 on product creation and order cancellation, and the database is unchanged after the denied request.
- **Order secrets are the only protection for customer data.** The secret is a 16-character random string and appears in the URL. It therefore ends up in browser history and in any `Referer` header to third-party resources on the order page. **pretix does not send a `Referrer-Policy` header** (defect A3-D02, see `zap_passive_scan_report.md`), so only the browser default (`strict-origin-when-cross-origin` in current browsers) limits this.
