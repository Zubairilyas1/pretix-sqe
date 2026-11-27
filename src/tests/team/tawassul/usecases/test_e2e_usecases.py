"""
Playwright (Chromium) end-to-end tests for use cases UC-1 to UC-6.

Every flow in ``use_case_spec.md`` has one test named ``test_ucN_<flow>``.
Each test checks the UI (URL, alert, page text) AND the database (orders,
cart positions, quota availability, vouchers), because a UI message alone can
be shown while nothing is stored.

Run:  cd src && ../.venv/Scripts/python -m pytest tests/team/tawassul/usecases -v
"""
import datetime
import re
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled
from playwright.sync_api import expect

from pretix.base.models import (
    CartPosition, Event, Item, Order, Quota, Voucher, WaitingListEntry,
)

from ..conftest import available, orders
from ..flows import (
    ORDER_URL, add_to_cart, buy, choose_bank_transfer, confirm_order,
    expect_alert, fill_contact, proceed_to_checkout, set_quantity,
)

pytestmark = pytest.mark.django_db(transaction=True)

CONTROL = "/control/event/sqe-org/sqe-conf"


def _item(event, name):
    """Item.name is a translated field, so match on its text."""
    return next(i for i in Item.objects.filter(event=event) if str(i.name) == name)


def _reload(obj):
    with scopes_disabled():
        return type(obj).objects.get(pk=obj.pk)


def _submit(page):
    page.locator("button.btn-save").first.click()
    page.wait_for_load_state("networkidle")


# =============================================================================
# UC-1  Organizer configures a ticket item and its quota (W1)
# =============================================================================

def test_uc1_main_create_item_with_new_quota(control_login, live_url, shop):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/items/add")
    page.fill("#id_name_0", "Workshop Ticket")
    page.fill("#id_default_price", "25.00")
    page.check("#id_quota_option_2")                      # "Create a new quota for this product"
    page.fill("input[name=quota_add_new_size]", "40")
    _submit(page)
    expect(page).to_have_url(re.compile(r"/items/\d+/"))
    expect_alert(page, "Your changes have been saved")
    with scopes_disabled():
        item = _item(shop, "Workshop Ticket")
        quota = item.quotas.get()
        assert item.default_price == Decimal("25.00")
        assert quota.size == 40
    assert available(quota) == 40


def test_uc1_alt_add_item_to_existing_quota(control_login, live_url, shop, team_quota):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/items/add")
    page.fill("#id_name_0", "Student Ticket")
    page.fill("#id_default_price", "10.00")
    page.check("#id_quota_option_1")                      # "Add product to an existing quota"
    page.select_option("select[name=quota_add_existing]", str(team_quota.pk))
    _submit(page)
    expect_alert(page, "Your changes have been saved")
    with scopes_disabled():
        item = _item(shop, "Student Ticket")
        assert list(item.quotas.all()) == [team_quota]     # shares the 10 seats with General Admission


def test_uc1_alt_create_quota_from_quota_page(control_login, live_url, shop, team_item):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/quotas/add")
    page.fill("#id_name", "Balcony")
    page.fill("#id_size", "5")
    page.check(f"input[name=itemvars][value='{team_item.pk}']")
    _submit(page)
    expect_alert(page, "The new quota has been created")
    with scopes_disabled():
        q = Quota.objects.get(event=shop, name="Balcony")
        assert q.size == 5 and team_item in q.items.all()


@pytest.mark.xfail(strict=True, reason="A3-D01: back office saves a negative item price "
                   "(no MinValueValidator on Item.default_price; same root cause as API weakness W-01)")
def test_uc1_exc_negative_price_rejected_in_backoffice(control_login, live_url, shop):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/items/add")
    page.fill("#id_name_0", "Broken Ticket")
    page.fill("#id_default_price", "-5.00")
    page.check("#id_quota_option_0")
    _submit(page)
    expect(page.locator(".has-error, .alert-danger").first).to_be_visible()
    with scopes_disabled():
        assert all(str(i.name) != "Broken Ticket" for i in Item.objects.filter(event=shop))


