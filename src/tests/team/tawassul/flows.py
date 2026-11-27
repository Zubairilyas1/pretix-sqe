"""
Reusable browser steps for the pretix shop and back office.

Each helper only drives the UI through the real pretix pages; the database
assertions stay in the tests so every test shows both sides.
"""
import re

from playwright.sync_api import Page, expect

CUSTOMER_EMAIL = "customer@sqe.test"
ORDER_URL = re.compile(r"/order/(?P<code>[A-Z0-9]+)/(?P<secret>[a-z0-9]+)/")


def add_to_cart(page: Page, shop_url: str, item, quantity: int = 1):
    """Shop page: set the quantity for one item and press 'Add to cart'."""
    page.goto(shop_url)
    set_quantity(page, item, quantity)
    page.click("#btn-add-to-cart")
    page.wait_for_load_state("networkidle")


def set_quantity(page: Page, item, quantity: int = 1):
    """pretix shows a number box, or a single checkbox when at most one ticket can be bought
    (e.g. one seat left, or a voucher page)."""
    box = page.locator(f"input[name=item_{item.pk}]").first
    if not box.count():                       # voucher page: one radio per product
        page.check(f"input[name=_selected_item][value=item_{item.pk}]")
        return
    if box.get_attribute("type") in ("checkbox", "radio"):
        box.check()
    else:
        box.fill(str(quantity))


def proceed_to_checkout(page: Page):
    page.get_by_role("button", name=re.compile("Proceed with checkout", re.I)).click()
    page.wait_for_url("**/checkout/questions/**")


def fill_contact(page: Page, email: str = CUSTOMER_EMAIL):
    page.fill("input[name=email]", email)
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_load_state("networkidle")


def choose_bank_transfer(page: Page):
    page.check("input[name=payment][value=banktransfer]")
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url("**/checkout/confirm/")


def confirm_order(page: Page):
    """Review page: press the final button and wait for the order page."""
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url(ORDER_URL)
    m = ORDER_URL.search(page.url)
    return m.group("code"), m.group("secret")


def buy(page: Page, shop_url: str, item, quantity: int = 1, email: str = CUSTOMER_EMAIL):
    """Full UC-3 main success scenario. Returns (order code, order secret)."""
    add_to_cart(page, shop_url, item, quantity)
    proceed_to_checkout(page)
    fill_contact(page, email)
    choose_bank_transfer(page)
    return confirm_order(page)


def expect_alert(page: Page, text: str):
    """pretix shows success and error messages as Bootstrap alerts."""
    expect(page.locator(".alert").filter(has_text=text).first).to_be_visible()
