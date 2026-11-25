"""
Business-rule rejections, state transitions, repeated requests and
authorisation, all through the HTTP API.

  Rule 1 (boundary)    quantity vs quota.available_number, 3-point BVA taken
                       from the generator's relative cases
  Rule 2 (decision)    inactive item / item without quota is refused
  Rule 3 (state)       every allowed order transition and at least one
                       disallowed transition from every state
  Repeated requests    same code, same idempotency key, double mark_paid
  Authorisation        organizer vs read-only token vs anonymous
"""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import Order, OrderPayment

DATA = json.loads((Path(__file__).resolve().parent.parent / "generator" / "test_data.json").read_text("utf-8"))


def _relative_cases(operation):
    return [
        pytest.param(c, id=c["id"])
        for c in DATA["cases"]
        if c["operation"] == operation and c["value_kind"] == "relative_to_runtime"
    ]


def _place(api, client, n=1, **kw):
    resp = client.post(api.orders(), api.order_payload(n, **kw), format="json")
    assert resp.status_code == 201, resp.content
    return resp.data["code"]


def _status(api, client, code):
    resp = client.get(api.orders(code))
    assert resp.status_code == 200
    return resp.data["status"]


# ==========================================================================
# Rule 1: quantity must not exceed quota availability (3-point BVA)
# ==========================================================================
@pytest.mark.django_db
@pytest.mark.parametrize("case", _relative_cases("createOrder"))
def test_rule1_order_quantity_vs_available(case, api, organizer_client, team_quota):
    available = api.available(organizer_client, team_quota)
    assert available == 10
    n = available + case["value"]              # 9, 10, 11
    resp = organizer_client.post(api.orders(), api.order_payload(n), format="json")

    if case["expected"] == "accept":
        assert resp.status_code == 201, resp.content
        assert api.available(organizer_client, team_quota) == available - n
    else:
        assert resp.status_code == 400
        assert "not enough quota" in json.dumps(resp.json()).lower()
        assert api.available(organizer_client, team_quota) == available, "rejected order consumed quota"
        assert api.order_count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("case", _relative_cases("createCartPosition"))
def test_rule1_cart_reservation_vs_available(case, api, organizer_client, team_quota):
    """One reservation needs 1 unit. limit-1: 2 left, limit: 1 left, limit+1: 0 left."""
    target_left = 1 - case["value"]
    for _ in range(10 - target_left):
        r = organizer_client.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json")
        assert r.status_code == 201
    assert api.available(organizer_client, team_quota) == target_left

    resp = organizer_client.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json")
    if case["expected"] == "accept":
        assert resp.status_code == 201, resp.content
        assert api.available(organizer_client, team_quota) == target_left - 1
    else:
        assert resp.status_code == 400
        assert "not enough quota" in json.dumps(resp.json()).lower()
        assert api.available(organizer_client, team_quota) == 0


# ==========================================================================
# Rule 2: item must be purchasable (active AND assigned to a quota)
# ==========================================================================
@pytest.mark.django_db
def test_rule2_inactive_item_rejected(api, organizer_client, team_item, team_quota):
    with scopes_disabled():
        team_item.active = False
        team_item.save()
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json")
    assert resp.status_code == 400
    assert "not active" in json.dumps(resp.json())
    assert api.order_count() == 0
    assert api.available(organizer_client, team_quota) == 10


@pytest.mark.django_db
def test_rule2_item_without_quota_rejected(api, organizer_client, team_item, team_quota):
    with scopes_disabled():
        team_quota.items.remove(team_item)
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json")
    assert resp.status_code == 400
    assert "not assigned to a quota" in json.dumps(resp.json())
    assert api.order_count() == 0


# ==========================================================================
# Rule 3: order state machine
#   n = pending, p = paid, e = expired, c = canceled
# ==========================================================================
def _order_in_state(api, client, state):
    code = _place(api, client)
    path = {"n": [], "p": ["mark_paid"], "e": ["mark_expired"], "c": ["mark_canceled"]}[state]
    for action in path:
        r = client.post(api.orders(code, action), {"send_email": False}, format="json")
        assert r.status_code == 200, r.content
    assert _status(api, client, code) == state
    return code


ALLOWED = [
    # (from, action, to)
    ("n", "mark_paid", "p"),
    ("n", "mark_canceled", "c"),
    ("n", "mark_expired", "e"),
    ("p", "mark_pending", "n"),
    ("p", "mark_canceled", "c"),
    ("p", "mark_refunded", "c"),
    ("e", "mark_paid", "p"),
    ("e", "mark_canceled", "c"),
    ("c", "reactivate", "n"),
]