def test_uc1_exc_quota_without_name_rejected(control_login, live_url, shop):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/quotas/add")
    before = Quota.objects.count()
    page.fill("#id_size", "5")
    page.evaluate("document.querySelector('#id_name').removeAttribute('required')")
    _submit(page)
    expect(page.locator(".has-error, .alert-danger").first).to_be_visible()
    assert Quota.objects.count() == before


# =============================================================================
# UC-2  Organizer publishes the event and defines the sales window
# =============================================================================

def _set_presale(event, start=None, end=None):
    with scopes_disabled():
        Event.objects.filter(pk=event.pk).update(presale_start=start, presale_end=end)


def test_uc2_main_organizer_takes_shop_live(control_login, live_url, shop, page):
    Event.objects.filter(pk=shop.pk).update(live=False)
    control_login.goto(f"{live_url}{CONTROL}/live/")
    control_login.get_by_role("button", name=re.compile("Go live", re.I)).click()
    control_login.wait_for_load_state("networkidle")
    assert _reload(shop).live is True
    # a fresh visitor (no organizer session) now sees the shop with an add-to-cart button
    visitor = control_login.context.browser.new_context().new_page()
    visitor.goto(f"{live_url}/sqe-org/sqe-conf/")
    expect(visitor.locator("#btn-add-to-cart")).to_be_visible()
    visitor.context.close()


def test_uc2_alt_take_shop_offline(control_login, live_url, shop):
    control_login.goto(f"{live_url}{CONTROL}/live/")
    control_login.get_by_role("button", name=re.compile("Take shop offline|Go offline", re.I)).click()
    control_login.wait_for_load_state("networkidle")
    assert _reload(shop).live is False
    visitor = control_login.context.browser.new_context().new_page()
    visitor.goto(f"{live_url}/sqe-org/sqe-conf/")
    expect(visitor.locator("#btn-add-to-cart")).to_have_count(0)
    visitor.context.close()


def test_uc2_alt_sales_not_started_yet(page, shop_url, shop):
    _set_presale(shop, start=now() + datetime.timedelta(days=2), end=now() + datetime.timedelta(days=10))
    page.goto(shop_url)
    expect(page.get_by_text(re.compile("booking period for this event will start", re.I))).to_be_visible()
    expect(page.locator("#btn-add-to-cart")).to_have_count(0)
    assert CartPosition.objects.count() == 0


def test_uc2_exc_sales_period_over(page, shop_url, shop, team_item):
    _set_presale(shop, start=now() - datetime.timedelta(days=10), end=now() - datetime.timedelta(minutes=1))
    page.goto(shop_url)
    expect(page.get_by_text("booking period for this event is over")).to_be_visible()
    # a crafted POST to the cart endpoint must not reserve anything either
    resp = page.request.post(f"{shop_url}cart/add", form={f"item_{team_item.pk}": "1"})
    assert resp.status in (200, 302, 403)
    assert CartPosition.objects.count() == 0


def test_uc2_exc_end_before_start_rejected(control_login, live_url, shop):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/settings/")
    tomorrow = (now() + datetime.timedelta(days=1)).date().isoformat()
    yesterday = (now() - datetime.timedelta(days=1)).date().isoformat()
    for field, day in (("presale_start", tomorrow), ("presale_end", yesterday)):
        page.evaluate(
            "([n, d]) => { document.querySelector(`input[name=${n}_0]`).value = d;"
            " document.querySelector(`input[name=${n}_1]`).value = '10:00'; }",
            [field, day],
        )
    _submit(page)
    expect(page.locator(".has-error, .alert-danger").first).to_be_visible()
    s = _reload(shop)
    assert s.presale_end is None or s.presale_end > s.presale_start


