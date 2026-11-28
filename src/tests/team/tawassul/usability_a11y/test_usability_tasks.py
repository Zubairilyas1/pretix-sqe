"""
Automated usability task tests (brief section 3): one task per workflow, performed by a script with test accounts.

TASK-W1  Organizer creates a quota (the shared record) on the quota screen. First a value the business rule
         rejects (size -5, capacity cannot be negative): the screen must explain what to correct; then the
         corrected value; the confirmation must be shown and the quota stored.
         The same form is completed with the KEYBOARD ONLY: focus must reach the required fields and the save
         button in visual order, and Enter must submit.
TASK-W2  Customer buys tickets. First 3 tickets although the product allows at most 2 per order (BR-1 limit):
         the error must name the limit; then 2 tickets; the order confirmation must be shown and the order and
         the quota read-back must match.
"""
import re

import pytest
from django_scopes import scopes_disabled
from playwright.sync_api import expect

from pretix.base.models import Order, Quota

from ..conftest import available
from ..flows import (
    add_to_cart, choose_bank_transfer, confirm_order, fill_contact,
    proceed_to_checkout,
)
from .test_keyboard_nav import DESCRIBE, tab_to

pytestmark = pytest.mark.django_db(transaction=True)
CONTROL = "/control/event/sqe-org/sqe-conf"


def test_task_w1_create_quota_reject_then_correct(control_login, live_url, shop, team_item):
    page = control_login
    page.goto(f"{live_url}{CONTROL}/quotas/add")
    expect(page.get_by_role("heading", name=re.compile("quota", re.I)).first).to_be_visible()   # task screen open
    page.fill("#id_name", "Usability balcony")
    page.check(f"input[name=itemvars][value='{team_item.pk}']")

    # 1. rejected value: negative capacity
    page.fill("#id_size", "-5")
    page.locator("button.btn-save").first.click()
    message = page.locator("#id_size").evaluate("e => e.validationMessage")
    assert "greater than or equal to 0" in message, f"error does not explain the correction: {message!r}"
    expect(page).to_have_url(re.compile(r"/quotas/add"))          # not submitted
    with scopes_disabled():
        assert not Quota.objects.filter(event=shop, name="Usability balcony").exists()

    # 2. corrected value
    page.fill("#id_size", "25")
    page.locator("button.btn-save").first.click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".alert-success").filter(has_text="The new quota has been created")).to_be_visible()
    with scopes_disabled():
        q = Quota.objects.get(event=shop, name="Usability balcony")
        assert q.size == 25 and team_item in q.items.all()


def test_task_w1_keyboard_only_quota_form(control_login, live_url, shop, team_item):
    """Focus order: name -> size -> product checkbox -> save; Space ticks the product, Enter submits."""
    page = control_login
    page.goto(f"{live_url}{CONTROL}/quotas/add")
    page.locator("#id_name").focus()
    page.keyboard.type("Keyboard quota")
    path = tab_to(page, "#id_size")
    page.keyboard.type("7")
    path += tab_to(page, f"input[name=itemvars][value='{team_item.pk}']")
    page.keyboard.press("Space")
    assert page.is_checked(f"input[name=itemvars][value='{team_item.pk}']")
    path += tab_to(page, "button.btn-save")
    # required fields were reached before the save button, in this order
    seq = ["name", "size", "itemvars"]
    visited = [p.split("|")[1] for p in ["input|name"] + path]
    positions = [visited.index(f) for f in seq if f in visited]
    assert len(positions) == 3 and positions == sorted(positions), f"focus order: {path}"
    assert page.evaluate(DESCRIBE).startswith("button")
    with page.expect_navigation():
        page.keyboard.press("Enter")
    expect(page.locator(".alert-success").filter(has_text="The new quota has been created")).to_be_visible()
    with scopes_disabled():
        assert Quota.objects.get(event=shop, name="Keyboard quota").size == 7


def test_task_w2_buy_tickets_reject_then_correct(page, shop_url, shop, team_item, team_quota):
    with scopes_disabled():
        team_item.max_per_order = 2
        team_item.save()
    before = available(team_quota)

    # 1. rejected value: more than the per-order limit
    add_to_cart(page, shop_url, team_item, 3)
    error = page.locator(".alert-danger").first
    expect(error).to_be_visible()
    expect(error).to_contain_text("cannot select more than 2")      # names the limit = how to correct it
    with scopes_disabled():
        assert Order.objects.filter(event=shop).count() == 0
    assert available(team_quota) == before                           # nothing reserved

    # 2. corrected value and complete the purchase
    add_to_cart(page, shop_url, team_item, 2)
    proceed_to_checkout(page)
    fill_contact(page)
    choose_bank_transfer(page)
    code, _ = confirm_order(page)
    expect(page.get_by_text("Your order has been placed successfully")).to_be_visible()
    with scopes_disabled():
        order = Order.objects.get(event=shop, code=code)
        assert order.positions.count() == 2
    assert available(team_quota) == before - 2
