"""
API tests driven by the generator output (EP classes + 3-point BVA).

Every case in generator/test_data.json for the five write operations becomes
one test. Each test sends the spec's valid baseline payload with exactly ONE
field changed, then checks:

  accept -> 2xx, and the stored value is read back unchanged (for scalar fields)
  reject -> 400, the error body names the offending field, and nothing was
            written (record count / stored value unchanged)

Cases whose limit depends on runtime data (value_kind "relative_to_runtime",
Business Rule 1) are tested in test_negative_rules.py and
test_cross_workflow.py, because they need a quota in a known state.

Where pretix behaves differently from the spec, the case is marked
xfail(strict=True) with the defect id from endpoint_weaknesses.md. Strict
means the suite turns red if the behaviour ever changes, so the defect list
stays accurate.
"""
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import CartPosition, Item, Order, Quota

from .conftest import apply_case

# SQE_TEST_DATA lets the regeneration demo run the same tests on data generated
# from a changed spec, to prove the predicted effect.
DATA_PATH = Path(os.environ.get("SQE_TEST_DATA") or
                 Path(__file__).resolve().parent.parent / "generator" / "test_data.json")
DATA = json.loads(DATA_PATH.read_text("utf-8"))

# Known deviations between spec (expected behaviour) and pretix (observed).
# Filled from test runs; each id is described in endpoint_weaknesses.md.
W01 = "W-01: negative item price accepted (no lower bound on Item.default_price)"
W02 = "W-02: negative cart position price accepted (no lower bound on CartPosition price)"
W04 = "W-04: item name not validated (empty / missing default locale / longer than 255)"
W05 = "W-05: quota size above the 32-bit integer range accepted (no max_value on Quota.size)"
W09 = "W-09: negative order position price accepted by POST orders/ (no lower bound on position price)"
W11 = "W-11: attendee_name longer than 255 accepted (OrderPosition.attendee_name_cached is max_length=255)"
W12 = "W-12: order action endpoints do not validate their body; send_email is used by truthiness (api/views/order.py:397)"
KNOWN_DEVIATIONS = {
    "createItem.default_price.BVA.min-1": W01,
    "createItem.default_price.EP.below_min": W01,
    "createCartPosition.price.BVA.min-1": W02,
    "createCartPosition.price.EP.below_min": W02,
    "createItem.name.en.BVA.len_min-1": W04,
    "createItem.name.en.EP.missing": W04,
    "createItem.name.en.BVA.len_max+1": W04,
    "createItem.name.en.EP.too_long": W04,
    "createQuota.size.BVA.max+1": W05,
    "createQuota.size.EP.above_max": W05,
    "patchQuota.size.BVA.max+1": W05,
    "patchQuota.size.EP.above_max": W05,
    "createOrder.positions[].price.BVA.min-1": W09,
    "createOrder.positions[].price.EP.below_min": W09,
    "createOrder.positions[].attendee_name.BVA.len_max+1": W11,
    "createOrder.positions[].attendee_name.EP.too_long": W11,
    "markOrderPaid.send_email.EP.null": W12,
    "markOrderPaid.send_email.EP.wrong_type": W12,
    "markOrderCanceled.send_email.EP.null": W12,
    "markOrderCanceled.send_email.EP.wrong_type": W12,
}


def _cases(operation):
    out = []
    for c in DATA["cases"]:
        if c["operation"] != operation or c["value_kind"] == "relative_to_runtime" or "location" in c:
            continue  # runtime-relative cases: rule tests; parameter cases: test_api_parameters.py
        marks = []
        if c["id"] in KNOWN_DEVIATIONS:
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_DEVIATIONS[c["id"]]))
        out.append(pytest.param(c, id=c["id"], marks=marks))
    return out


def _model_count(model, event):
    with scopes_disabled():
        return model.objects.filter(event=event).count()


def _assert_reject(resp, case):
    assert resp.status_code == 400, (
        f"{case['id']}: expected 400 for value {case['value']!r} ({case['note']}), "
        f"got {resp.status_code}: {resp.content[:300]!r}"
    )
    top_field = case["field"].split(".")[0].replace("[]", "")
    body = resp.json()
    assert top_field in body, f"{case['id']}: error body does not name field {top_field!r}: {body}"


def _assert_stored(stored, case):
    """Accepted scalar values must be stored exactly as sent."""
    if case["value_kind"] != "value" or case["value"] is None or isinstance(case["value"], (dict, list)):
        return
    sent = case["value"]
    if isinstance(sent, str) and isinstance(stored, (Decimal, str)):
        try:
            assert Decimal(str(stored)) == Decimal(sent)
            return
        except ArithmeticError:
            pass
    assert str(stored) == str(sent), f"{case['id']}: stored {stored!r} != sent {sent!r}"


# --------------------------------------------------------------------------
# Workflow 1: create item
# --------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("createItem"))
def test_create_item(case, api, organizer_client, team_event):
    payload = api.fill(apply_case(DATA["baselines"]["createItem"], case))
    before = _model_count(Item, team_event)
    resp = organizer_client.post(api.items(), payload, format="json")

    if case["expected"] == "accept":
        assert resp.status_code == 201, f"{case['id']}: {resp.content[:300]!r}"
        with scopes_disabled():
            item = Item.objects.get(pk=resp.data["id"])
        field = case["field"]
        stored = str(item.name.localize("en")) if field == "name.en" else getattr(item, field, None)
        _assert_stored(stored, case)
    else:
        _assert_reject(resp, case)
        assert _model_count(Item, team_event) == before