# =============================================================================
# UC-3  Customer selects tickets, enters details and completes checkout (W2)
# =============================================================================

def test_uc3_main_checkout_one_ticket(page, shop_url, shop, team_item, team_quota):
    code, secret = buy(page, shop_url, team_item)
    expect(page).to_have_url(re.compile(r"thanks=yes"))
    expect(page.get_by_text("Your order has been placed successfully")).to_be_visible()
    with scopes_disabled():
        order = Order.objects.get(code=code)
        assert order.secret == secret
        assert order.status == Order.STATUS_PENDING
        assert order.email == "customer@sqe.test"
        assert order.positions.count() == 1 and order.total == Decimal("50.00")
        assert CartPosition.objects.count() == 0            # cart turned into the order
    assert available(team_quota) == 9                      # shared record consumed


def test_uc3_alt_two_tickets(page, shop_url, shop, team_item, team_quota):
    code, _ = buy(page, shop_url, team_item, quantity=2)
    with scopes_disabled():
        order = Order.objects.get(code=code)
        assert order.positions.count() == 2 and order.total == Decimal("100.00")
    assert available(team_quota) == 8


def test_uc3_alt_remove_ticket_before_checkout(page, shop_url, shop, team_item, team_quota):
    add_to_cart(page, shop_url, team_item, quantity=2)
    assert CartPosition.objects.count() == 2
    with page.expect_navigation():
        page.locator("button[title^='Remove one General Admission Ticket']").locator("visible=true").first.click()
    expect_alert(page, "Your cart has been updated")
    assert CartPosition.objects.count() == 1
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    code, _ = confirm_order(page)
    with scopes_disabled():
        assert Order.objects.get(code=code).positions.count() == 1
    assert available(team_quota) == 9


def test_uc3_exc_invalid_email(page, shop_url, shop, team_item):
    add_to_cart(page, shop_url, team_item)
    proceed_to_checkout(page)
    page.evaluate("document.querySelector('input[name=email]').type = 'text'")  # bypass browser check
    fill_contact(page, email="not-an-email")
    expect(page).to_have_url(re.compile("/checkout/questions/"))
    expect(page.locator(".has-error").first).to_be_visible()
    assert orders(shop) == []
    assert CartPosition.objects.count() == 1                # reservation kept for correction


def test_uc3_exc_cart_expired_before_confirm(page, shop_url, shop, team_item, team_quota):
    add_to_cart(page, shop_url, team_item)
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    # the reservation runs out while the customer is on the review page,
    # and in the meantime someone else takes all remaining seats
    CartPosition.objects.update(expires=now() - datetime.timedelta(minutes=1))
    Quota.objects.filter(pk=team_quota.pk).update(size=0)
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_load_state("networkidle")
    assert not ORDER_URL.search(page.url)
    expect(page.locator(".alert-danger").first).to_be_visible()
    assert orders(shop) == []


# =============================================================================
# UC-4  Customer applies a voucher code during checkout
# =============================================================================

@pytest.fixture
def voucher(shop, team_item):
    with scopes_disabled():
        return Voucher.objects.create(event=shop, code="SQE20OFF", item=team_item,
                                      price_mode="percent", value=Decimal("20.00"), max_usages=1)


def _redeem(page, shop_url, code):
    page.goto(f"{shop_url}redeem?voucher={code}")
    page.wait_for_load_state("networkidle")


def _buy_after_redeem(page, item):
    set_quantity(page, item, 1)
    page.click("#btn-add-to-cart")
    page.wait_for_load_state("networkidle")
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    return confirm_order(page)


def test_uc4_main_percentage_voucher(page, shop_url, shop, team_item, voucher):
    _redeem(page, shop_url, "SQE20OFF")
    code, _ = _buy_after_redeem(page, team_item)
    with scopes_disabled():
        order = Order.objects.get(code=code)
        assert order.total == Decimal("40.00")             # 50.00 minus 20 %
        assert order.positions.get().voucher == voucher
        assert Voucher.objects.get(pk=voucher.pk).redeemed == 1


