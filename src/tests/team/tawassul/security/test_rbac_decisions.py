"""
Role-based access control decisions (Task 3.3.1), automated with Playwright.

Each row of ``rbac_access_matrix.md`` marked "automated" is one parametrised
case here. A decision is checked by the HTTP status (or the redirect target)
that a real browser session of that role receives, and, for writes, by the
database not changing.
"""
import re

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Item, Order, Team, User

from ..conftest import ORGANIZER_PASSWORD
from ..flows import buy

pytestmark = pytest.mark.django_db(transaction=True)

EV = "/control/event/sqe-org/sqe-conf"
VIEWER_EMAIL = "viewer@sqe.test"


@pytest.fixture
def viewer_login(page, live_url, team_organizer, shop):
    """A team member who may only *view* orders (no product permissions)."""
    user = User.objects.create_user(VIEWER_EMAIL, ORGANIZER_PASSWORD)
    with scopes_disabled():
        team = Team.objects.create(organizer=team_organizer, name="Read-only", all_events=True,
                                   limit_event_permissions={"event.orders:read": True})
        team.members.add(user)
    page.goto(f"{live_url}/control/login")
    page.fill("input[name=email]", VIEWER_EMAIL)
    page.fill("input[name=password]", ORGANIZER_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r"/control/(?!login)"))
    return page


# --- Organizer role ----------------------------------------------------------

def test_rbac_organizer_can_open_control(control_login, live_url):
    resp = control_login.goto(f"{live_url}/control/")
    assert resp.status == 200
    assert "/control/login" not in control_login.url


def test_rbac_organizer_can_open_item_editor(control_login, live_url, shop):
    resp = control_login.goto(f"{live_url}{EV}/items/add")
    assert resp.status == 200


# --- Customer role (anonymous shop visitor) ----------------------------------

def test_rbac_customer_can_open_presale(page, shop_url):
    resp = page.goto(shop_url)
    assert resp.status == 200


def test_rbac_customer_is_sent_to_login_for_control(page, live_url, shop):
    page.goto(f"{live_url}/control/")
    assert re.search(r"/control/login(\?|$)", page.url), page.url


def test_rbac_customer_cannot_open_event_backoffice(page, live_url, shop):
    page.goto(f"{live_url}{EV}/orders/")
    assert "/control/login" in page.url


def test_rbac_customer_cannot_view_other_order_without_secret(page, live_url, shop_url, team_item):
    code, secret = buy(page, shop_url, team_item)
    other = page.context.browser.new_context().new_page()          # a different customer
    resp = other.goto(f"{live_url}/sqe-org/sqe-conf/order/{code}/{secret[:-1]}x/")
    assert resp.status == 404
    resp = other.goto(f"{live_url}/sqe-org/sqe-conf/order/{code}/")
    assert resp.status == 404
    other.context.close()


def test_rbac_customer_cannot_guess_order_with_wrong_code(page, live_url, shop_url, team_item):
    _, secret = buy(page, shop_url, team_item)
    resp = page.goto(f"{live_url}/sqe-org/sqe-conf/order/ZZZZZ/{secret}/")
    assert resp.status == 404


# --- Organizer team member with limited rights ------------------------------

def test_rbac_viewer_can_list_orders(viewer_login, live_url):
    resp = viewer_login.goto(f"{live_url}{EV}/orders/")
    assert resp.status == 200


def test_rbac_viewer_cannot_create_items(viewer_login, live_url, shop):
    before = Item.objects.filter(event=shop).count()
    resp = viewer_login.goto(f"{live_url}{EV}/items/add")
    assert resp.status == 403
    assert Item.objects.filter(event=shop).count() == before


def test_rbac_viewer_cannot_cancel_orders(viewer_login, live_url, shop_url, team_item):
    customer = viewer_login.context.browser.new_context().new_page()
    code, _ = buy(customer, shop_url, team_item)
    customer.context.close()
    resp = viewer_login.goto(f"{live_url}{EV}/orders/{code}/transition?status=c")
    assert resp.status == 403
    with scopes_disabled():
        assert Order.objects.get(code=code).status == Order.STATUS_PENDING
