"""
Keyboard-only checkout (Task 3.2.1).

The whole purchase is done with Tab / Shift+Tab / Enter / Space plus typing the
email address; the mouse is never used. The test records where focus goes after
every Tab and asserts that:

* every required field and the submit button are reachable by keyboard,
* they are reached in a logical order (top to bottom of the form),
* the order is finally created in the database.
"""
import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Order

from ..flows import CUSTOMER_EMAIL

pytestmark = pytest.mark.django_db(transaction=True)

DESCRIBE = """() => {
  const e = document.activeElement;
  if (!e || e === document.body) return 'body';
  return [e.tagName.toLowerCase(), e.getAttribute('name') || '', e.id || '',
          (e.innerText || e.value || '').trim().slice(0, 30)].join('|');
}"""


def tab_to(page, selector, limit=80, backwards=False):
    """Press Tab until the focused element matches ``selector``; return the focus path."""
    path = []
    for _ in range(limit):
        if page.evaluate("s => document.activeElement && document.activeElement.matches(s)", selector):
            return path
        page.keyboard.press("Shift+Tab" if backwards else "Tab")
        path.append(page.evaluate(DESCRIBE))
    raise AssertionError(f"{selector!r} not reachable by keyboard within {limit} Tabs; path: {path}")


def test_keyboard_only_checkout(page, shop_url, shop, team_item, team_quota):
    page.goto(shop_url)

    # 1. product list: quantity box, then the Add to cart button
    tab_to(page, f"input[name=item_{team_item.pk}]")
    page.keyboard.press("Control+A")
    page.keyboard.type("1")
    tab_to(page, "#btn-add-to-cart")
    with page.expect_navigation():
        page.keyboard.press("Enter")

    # 2. cart: reach "Proceed with checkout"
    tab_to(page, "main button.btn-primary.btn-lg[type=submit]")
    with page.expect_navigation():
        page.keyboard.press("Enter")
    page.wait_for_url("**/checkout/questions/**")

    # 3. contact form: email has autofocus; record the order of the rest
    assert page.evaluate("document.activeElement.name") == "email"
    page.keyboard.type(CUSTOMER_EMAIL)
    # the optional invoice address is a collapsed <details>; it must open with the keyboard
    tab_to(page, "main form summary")
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.parentElement.open"), "Enter did not expand the section"
    path = tab_to(page, "main form button[type=submit].btn-primary")
    names = [p.split("|")[1] for p in path]
    for field in ("name_parts_0", "name_parts_1", "street", "zipcode", "city", "country"):
        assert field in names, f"{field} skipped by Tab; focus path was {path}"
    order = [names.index(f) for f in ("name_parts_0", "name_parts_1", "street", "zipcode", "city", "country")]
    assert order == sorted(order), f"invoice fields not in visual (top-to-bottom) order: {path}"
    with page.expect_navigation():
        page.keyboard.press("Enter")

    # 4. payment: choose bank transfer with Space, then submit with Enter
    page.wait_for_url("**/checkout/payment/")
    tab_to(page, "input[name=payment][value=banktransfer]")
    page.keyboard.press("Space")
    assert page.is_checked("input[name=payment][value=banktransfer]")
    tab_to(page, "main form button[type=submit].btn-primary")
    with page.expect_navigation():
        page.keyboard.press("Enter")

    # 5. review page: the confirm button must be reachable and work with Enter
    page.wait_for_url("**/checkout/confirm/")
    tab_to(page, "main form button[type=submit].btn-primary")
    with page.expect_navigation():
        page.keyboard.press("Enter")
    page.wait_for_url("**/order/**")

    with scopes_disabled():
        order = Order.objects.get(event=shop)
        assert order.email == CUSTOMER_EMAIL
        assert order.status == Order.STATUS_PENDING
        assert order.positions.count() == 1


def test_focus_is_visible_on_add_to_cart(page, shop_url, shop, team_item):
    """WCAG 2.4.7 Focus Visible: the focused button must show an outline or a changed style."""
    page.goto(shop_url)
    tab_to(page, "#btn-add-to-cart")
    style = page.evaluate("""() => { const s = getComputedStyle(document.activeElement);
        return {outline: s.outlineStyle + ' ' + s.outlineWidth, shadow: s.boxShadow}; }""")
    assert not style["outline"].startswith("none") or style["shadow"] != "none", style


def test_skip_link_reaches_main_content(page, shop_url, shop):
    """WCAG 2.4.1 Bypass Blocks: the first Tab stop is a 'skip to content' link."""
    page.goto(shop_url)
    page.keyboard.press("Tab")
    first = page.evaluate("() => [document.activeElement.tagName, document.activeElement.getAttribute('href'),"
                          " document.activeElement.innerText.trim()]")
    assert first[0] == "A" and first[1] and first[1].startswith("#"), first