def test_uc4_alt_fixed_price_voucher(page, shop_url, shop, team_item):
    with scopes_disabled():
        Voucher.objects.create(event=shop, code="FIXED15", item=team_item, price_mode="set", value=Decimal("15.00"))
    _redeem(page, shop_url, "FIXED15")
    code, _ = _buy_after_redeem(page, team_item)
    with scopes_disabled():
        assert Order.objects.get(code=code).total == Decimal("15.00")


def test_uc4_alt_voucher_entered_on_shop_page(page, shop_url, shop, team_item, voucher):
    page.goto(shop_url)
    page.fill("input[name=voucher]", "SQE20OFF")
    page.locator("form[action*='redeem'] button[type=submit]").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile("redeem"))
    code, _ = _buy_after_redeem(page, team_item)
    with scopes_disabled():
        assert Order.objects.get(code=code).total == Decimal("40.00")


def test_uc4_exc_unknown_voucher(page, shop_url, shop):
    _redeem(page, shop_url, "NOSUCHCODE")
    expect(page.locator(".alert-danger").first).to_contain_text(re.compile("not known|invalid|not valid", re.I))
    assert CartPosition.objects.count() == 0


def test_uc4_exc_voucher_already_used(page, shop_url, shop, team_item, voucher):
    Voucher.objects.filter(pk=voucher.pk).update(redeemed=1)  # max_usages = 1 already reached
    _redeem(page, shop_url, "SQE20OFF")
    expect(page.locator(".alert-danger").first).to_contain_text(re.compile("already been used|redeemed", re.I))
    assert CartPosition.objects.count() == 0
    assert orders(shop) == []


# =============================================================================
# UC-5  Customer attempts to buy a sold-out category (shared record at 0)
# =============================================================================

def _sell_out(quota):
    Quota.objects.filter(pk=quota.pk).update(size=0)


def test_uc5_main_sold_out_is_shown_and_not_bookable(page, shop_url, shop, team_quota):
    _sell_out(team_quota)
    page.goto(shop_url)
    expect(page.get_by_text("SOLD OUT").first).to_be_visible()
    expect(page.locator("input.input-item-count")).to_have_count(0)
    assert available(team_quota) == 0
    assert CartPosition.objects.count() == 0


def test_uc5_alt_join_waiting_list(page, shop_url, shop, team_item, team_quota):
    shop.settings.set("waiting_list_enabled", True)
    _sell_out(team_quota)
    page.goto(shop_url)
    page.get_by_role("link", name=re.compile("waiting list", re.I)).first.click()
    page.fill("input[name=email]", "waiting@sqe.test")
    page.locator("main form button[type=submit]").last.click()
    page.wait_for_load_state("networkidle")
    expect_alert(page, "waiting list")
    with scopes_disabled():
        assert WaitingListEntry.objects.filter(event=shop, email="waiting@sqe.test", item=team_item).exists()


def test_uc5_alt_other_category_still_bookable(page, shop_url, shop, team_quota):
    with scopes_disabled():
        vip = Item.objects.create(event=shop, name="VIP Ticket", default_price=Decimal("120.00"))
        vq = Quota.objects.create(event=shop, name="VIP", size=2)
        vq.items.add(vip)
    _sell_out(team_quota)
    code, _ = buy(page, shop_url, vip)
    with scopes_disabled():
        assert Order.objects.get(code=code).positions.get().item == vip
    assert available(vq) == 1 and available(team_quota) == 0