# --------------------------------------------------------------------------
# Workflow 1: create quota (writes the shared record)
# --------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("createQuota"))
def test_create_quota(case, api, organizer_client, team_event):
    payload = api.fill(apply_case(DATA["baselines"]["createQuota"], case))
    before = _model_count(Quota, team_event)
    resp = organizer_client.post(api.quotas(), payload, format="json")

    if case["expected"] == "accept":
        assert resp.status_code == 201, f"{case['id']}: {resp.content[:300]!r}"
        with scopes_disabled():
            quota = Quota.objects.get(pk=resp.data["id"])
        _assert_stored(getattr(quota, case["field"], None), case)
    else:
        _assert_reject(resp, case)
        assert _model_count(Quota, team_event) == before


# --------------------------------------------------------------------------
# Workflow 1: patch quota size
# --------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("patchQuota"))
def test_patch_quota(case, api, organizer_client, team_quota):
    payload = api.fill(apply_case(DATA["baselines"]["patchQuota"], case))
    resp = organizer_client.patch(api.quotas(team_quota.pk), payload, format="json")
    with scopes_disabled():
        team_quota.refresh_from_db()

    if case["expected"] == "accept":
        assert resp.status_code == 200, f"{case['id']}: {resp.content[:300]!r}"
        _assert_stored(getattr(team_quota, case["field"], None), case)
    else:
        _assert_reject(resp, case)
        assert team_quota.size == 10, "rejected PATCH must not change the stored size"


# --------------------------------------------------------------------------
# Workflow 2: cart position (reserves quota)
# --------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("createCartPosition"))
def test_create_cart_position(case, api, organizer_client, team_event, team_quota):
    payload = api.fill(apply_case(DATA["baselines"]["createCartPosition"], case))
    before = _model_count(CartPosition, team_event)
    resp = organizer_client.post(api.carts(), payload, format="json")

    if case["expected"] == "accept":
        assert resp.status_code == 201, f"{case['id']}: {resp.content[:300]!r}"
        with scopes_disabled():
            cp = CartPosition.objects.get(pk=resp.data["id"])
        _assert_stored(getattr(cp, case["field"], None), case)
    else:
        _assert_reject(resp, case)
        assert _model_count(CartPosition, team_event) == before


# --------------------------------------------------------------------------
# Workflow 2: create order (consumes quota)
# --------------------------------------------------------------------------
@pytest.fixture
def unlimited_quota(team_quota):
    """Order field tests must not be limited by capacity (that is Rule 1, tested elsewhere)."""
    with scopes_disabled():
        team_quota.size = None
        team_quota.save()
    return team_quota


@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("createOrder"))
def test_create_order(case, api, organizer_client, team_event, unlimited_quota):
    payload = api.fill(apply_case(DATA["baselines"]["createOrder"], case))
    before = _model_count(Order, team_event)
    resp = organizer_client.post(api.orders(), payload, format="json")

    if case["expected"] == "accept":
        assert resp.status_code == 201, f"{case['id']}: {resp.content[:300]!r}"
        with scopes_disabled():
            order = Order.objects.get(event=team_event, code=resp.data["code"])
            if case["value_kind"] == "array_length":
                assert order.positions.count() == case["value"]
            elif case["field"] in ("code", "email", "status", "locale", "testmode"):
                _assert_stored(getattr(order, case["field"]), case)
            elif case["field"].startswith("positions[]."):
                pos = order.positions.first()
                sub = case["field"].split(".", 1)[1]
                if sub == "item":
                    assert pos.item_id == api.item.pk
                elif sub == "attendee_name" and case["value"] is not None:
                    assert pos.attendee_name == case["value"]
                elif sub == "price" and case["value"] is not None:
                    _assert_stored(pos.price, case)
    else:
        _assert_reject(resp, case)
        assert _model_count(Order, team_event) == before


# --------------------------------------------------------------------------
# Workflow 2: order state actions with a body (mark_paid, mark_canceled)
# --------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("case", _cases("markOrderPaid") + _cases("markOrderCanceled"))
def test_order_action_body(case, api, organizer_client, team_event, team_quota):
    code = organizer_client.post(api.orders(), api.order_payload(1), format="json").data["code"]
    action = {"markOrderPaid": "mark_paid", "markOrderCanceled": "mark_canceled"}[case["operation"]]
    target = {"markOrderPaid": Order.STATUS_PAID, "markOrderCanceled": Order.STATUS_CANCELED}[case["operation"]]
    payload = apply_case(DATA["baselines"][case["operation"]], case)
    resp = organizer_client.post(api.orders(code, action), payload, format="json")
    with scopes_disabled():
        status = Order.objects.get(event=team_event, code=code).status
    if case["expected"] == "accept":
        assert resp.status_code == 200, f"{case['id']}: {resp.content[:300]!r}"
        assert status == target
    else:
        _assert_reject(resp, case)
        assert status == Order.STATUS_PENDING, "rejected action must not change the order state"
