# Use Case Specification: pretix Workflows W1 and W2 (Area 3, Tawassul)

**System:** pretix at baseline `c0d887738b6cd97f724b926718c55e2ae87c9901`
**Workflows:** W1 organizer creates items and quotas; W2 customer buys tickets. The shared record is `Quota`: W1 sets `size`, W2 consumes `availability()`.
**Actors:**
- **Organizer:** a back-office user in a team with event permissions (`/control/`).
- **Customer:** an anonymous visitor of the shop (`/{organizer}/{event}/`).

**Business rules referenced:**
- **R1:** an order or reservation is accepted only within the available quota.
- **R2:** an item is purchasable only if it is active, has a quota, and is inside the sales window.
- **R3:** orders change state only along the allowed lifecycle (pending, paid, expired, canceled), and only pending or paid orders hold seats.
- **R4:** a voucher is honoured only while it is valid and has usages left.

**Ownership (2 use cases per member, as the brief requires):**

| UC | Title | Owner | Workflow |
| :-: | :--- | :--- | :-: |
| UC-1 | Organizer configures ticket item and quota | Zubair | W1 |
| UC-2 | Organizer publishes event and defines sales window | Zubair | W1 |
| UC-3 | Customer selects tickets and completes checkout | Sami | W2 |
| UC-4 | Customer applies a voucher code | Sami | W2 |
| UC-5 | Customer attempts to buy a sold-out category | Tawassul | W1 × W2 |
| UC-6 | Customer cancels a pending order before expiry | Tawassul | W2 |

Every flow below is automated in `test_e2e_usecases.py`. The test name is given in brackets. Each test asserts both the UI (URL, alert or page text) and the database state.

---

## UC-1 Organizer configures ticket item and quota

| | |
| :--- | :--- |
| **Primary actor** | Organizer |
| **Goal** | A new ticket item exists with a capacity that customers can buy against |
| **Preconditions** | Organizer is logged in with product permissions. The event `sqe-conf` exists. |
| **Trigger** | Organizer opens *Products → Create a new product* (`/control/event/sqe-org/sqe-conf/items/add`) |
| **Rules** | R2 (item needs a quota to be sold) |

**Main success scenario** [`test_uc1_main_create_item_with_new_quota`]
1. Organizer enters the item name "Workshop Ticket" and the default price 25.00.
2. Organizer selects "Create a new quota for this product" with size 40.
3. Organizer presses *Save*.
4. System stores the item, creates quota "Workshop Ticket" (size 40) linked to it, and shows *Your changes have been saved*.

**Alternative flows**
- **A1. Add to an existing quota** [`test_uc1_alt_add_item_to_existing_quota`]. At step 2 the organizer selects an existing quota. The new item shares that capacity; no new quota is created.
- **A2. Create the quota from the quota page** [`test_uc1_alt_create_quota_from_quota_page`]. The organizer opens *Quotas → Create a new quota*, enters name, size 5 and ticks the item. The quota is stored and linked.

**Exception flows**
- **E1. Negative price** [`test_uc1_exc_negative_price_rejected_in_backoffice`]. At step 1 the price is −5.00. Expected: the form shows a validation error and nothing is stored. **Observed: the item is saved with −5.00 (defect A3-D01, strict xfail).**
- **E2. Quota without name** [`test_uc1_exc_quota_without_name_rejected`]. The quota form is submitted with an empty name. The form shows an error and no quota is stored.

**Postconditions:** the item exists, is linked to at least one quota, and `Quota.availability()` equals its size.

---

## UC-2 Organizer publishes event and defines sales window

| | |
| :--- | :--- |
| **Primary actor** | Organizer (customer observes the result) |
| **Goal** | Customers can buy only while the shop is live and inside the sales window |
| **Preconditions** | The event has an item with quota (UC-1 done). Organizer is logged in. |
| **Trigger** | Organizer opens *Shop status* (`/control/event/sqe-org/sqe-conf/live/`) |
| **Rules** | R2 |