DISALLOWED = [
    # at least one per state; the error text comes from views/order.py
    ("n", "mark_refunded", "The order is not paid."),
    ("n", "mark_pending", "The order is not paid."),
    ("n", "reactivate", "The order is not allowed to be reactivated."),
    ("p", "mark_paid", "The order is not pending or expired."),
    ("p", "mark_expired", "The order is not pending."),
    ("p", "reactivate", "The order is not allowed to be reactivated."),
    ("e", "mark_refunded", "The order is not paid."),
    ("e", "mark_expired", "The order is not pending."),
    ("c", "mark_paid", "The order is not pending or expired."),
    ("c", "mark_canceled", "The order is not allowed to be canceled."),
    ("c", "mark_refunded", "The order is not paid."),
]


@pytest.mark.django_db
@pytest.mark.parametrize("frm,action,to", ALLOWED, ids=[f"{a}:{b}->{c}" for a, b, c in ALLOWED])
def test_rule3_allowed_transition(frm, action, to, api, organizer_client, team_quota):
    code = _order_in_state(api, organizer_client, frm)
    resp = organizer_client.post(api.orders(code, action), {"send_email": False}, format="json")
    assert resp.status_code == 200, resp.content
    assert resp.data["status"] == to
    assert _status(api, organizer_client, code) == to
    # shared record: only pending and paid orders hold a seat
    expected_left = 10 if to in ("c", "e") else 9
    assert api.available(organizer_client, team_quota) == expected_left


@pytest.mark.django_db
@pytest.mark.parametrize("frm,action,message", DISALLOWED, ids=[f"{a}:{b}" for a, b, _ in DISALLOWED])
def test_rule3_disallowed_transition(frm, action, message, api, organizer_client, team_quota):
    code = _order_in_state(api, organizer_client, frm)
    available_before = api.available(organizer_client, team_quota)
    resp = organizer_client.post(api.orders(code, action), {"send_email": False}, format="json")
    assert resp.status_code == 400
    assert resp.json() == {"detail": message}
    assert _status(api, organizer_client, code) == frm, "state changed on a rejected transition"
    assert api.available(organizer_client, team_quota) == available_before


@pytest.mark.django_db
def test_rule3_paying_canceled_order_after_quota_sold_out_is_refused(api, organizer_client, team_quota):
    """Reactivating a canceled order must re-check capacity (state rule + boundary rule together)."""
    code = _order_in_state(api, organizer_client, "c")
    _place(api, organizer_client, 10)                          # sell the quota out
    assert api.available(organizer_client, team_quota) == 0
    resp = organizer_client.post(api.orders(code, "reactivate"), {}, format="json")
    assert resp.status_code == 400
    assert _status(api, organizer_client, code) == "c"
    assert api.available(organizer_client, team_quota) == 0


# ==========================================================================
# Repeated requests must not create duplicates
# ==========================================================================
@pytest.mark.django_db
def test_repeat_with_same_order_code_is_rejected(api, organizer_client, team_quota):
    first = organizer_client.post(api.orders(), api.order_payload(1, code="SQEDUP1"), format="json")
    second = organizer_client.post(api.orders(), api.order_payload(1, code="SQEDUP1"), format="json")
    assert first.status_code == 201
    assert second.status_code == 400
    assert "code" in second.json()
    assert api.order_count() == 1
    assert api.available(organizer_client, team_quota) == 9


