"""
Shared fixtures for Area 3 (Tawassul): Playwright end-to-end, accessibility and
security tests against a real pretix server started by pytest-django's
``live_server``.

The team fixtures (``team_organizer`` slug ``sqe-org``, ``team_event`` slug
``sqe-conf``, ``team_item``, ``team_quota`` size 10) come from
``tests/team/conftest.py``. Here they are made shop-ready: the event is live,
sales are open, bank transfer is enabled and an organizer user exists.
"""
import datetime
import os
import re
import time

import pytest
from django.utils.timezone import now
from django_scopes import scope, scopes_disabled

import pretix
from pretix.base.models import Order, Quota, Team, User

# Playwright drives the browser from the test thread; Django's ORM is used from
# the same thread for database assertions.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

ORGANIZER_EMAIL = "organizer@sqe.test"
ORGANIZER_PASSWORD = "Sqe-Organizer-2026!"
CUSTOMER_EMAIL = "customer@sqe.test"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 900}, "locale": "en-US"}


@pytest.fixture
def live_url(live_server, settings, browser):
    """Base URL of the running pretix, with SCSS compiled on the fly like pretix's own e2e suite."""
    settings.COMPRESS_ENABLED = True
    settings.COMPRESS_OFFLINE = False
    from pretix.testutils.settings import COMPRESS_PRECOMPILERS_ORIGINAL
    settings.COMPRESS_PRECOMPILERS = COMPRESS_PRECOMPILERS_ORIGINAL
    settings.COMPRESS_CACHE_BACKEND = "default"
    # pretix compiles each event's theme CSS from STATIC_ROOT/pretixbase/scss
    # (pretix/presale/style.py); the test settings leave STATIC_ROOT empty.
    settings.STATIC_ROOT = os.path.join(os.path.dirname(pretix.__file__), "static")
    settings.SITE_URL = live_server.url
    yield live_server.url
    # Close the browser before pytest-django resets the database; an open page
    # still talking to the live server otherwise leaves SQLite tables locked.
    for ctx in list(browser.contexts):
        ctx.close()
    _wait_until_db_writable()


LOCK_PROBE_TABLES = ("pretixbase_organizer", "pretixbase_event", "pretixbase_item", "pretixbase_quota",
                     "pretixbase_cartposition", "pretixbase_order", "pretixbase_user")


def _wait_until_db_writable(timeout=15):
    """The live server thread shares the in-memory SQLite database. A request that
    is still finishing holds a table lock, and the next test's setup or pytest-django's
    flush then fails with 'database table is locked'. Wait until a write lock can be
    taken (and released) before handing the database back."""
    from django.db import OperationalError, connection
    deadline = time.time() + timeout
    while True:
        try:
            with connection.cursor() as cur:
                cur.execute("SAVEPOINT sqe_probe")
                for table in LOCK_PROBE_TABLES:
                    cur.execute(f"UPDATE {table} SET id = id WHERE id = -1")
                cur.execute("RELEASE SAVEPOINT sqe_probe")
            return
        except OperationalError:
            if time.time() > deadline:
                raise
            time.sleep(0.2)


@pytest.fixture
def shop(team_organizer, team_event, team_item, team_quota):
    """W1 done: the event is live and the item can be bought (Rule 2 satisfied)."""
    team_organizer.plugins = "pretix.plugins.banktransfer"
    team_organizer.save()
    with scope(organizer=team_organizer):
        team_event.live = True
        team_event.presale_start = now() - datetime.timedelta(days=1)
        team_event.presale_end = now() + datetime.timedelta(days=20)
        team_event.plugins = "pretix.plugins.banktransfer"
        team_event.save()
        team_event.set_defaults()
        team_event.settings.set("locale", "en")
        team_event.settings.set("locales", ["en"])
        team_event.settings.set("payment_banktransfer__enabled", True)
        team_event.settings.set("payment_banktransfer_bank_details_type", "other")
        team_event.settings.set("payment_banktransfer_bank_details", "SQE test bank account")
        team_event.settings.set("attendee_names_asked", False)
    return team_event


@pytest.fixture
def shop_url(live_url, shop):
    return f"{live_url}/{shop.organizer.slug}/{shop.slug}/"


@pytest.fixture
def organizer_user(team_organizer, team_event):
    """A back-office user with full rights on the team event."""
    user = User.objects.create_user(ORGANIZER_EMAIL, ORGANIZER_PASSWORD)
    with scopes_disabled():
        team = Team.objects.create(
            organizer=team_organizer, name="SQE organizers",
            all_events=True, all_event_permissions=True, all_organizer_permissions=True,
        )
        team.members.add(user)
    return user


@pytest.fixture
def control_login(page, live_url, organizer_user):
    """Log the organizer in through the real login form; returns the page."""
    page.goto(f"{live_url}/control/login")
    page.fill("input[name=email]", ORGANIZER_EMAIL)
    page.fill("input[name=password]", ORGANIZER_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r"/control/(?!login)"))
    return page


def available(quota):
    """Seats left on the shared record, read from the database."""
    with scopes_disabled():
        q = Quota.objects.get(pk=quota.pk)
        return q.availability()[1]


def orders(event):
    with scopes_disabled():
        return list(Order.objects.filter(event=event).order_by("pk"))


@pytest.fixture(autouse=True)
def _scopes_off_in_test_thread():
    """Database assertions in Area 3 tests read across events; pretix's live
    server thread keeps its own scoping, so production behaviour is unchanged."""
    with scopes_disabled():
        yield