**Main success scenario** [`test_uc2_main_organizer_takes_shop_live`]
1. The shop is offline; the organizer presses *Go live*.
2. System sets `Event.live = True`.
3. A new visitor opens the shop and sees the product list with an *Add to cart* button.

**Alternative flows**
- **A1. Take the shop offline** [`test_uc2_alt_take_shop_offline`]. The organizer takes the live shop offline. `Event.live = False`, and visitors no longer see *Add to cart*.
- **A2. Sales start in the future** [`test_uc2_alt_sales_not_started_yet`]. `presale_start` is two days ahead. The shop shows *The booking period for this event will start on …* and offers no cart button. No reservation is possible.

**Exception flows**
- **E1. Sales period over** [`test_uc2_exc_sales_period_over`]. `presale_end` is in the past. The shop shows *The booking period for this event is over*, and even a crafted POST to `cart/add` creates no cart position.
- **E2. End before start** [`test_uc2_exc_end_before_start_rejected`]. In *Settings* the organizer enters an end date before the start date. The form shows an error and the stored window stays valid.

**Postconditions:** `Event.live` and the presale window in the database match what the customer sees.

---

## UC-3 Customer selects tickets, enters details and completes checkout

| | |
| :--- | :--- |
| **Primary actor** | Customer |
| **Goal** | A pending order exists and the seats are reserved on the quota |
| **Preconditions** | The shop is live and in the sales window. Item "General Admission Ticket" (50.00) has quota size 10. Bank transfer is enabled. |
| **Trigger** | Customer opens the shop page |
| **Rules** | R1, R2, R3 |

**Main success scenario** [`test_uc3_main_checkout_one_ticket`]
1. Customer sets the quantity to 1 and presses *Add to cart*. System reserves a cart position for 30 minutes.
2. Customer presses *Proceed with checkout*.
3. Customer enters an email address (*Your information*) and continues.
4. Customer selects *Bank transfer* (*Payment*) and continues.
5. Customer reviews the order and confirms.
6. System creates the order with status *pending* and redirects to `/order/{code}/{secret}/?thanks=yes` with *Your order has been placed successfully*.

Database checks: one order with 1 position and total 50.00; the cart is emptied; quota availability drops from 10 to 9.

**Alternative flows**
- **A1. Several tickets** [`test_uc3_alt_two_tickets`]. Quantity 2 at step 1. The order has 2 positions, total 100.00, and availability is 8.
- **A2. Change the cart before checkout** [`test_uc3_alt_remove_ticket_before_checkout`]. After adding 2 tickets the customer removes one in the cart. Checkout then creates an order with 1 position.

**Exception flows**
- **E1. Invalid email** [`test_uc3_exc_invalid_email`]. At step 3 the email is `not-an-email`. The page stays on *Your information* with a field error. No order is created and the reservation is kept.
- **E2. Reservation expired and seats gone** [`test_uc3_exc_cart_expired_before_confirm`]. The cart expires on the review page while all seats are taken. Confirming shows an error and no order is created (R1 is protected).

**Postconditions:** order status *pending*; the quota is reduced by the ordered quantity.

---

## UC-4 Customer applies a voucher code during checkout

| | |
| :--- | :--- |
| **Primary actor** | Customer |
| **Goal** | The order is priced with the voucher and the voucher's usage is recorded |
| **Preconditions** | UC-3 preconditions. Voucher `SQE20OFF` (−20 %, max 1 use) exists for the item. |
| **Trigger** | Customer opens `/redeem?voucher=SQE20OFF` from a link |
| **Rules** | R4 |

**Main success scenario** [`test_uc4_main_percentage_voucher`]
1. System shows *Voucher redemption* with the item at the reduced price 40.00.
2. Customer adds the item to the cart and completes checkout (UC-3 steps 2–5).
3. System creates the order with total 40.00, links the position to the voucher and sets `Voucher.redeemed = 1`.

