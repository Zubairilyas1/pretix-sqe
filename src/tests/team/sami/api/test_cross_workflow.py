"""
Cross-workflow integration: Workflow 1 writes the shared record (Quota),
Workflow 2 consumes it, and every step reads the record back through the API
after both successes AND rejections.

Invariant checked throughout:
    available_number = size - (pending + paid positions) - (unexpired cart positions)
and a rejected request leaves available_number exactly where it was.
"""
import json

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Order


def _create_quota_via_w1(api, client, size):
    """Workflow 1 through the API: a fresh item and a quota for it."""
    item = client.post(api.items(), {"name": {"en": "Workshop Seat"}, "default_price": "20.00",
                                     "active": True, "admission": True}, format="json")
    assert item.status_code == 201, item.content
    quota = client.post(api.quotas(), {"name": "Workshop", "size": size, "items": [item.data["id"]]},
                        format="json")
    assert quota.status_code == 201, quota.content
    return item.data["id"], quota.data["id"]


def _available(api, client, quota_id):
    return api.availability(client, quota_id)["available_number"]


def _order(api, client, item_id, n):
    return client.post(api.orders(), {
        "email": "buyer@example.org", "locale": "en", "payment_provider": "manual",
        "send_email": False, "positions": [{"item": item_id} for _ in range(n)],
    }, format="json")


@pytest.mark.django_db
def test_w1_capacity_is_consumed_and_released_by_w2(api, organizer_client, team_event):
    # Step 1  W1 creates quota size 5 -> read back 5
    item_id, quota_id = _create_quota_via_w1(api, organizer_client, size=5)
    assert _available(api, organizer_client, quota_id) == 5

    # Step 2  W2 orders 3 -> success -> read back 2
    ok = _order(api, organizer_client, item_id, 3)
    assert ok.status_code == 201, ok.content
    code = ok.data["code"]
    snap = api.availability(organizer_client, quota_id)
    assert (snap["total_size"], snap["pending_orders"], snap["available_number"]) == (5, 3, 2)

    # Step 3  W2 orders 3 more -> rejected -> read back STILL 2 (no partial decrement)
    rejected = _order(api, organizer_client, item_id, 3)
    assert rejected.status_code == 400
    assert "not enough quota" in json.dumps(rejected.json()).lower()
    assert _available(api, organizer_client, quota_id) == 2
    with scopes_disabled():
        assert Order.objects.filter(event=team_event).count() == 1

    # Step 4  W2 reserves 1 cart position -> 1 left; deleting it releases -> 2
    cart = organizer_client.post(api.carts(), {"item": item_id, "price": "20.00"}, format="json")
    assert cart.status_code == 201
    snap = api.availability(organizer_client, quota_id)
    assert (snap["pending_orders"], snap["cart_positions"], snap["available_number"]) == (3, 1, 1)
    assert organizer_client.delete(api.carts(cart.data["id"])).status_code == 204
    assert _available(api, organizer_client, quota_id) == 2

    # Step 5  cancel the order -> all 5 back
    cancel = organizer_client.post(api.orders(code, "mark_canceled"), {"send_email": False}, format="json")
    assert cancel.status_code == 200
    assert _available(api, organizer_client, quota_id) == 5


@pytest.mark.django_db
def test_w1_shrinking_capacity_blocks_w2(api, organizer_client):
    item_id, quota_id = _create_quota_via_w1(api, organizer_client, size=5)
    assert _order(api, organizer_client, item_id, 3).status_code == 201

    # W1 lowers capacity to exactly what is sold -> nothing left
    r = organizer_client.patch(api.quotas(quota_id), {"size": 3}, format="json")
    assert r.status_code == 200
    assert _available(api, organizer_client, quota_id) == 0

    rejected = _order(api, organizer_client, item_id, 1)
    assert rejected.status_code == 400
    assert _available(api, organizer_client, quota_id) == 0

    # W1 raises capacity again -> W2 can buy exactly one more
    organizer_client.patch(api.quotas(quota_id), {"size": 4}, format="json")
    assert _available(api, organizer_client, quota_id) == 1
    assert _order(api, organizer_client, item_id, 1).status_code == 201
    assert _available(api, organizer_client, quota_id) == 0


@pytest.mark.django_db
def test_w1_closing_quota_blocks_w2_even_with_capacity(api, organizer_client):
    item_id, quota_id = _create_quota_via_w1(api, organizer_client, size=5)
    organizer_client.patch(api.quotas(quota_id), {"closed": True}, format="json")
    assert api.availability(organizer_client, quota_id)["available"] is False
    rejected = _order(api, organizer_client, item_id, 1)
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_w2_paid_and_pending_both_hold_capacity(api, organizer_client):
    item_id, quota_id = _create_quota_via_w1(api, organizer_client, size=2)
    pending = _order(api, organizer_client, item_id, 1).data["code"]
    paid = _order(api, organizer_client, item_id, 1).data["code"]
    organizer_client.post(api.orders(paid, "mark_paid"), {"send_email": False}, format="json")
    assert _available(api, organizer_client, quota_id) == 0

    # expiring the pending order releases its seat; the paid one keeps it
    organizer_client.post(api.orders(pending, "mark_expired"), {}, format="json")
    assert _available(api, organizer_client, quota_id) == 1


@pytest.mark.django_db
def test_w2_api_and_db_agree_on_shared_record(api, organizer_client, team_quota):
    """The API read-back equals the model's own computation (no stale cache)."""
    for n in (1, 2, 3):
        _order(api, organizer_client, api.item.pk, n)
        assert api.available(organizer_client, team_quota) == api.db_available(team_quota)