@pytest.mark.django_db(transaction=True)
def test_repeat_with_same_idempotency_key_returns_first_response(api, organizer_client, team_quota):
    headers = {"HTTP_X_IDEMPOTENCY_KEY": "sqe-order-0001"}
    first = organizer_client.post(api.orders(), api.order_payload(1), format="json", **headers)
    second = organizer_client.post(api.orders(), api.order_payload(1), format="json", **headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["code"] == second.json()["code"]
    assert api.order_count() == 1
    assert api.available(organizer_client, team_quota) == 9


@pytest.mark.django_db
def test_repeat_mark_paid_creates_one_payment(api, organizer_client):
    code = _place(api, organizer_client)
    first = organizer_client.post(api.orders(code, "mark_paid"), {"send_email": False}, format="json")
    second = organizer_client.post(api.orders(code, "mark_paid"), {"send_email": False}, format="json")
    assert first.status_code == 200
    assert second.status_code == 400
    with scopes_disabled():
        order = Order.objects.get(code=code)
        assert order.payments.filter(state=OrderPayment.PAYMENT_STATE_CONFIRMED).count() == 1


@pytest.mark.django_db
def test_repeat_without_idempotency_key_creates_second_order(api, organizer_client, team_quota):
    """
    Characterisation of weakness W-03 (endpoint_weaknesses.md): without an
    explicit key or code, a client retry after a lost response places a
    second order and consumes a second seat.
    """
    organizer_client.post(api.orders(), api.order_payload(1), format="json")
    organizer_client.post(api.orders(), api.order_payload(1), format="json")
    assert api.order_count() == 2
    assert api.available(organizer_client, team_quota) == 8


# ==========================================================================
# Authorisation (two roles + anonymous)
# ==========================================================================
@pytest.mark.django_db
def test_auth_readonly_can_read_orders(api, organizer_client, readonly_client):
    code = _place(api, organizer_client)
    assert readonly_client.get(api.orders(code)).status_code == 200


@pytest.mark.django_db
def test_auth_readonly_cannot_create_order(api, readonly_client, team_quota):
    resp = readonly_client.post(api.orders(), api.order_payload(1), format="json")
    assert resp.status_code == 403
    assert api.order_count() == 0
    assert api.db_available(team_quota) == 10


@pytest.mark.django_db
def test_auth_readonly_cannot_change_quota(api, readonly_client, team_quota):
    resp = readonly_client.patch(api.quotas(team_quota.pk), {"size": 1000}, format="json")
    assert resp.status_code == 403
    with scopes_disabled():
        team_quota.refresh_from_db()
    assert team_quota.size == 10


@pytest.mark.django_db
def test_auth_readonly_cannot_change_order_state(api, organizer_client, readonly_client):
    code = _place(api, organizer_client)
    resp = readonly_client.post(api.orders(code, "mark_paid"), {}, format="json")
    assert resp.status_code == 403
    assert _status(api, organizer_client, code) == "n"


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", [("get", "quotas"), ("post", "orders"), ("post", "items")])
def test_auth_anonymous_is_refused(method, path, api, anon_client):
    url = api.base + path + "/"
    resp = getattr(anon_client, method)(url, {}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_unknown_order_code_is_404(api, organizer_client):
    assert organizer_client.get(api.orders("ZZZZZ")).status_code == 404
    assert organizer_client.post(api.orders("ZZZZZ", "mark_paid"), {}, format="json").status_code == 404


# ==========================================================================
# Rule 2 (remaining conditions) and per-order limits through the order API.
# These assert the behaviour the presale shop enforces; where the API does
# not, the test is marked xfail(strict) with its weakness id.
# ==========================================================================
def _set_item(item, **fields):
    with scopes_disabled():
        for k, v in fields.items():
            setattr(item, k, v)
        item.save()


W07 = "W-07: order API does not check the item's sale window (available_from/available_until)"
W08 = "W-08: order API does not check min_per_order / max_per_order"


@pytest.mark.xfail(strict=True, reason=W07)
@pytest.mark.django_db
def test_rule2_item_sale_ended_rejected(api, organizer_client, team_item, team_quota):
    _set_item(team_item, available_until=now() - timedelta(minutes=1))
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json")
    assert resp.status_code == 400
    assert api.available(organizer_client, team_quota) == 10


@pytest.mark.xfail(strict=True, reason=W07)
@pytest.mark.django_db
def test_rule2_item_sale_not_started_rejected(api, organizer_client, team_item, team_quota):
    _set_item(team_item, available_from=now() + timedelta(days=1))
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json")
    assert resp.status_code == 400
    assert api.available(organizer_client, team_quota) == 10


@pytest.mark.django_db
@pytest.mark.parametrize("n,expected", [
    (2, 201), (3, 201), pytest.param(4, 400, marks=pytest.mark.xfail(strict=True, reason=W08)),
], ids=["max-1", "max", "max+1"])
def test_rule1_max_per_order_bva(n, expected, api, organizer_client, team_item, team_quota):
    _set_item(team_item, max_per_order=3)
    resp = organizer_client.post(api.orders(), api.order_payload(n), format="json")
    assert resp.status_code == expected, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize("n,expected", [
    pytest.param(1, 400, marks=pytest.mark.xfail(strict=True, reason=W08)), (2, 201), (3, 201),
], ids=["min-1", "min", "min+1"])
def test_rule1_min_per_order_bva(n, expected, api, organizer_client, team_item, team_quota):
    _set_item(team_item, min_per_order=2)
    resp = organizer_client.post(api.orders(), api.order_payload(n), format="json")
    assert resp.status_code == expected, resp.content


@pytest.mark.xfail(strict=True, reason="W-06: ?with_availability=true ignored on quota detail")
@pytest.mark.django_db
def test_quota_detail_honours_with_availability(api, organizer_client, team_quota):
    """Spec: the flag should work on detail as on list. Observed: only list (W-06)."""
    listed = organizer_client.get(api.quotas() + "?with_availability=true").data["results"][0]
    detail = organizer_client.get(api.quotas(team_quota.pk) + "?with_availability=true").data
    assert listed["available_number"] == 10
    assert "available_number" in detail