**Alternative flows**
- **A1. Fixed-price voucher** [`test_uc4_alt_fixed_price_voucher`]. Voucher `FIXED15` sets the price to 15.00, and the order total is 15.00.
- **A2. Code typed on the shop page** [`test_uc4_alt_voucher_entered_on_shop_page`]. The customer types the code in the shop's voucher box instead of using a link, and reaches the same redemption page.

**Exception flows**
- **E1. Unknown code** [`test_uc4_exc_unknown_voucher`]. The system shows an error and nothing is reserved.
- **E2. Voucher already used up** [`test_uc4_exc_voucher_already_used`]. `redeemed = max_usages`. The system shows that the voucher has already been used, and no reservation or order is created.

**Postconditions:** `Voucher.redeemed` is incremented exactly once per order.

---

## UC-5 Customer attempts to purchase tickets for a sold-out category

| | |
| :--- | :--- |
| **Primary actor** | Customer |
| **Goal** | The system never sells more seats than the quota (shared record of W1 and W2) |
| **Preconditions** | The shop is live. The item's quota has no seats left. |
| **Trigger** | Customer opens the shop page |
| **Rules** | R1, R2 |

**Main success scenario** [`test_uc5_main_sold_out_is_shown_and_not_bookable`]
1. System shows the item as *SOLD OUT* without a quantity box.
2. The customer cannot reserve; no cart position exists and availability stays at 0.

**Alternative flows**
- **A1. Waiting list** [`test_uc5_alt_join_waiting_list`]. With the waiting list enabled, the customer follows *Join waiting list*, enters an email and is stored as a `WaitingListEntry`.
- **A2. Another category is still free** [`test_uc5_alt_other_category_still_bookable`]. The customer buys "VIP Ticket" from its own quota. VIP availability drops and the sold-out quota is untouched.

**Exception flows**
- **E1. Last seat taken during checkout** [`test_uc5_exc_last_seat_taken_during_checkout`]. The customer holds the last seat, the reservation expires, and another customer buys the seat. Confirming shows an error and only the other order exists (no overbooking).
- **E2. Quota closed by organizer** [`test_uc5_exc_closed_quota`]. The quota is closed. The shop shows *SOLD OUT* and a crafted `cart/add` POST reserves nothing.

**Postconditions:** the number of orders and reservations never exceeds `Quota.size`.

---

## UC-6 Customer cancels an unconfirmed (pending) order before expiration

| | |
| :--- | :--- |
| **Primary actor** | Customer (organizer in A2) |
| **Goal** | The pending order is canceled and its seats return to the quota |
| **Preconditions** | A pending order exists (UC-3). The setting *customers can cancel unpaid orders* is on. |
| **Trigger** | Customer opens `/order/{code}/{secret}/cancel` |
| **Rules** | R3 |

**Main success scenario** [`test_uc6_main_customer_cancels_pending_order`]
1. System shows the cancellation confirmation page.
2. Customer confirms the cancellation.
3. System sets the order to *canceled*, shows a confirmation and releases the seat (availability back from 9 to 10).

**Alternative flows**
- **A1. From the order page** [`test_uc6_alt_cancel_link_from_order_page`]. The customer follows *Cancel order* on the order page instead of a direct link.
- **A2. Organizer cancels** [`test_uc6_alt_organizer_cancels_in_backoffice`]. The organizer cancels the order in the back office (`orders/{code}/transition?status=c`), with the same result.

**Exception flows**
- **E1. Wrong secret** [`test_uc6_exc_wrong_secret_is_404`]. The cancel URL with a wrong secret returns HTTP 404, and the order stays pending.
- **E2. Self-cancellation disabled** [`test_uc6_exc_self_cancel_disabled`]. With the setting off, no *Cancel order* link is shown, the cancel URL does not cancel, and the order and its seat stay as they were.

**Postconditions:** a canceled order holds no seats; an order that was not canceled is unchanged.
