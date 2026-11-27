"""
Security response headers and session cookie attributes (Task 3.3.2).

These are the same checks OWASP ZAP's passive scanner makes
(rules 10020 X-Frame-Options, 10021 X-Content-Type-Options, 10038 CSP,
10010 cookie without HttpOnly, 10054 cookie without SameSite). Asserting them
in the suite keeps the ZAP result from silently regressing.
"""
import pytest

from ..flows import add_to_cart

pytestmark = pytest.mark.django_db(transaction=True)


def _headers(page, url):
    resp = page.goto(url)
    return {k.lower(): v for k, v in resp.all_headers().items()}


@pytest.mark.parametrize("where", ["shop", "control_login"])
def test_clickjacking_protection(page, live_url, shop_url, where):
    url = shop_url if where == "shop" else f"{live_url}/control/login"
    h = _headers(page, url)
    framing_blocked = h.get("x-frame-options", "").upper() in ("DENY", "SAMEORIGIN") or \
        "frame-ancestors" in h.get("content-security-policy", "")
    assert framing_blocked, h


A3_D02 = ("A3-D02: pretix uses its own SecurityMiddleware (CSP, P3P) instead of Django's, "
          "so X-Content-Type-Options and Referrer-Policy are never sent; the nginx guide does not add them")


@pytest.mark.xfail(strict=True, reason=A3_D02)
@pytest.mark.parametrize("where", ["shop", "control_login"])
def test_no_mime_sniffing(page, live_url, shop_url, where):
    url = shop_url if where == "shop" else f"{live_url}/control/login"
    assert _headers(page, url).get("x-content-type-options") == "nosniff"


@pytest.mark.parametrize("where", ["shop", "control_login"])
def test_content_security_policy_present(page, live_url, shop_url, where):
    url = shop_url if where == "shop" else f"{live_url}/control/login"
    csp = _headers(page, url).get("content-security-policy", "")
    assert csp, "no Content-Security-Policy header"
    assert "script-src" in csp or "default-src" in csp, csp


@pytest.mark.xfail(strict=True, reason=A3_D02)
def test_referrer_policy_protects_order_secret(page, shop_url, shop):
    """Order URLs contain the order secret; without a Referrer-Policy the full URL
    is sent as Referer to any external resource or link on the order page."""
    policy = _headers(page, shop_url).get("referrer-policy", "")
    assert policy in ("same-origin", "strict-origin", "strict-origin-when-cross-origin", "no-referrer"), policy


def _set_cookie_headers(page, url, method="GET", form=None):
    """Raw Set-Cookie lines as pretix sends them (the browser's cookie jar would
    report its own defaults instead, e.g. SameSite=Lax when the attribute is absent)."""
    resp = page.request.fetch(url, method=method, form=form)
    return [h["value"] for h in resp.headers_array if h["name"].lower() == "set-cookie"]


def test_session_cookie_is_httponly(page, shop_url, shop, team_item):
    add_to_cart(page, shop_url, team_item)                   # a cart session now exists
    session = [c for c in page.context.cookies() if c["name"].endswith("session")]
    assert session, [c["name"] for c in page.context.cookies()]
    assert all(c["httpOnly"] for c in session), session


def test_cookies_samesite_design_over_http(page, shop_url, shop):
    """Characterisation of a deliberate design (pretix/helpers/cookies.py): to keep the
    shop widget working inside third-party iframes, pretix sends **no** SameSite on
    plain HTTP (browser default Lax applies) and SameSite=None; Secure; Partitioned on
    HTTPS, relying on CSRF tokens instead. ZAP rule 10054 flags this; it is an
    accepted risk, not a defect. If pretix changes the design, this test tells us."""
    lines = [ln for ln in _set_cookie_headers(page, shop_url) if "csrftoken" in ln]
    assert lines, "no CSRF cookie set"
    assert all("samesite" not in ln.lower() for ln in lines), lines
    # the CSRF cookie is readable by JavaScript on purpose (sent back in a header)
    assert all("httponly" not in ln.lower() for ln in lines), lines