def test_uc5_exc_last_seat_taken_during_checkout(page, shop_url, shop, team_item, team_quota):
    Quota.objects.filter(pk=team_quota.pk).update(size=1)
    add_to_cart(page, shop_url, team_item)                 # holds the last seat for 30 minutes
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    CartPosition.objects.update(expires=now() - datetime.timedelta(minutes=1))
    with scopes_disabled():                                # another customer buys the seat meanwhile
        other = Order.objects.create(event=shop, code="OTHER", email="x@sqe.test", status="p", total=50,
                                     datetime=now(), expires=now() + datetime.timedelta(days=1),
                                     sales_channel=shop.organizer.sales_channels.get(identifier="web"))
        other.positions.create(item=team_item, price=50, positionid=1)
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_load_state("networkidle")
    expect(page.locator(".alert-danger").first).to_be_visible()
    assert [o.code for o in orders(shop)] == ["OTHER"]      # no overbooking
    assert available(team_quota) == 0


def test_uc5_exc_closed_quota(page, shop_url, shop, team_item, team_quota):
    Quota.objects.filter(pk=team_quota.pk).update(closed=True)
    page.goto(shop_url)
    expect(page.get_by_text("SOLD OUT").first).to_be_visible()
    resp = page.request.post(f"{shop_url}cart/add", form={f"item_{team_item.pk}": "1"})
    assert resp.status in (200, 302, 403)
    assert CartPosition.objects.count() == 0


# =============================================================================
# UC-6  Customer cancels an unconfirmed (pending) order before it expires
# =============================================================================

@pytest.fixture
def cancellable(shop):
    shop.settings.set("cancel_allow_user", True)
    return shop


def _cancel_page(page, live_url, code, secret):
    page.goto(f"{live_url}/sqe-org/sqe-conf/order/{code}/{secret}/cancel")
    page.wait_for_load_state("networkidle")


def test_uc6_main_customer_cancels_pending_order(page, live_url, shop_url, cancellable, team_item, team_quota):
    code, secret = buy(page, shop_url, team_item)
    assert available(team_quota) == 9
    _cancel_page(page, live_url, code, secret)
    page.locator("main form button[type=submit].btn-danger, main form button[type=submit].btn-primary").first.click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile("canceled", re.I)).first).to_be_visible()
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_CANCELED
    assert available(team_quota) == 10                     # seat returned to the shared record


def test_uc6_alt_cancel_link_from_order_page(page, live_url, shop_url, cancellable, team_item):
    code, secret = buy(page, shop_url, team_item)
    page.get_by_role("link", name=re.compile("Cancel order", re.I)).first.click()
    expect(page).to_have_url(re.compile(r"/cancel$"))
    page.locator("main form button[type=submit]").first.click()
    page.wait_for_load_state("networkidle")
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_CANCELED


def test_uc6_alt_organizer_cancels_in_backoffice(page, control_login, live_url, shop_url, shop, team_item, team_quota):
    customer = control_login.context.browser.new_context().new_page()
    code, _ = buy(customer, shop_url, team_item)
    customer.context.close()
    control_login.goto(f"{live_url}{CONTROL}/orders/{code}/transition?status=c")
    control_login.locator("form button[type=submit].btn-danger, form button[type=submit].btn-primary").first.click()
    control_login.wait_for_load_state("networkidle")
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_CANCELED
    assert available(team_quota) == 10


def test_uc6_exc_wrong_secret_is_404(page, live_url, shop_url, cancellable, team_item):
    code, _ = buy(page, shop_url, team_item)
    resp = page.goto(f"{live_url}/sqe-org/sqe-conf/order/{code}/wrongsecret123/cancel")
    assert resp.status == 404
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_PENDING


def test_uc6_exc_self_cancel_disabled(page, live_url, shop_url, shop, team_item, team_quota):
    shop.settings.set("cancel_allow_user", False)
    code, secret = buy(page, shop_url, team_item)
    expect(page.get_by_role("link", name=re.compile("Cancel order", re.I))).to_have_count(0)
    _cancel_page(page, live_url, code, secret)
    assert "/cancel" not in page.url or page.locator(".alert-danger").count() > 0
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_PENDING
    assert available(team_quota) == 9
