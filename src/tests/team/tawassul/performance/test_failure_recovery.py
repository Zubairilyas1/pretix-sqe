"""
Failure injection and recovery (Task 3.4.2).

A real customer checkout (Playwright, UC-3) is interrupted by a database failure
injected *inside* ``pretix.base.services.orders._create_order``, i.e. after the
Order row has been inserted but before the order is complete. The patch is
applied in the test process, so it affects the live server thread too.

For each injection point the test asserts:

1. graceful failure: the customer sees an error page/message, not a crash page,
   and is not sent to an order page;
2. no partial data: no Order, OrderPosition or OrderPayment is left behind, and
   the quota (shared record) is not consumed by an order;
3. recovery: after the dependency is "restored" (patch removed) the same
   customer retries and exactly one order is created, with no duplicate.
"""
from unittest import mock

import pytest
from django.db import OperationalError
from django_scopes import scopes_disabled

from pretix.base.models import Order, OrderPayment, OrderPosition

from ..conftest import available
from ..flows import (
    ORDER_URL, add_to_cart, choose_bank_transfer, fill_contact,
    proceed_to_checkout,
)

pytestmark = pytest.mark.django_db(transaction=True)

INJECTION_POINTS = {
    # cart positions are being turned into order positions
    "positions": "pretix.base.models.orders.OrderPosition.transform_cart_positions",
    # the order is being booked into the transaction ledger
    "transactions": "pretix.base.models.orders.Order.create_transactions",
}


def _db_counts(event):
    with scopes_disabled():
        return (Order.objects.filter(event=event).count(),
                OrderPosition.all.filter(order__event=event).count(),
                OrderPayment.objects.filter(order__event=event).count())


@pytest.mark.parametrize("point", list(INJECTION_POINTS))
def test_db_failure_during_order_commit_then_recovery(point, page, shop_url, shop, team_item, team_quota):
    add_to_cart(page, shop_url, team_item)
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    seats_before = available(team_quota)                    # 9: the cart holds one seat

    # --- 1. inject the failure and confirm ----------------------------------
    with mock.patch(INJECTION_POINTS[point], side_effect=OperationalError("simulated: database connection lost")):
        page.click("main form button[type=submit].btn-primary")
        page.wait_for_load_state("networkidle")
        assert not ORDER_URL.search(page.url), "customer was sent to an order page although saving failed"
        body = page.inner_text("body")
        assert "Traceback" not in body and "OperationalError" not in body, "internal error leaked to the customer"

    # --- 2. nothing half-saved, shared record consistent ---------------------
    assert _db_counts(shop) == (0, 0, 0)
    assert available(team_quota) == seats_before            # not consumed by a ghost order

    # --- 3. dependency restored: retry once, exactly one order ---------------
    page.goto(shop_url.rstrip("/") + "/checkout/confirm/")
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url(ORDER_URL)
    orders, positions, payments = _db_counts(shop)
    assert (orders, positions) == (1, 1), "retry must create exactly one order with one position"
    assert payments == 1
    assert available(team_quota) == 9
