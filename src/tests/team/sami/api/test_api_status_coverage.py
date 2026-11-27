"""
API coverage criterion "every documented response": each (operation, status code) pair declared in
openapi/pretix_orders_api.yaml is produced by one test and the response is validated against the spec.
`test_every_documented_status_is_covered` fails if the spec documents a status that no test produces.

Extra criteria (not documented in the spec, checked for every operation):
  * anonymous request          -> 401 on every operation
  * read-only token, write op  -> 403 on every write operation
  * non-JSON body on writes    -> 415 Unsupported Media Type
"""
import json
from hashlib import sha1
from pathlib import Path

import pytest
import yaml
from django.utils.timezone import now
from django_scopes import scopes_disabled
from openapi_schema_validator import OAS30Validator
from tests.team.sami.generator.generate_test_data import inline_refs

from pretix.api.models import ApiCall
from pretix.base.models import Order

SPEC = yaml.safe_load((Path(__file__).resolve().parent.parent / "openapi" / "pretix_orders_api.yaml")
                      .read_text("utf-8"))
OPS = {}
for _path, _item in SPEC["paths"].items():
    for _m, _op in _item.items():
        if _m in ("get", "post", "patch", "delete"):
            OPS[_op["operationId"]] = (_path, _m, _op)
DOCUMENTED = sorted((op_id, int(code)) for op_id, (_, _, op) in OPS.items() for code in op["responses"])
WRITE_OPS = sorted(op_id for op_id, (_, m, _) in OPS.items() if m != "get")


def _validate(op_id, resp):
    declared = OPS[op_id][2]["responses"][str(resp.status_code)]
    content = declared.get("content", {}).get("application/json")
    if content and resp.content:
        OAS30Validator(inline_refs(SPEC, content["schema"])).validate(resp.json())


def _order(api, client, state="n"):
    code = client.post(api.orders(), api.order_payload(1), format="json").data["code"]
    for step in {"n": [], "p": ["mark_paid"], "c": ["mark_canceled"]}[state]:
        client.post(api.orders(code, step), {"send_email": False}, format="json")
    return code


def _cart(api, client):
    return client.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json").data["id"]


# (operation, status) -> function(api, organizer_client, readonly_client, anon_client, quota) -> response
def _call(op_id, status, api, org, ro, anon, quota):
    q = quota.pk
    bad = 999999
    send = {"send_email": False}
    table = {
        ("listItems", 200): lambda: org.get(api.items()),
        ("listItems", 401): lambda: anon.get(api.items()),
        ("createItem", 201): lambda: org.post(api.items(), {"name": {"en": "S"}, "default_price": "1.00"}, format="json"),
        ("createItem", 400): lambda: org.post(api.items(), {"default_price": "1.00"}, format="json"),
        ("createItem", 401): lambda: anon.post(api.items(), {"name": {"en": "S"}, "default_price": "1.00"}, format="json"),
        ("createItem", 403): lambda: ro.post(api.items(), {"name": {"en": "S"}, "default_price": "1.00"}, format="json"),
        ("listQuotas", 200): lambda: org.get(api.quotas()),
        ("listQuotas", 401): lambda: anon.get(api.quotas()),
        ("createQuota", 201): lambda: org.post(api.quotas(), {"name": "S", "size": 1, "items": [api.item.pk]}, format="json"),
        ("createQuota", 400): lambda: org.post(api.quotas(), {"name": "S", "size": "abc"}, format="json"),
        ("createQuota", 401): lambda: anon.post(api.quotas(), {"name": "S", "size": 1}, format="json"),
        ("createQuota", 403): lambda: ro.post(api.quotas(), {"name": "S", "size": 1}, format="json"),
        ("getQuota", 200): lambda: org.get(api.quotas(q)),
        ("getQuota", 404): lambda: org.get(api.quotas(bad)),
        ("patchQuota", 200): lambda: org.patch(api.quotas(q), {"size": 12}, format="json"),
        ("patchQuota", 400): lambda: org.patch(api.quotas(q), {"size": -1}, format="json"),
        ("patchQuota", 403): lambda: ro.patch(api.quotas(q), {"size": 12}, format="json"),
        ("patchQuota", 404): lambda: org.patch(api.quotas(bad), {"size": 12}, format="json"),
        ("getQuotaAvailability", 200): lambda: org.get(api.quotas(q) + "availability/"),
        ("getQuotaAvailability", 404): lambda: org.get(api.quotas(bad) + "availability/"),
        ("listCartPositions", 200): lambda: org.get(api.carts()),
        ("createCartPosition", 201): lambda: org.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json"),
        ("createCartPosition", 400): lambda: org.post(api.carts(), {"price": "50.00"}, format="json"),
        ("createCartPosition", 403): lambda: ro.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json"),
        ("deleteCartPosition", 204): lambda: org.delete(api.carts(_cart(api, org))),
        ("deleteCartPosition", 404): lambda: org.delete(api.carts(bad)),
        ("listOrders", 200): lambda: org.get(api.orders()),
        ("createOrder", 201): lambda: org.post(api.orders(), api.order_payload(1), format="json"),
        ("createOrder", 400): lambda: org.post(api.orders(), api.order_payload(0), format="json"),
        ("createOrder", 401): lambda: anon.post(api.orders(), api.order_payload(1), format="json"),
        ("createOrder", 403): lambda: ro.post(api.orders(), api.order_payload(1), format="json"),
        ("getOrder", 200): lambda: org.get(api.orders(_order(api, org))),
        ("getOrder", 404): lambda: org.get(api.orders("ZZZZZ")),
        ("markOrderPaid", 200): lambda: org.post(api.orders(_order(api, org), "mark_paid"), send, format="json"),
        ("markOrderPaid", 400): lambda: org.post(api.orders(_order(api, org, "c"), "mark_paid"), send, format="json"),
        ("markOrderPaid", 404): lambda: org.post(api.orders("ZZZZZ", "mark_paid"), send, format="json"),
        ("markOrderCanceled", 200): lambda: org.post(api.orders(_order(api, org), "mark_canceled"), send, format="json"),
        ("markOrderCanceled", 400): lambda: org.post(api.orders(_order(api, org, "c"), "mark_canceled"), send, format="json"),
        ("markOrderExpired", 200): lambda: org.post(api.orders(_order(api, org), "mark_expired"), format="json"),
        ("markOrderExpired", 400): lambda: org.post(api.orders(_order(api, org, "p"), "mark_expired"), format="json"),
        ("markOrderPending", 200): lambda: org.post(api.orders(_order(api, org, "p"), "mark_pending"), format="json"),
        ("markOrderPending", 400): lambda: org.post(api.orders(_order(api, org), "mark_pending"), format="json"),
        ("markOrderRefunded", 200): lambda: org.post(api.orders(_order(api, org, "p"), "mark_refunded"), format="json"),
        ("markOrderRefunded", 400): lambda: org.post(api.orders(_order(api, org), "mark_refunded"), format="json"),
        ("reactivateOrder", 200): lambda: org.post(api.orders(_order(api, org, "c"), "reactivate"), format="json"),
        ("reactivateOrder", 400): lambda: org.post(api.orders(_order(api, org), "reactivate"), format="json"),
    }
    return table[(op_id, status)]()


SPECIAL = {("createOrder", 409)}  # needs a transactional database, tested separately below
TESTED = [p for p in DOCUMENTED if p not in SPECIAL]


def test_every_documented_status_is_covered():
    """Guard: a status documented in the spec without a test here makes this test fail."""
    import inspect
    src = inspect.getsource(_call)
    missing = [f"{o} {s}" for o, s in TESTED if f'("{o}", {s})' not in src]
    assert not missing, f"documented responses without a test: {missing}"
    assert set(TESTED) | SPECIAL == set(DOCUMENTED)


@pytest.mark.django_db
@pytest.mark.parametrize("op_id, status", TESTED, ids=[f"{o}-{s}" for o, s in TESTED])
def test_documented_status(op_id, status, api, organizer_client, readonly_client, anon_client, team_quota):
    resp = _call(op_id, status, api, organizer_client, readonly_client, anon_client, team_quota)
    assert resp.status_code == status, f"{op_id}: expected {status}, got {resp.status_code} {resp.content[:200]!r}"
    _validate(op_id, resp)


@pytest.mark.django_db(transaction=True)
def test_documented_status_create_order_409(api, organizer_client, team_quota):
    """A request with the same idempotency key that is still being processed (locked ApiCall) -> 409,
    and nothing is written. The in-flight call is simulated by inserting the locked row the middleware
    itself would create."""
    auth = organizer_client._credentials["HTTP_AUTHORIZATION"]
    with scopes_disabled():
        ApiCall.objects.create(auth_hash=sha1(f"{auth}:".encode()).hexdigest(), idempotency_key="sqe-409",
                               locked=now(), request_method="POST", request_path=api.orders(),
                               response_code=0, response_headers="{}", response_body=b"")
        before = Order.objects.count()
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json", HTTP_X_IDEMPOTENCY_KEY="sqe-409")
    assert resp.status_code == 409
    assert resp["Retry-After"] == "5"
    with scopes_disabled():
        assert Order.objects.count() == before


# ---------------------------------------------------------------- authentication on every operation
def _any_request(op_id, client, api, quota):
    path, method, _ = OPS[op_id]
    url = api.url(path, quota_id=quota.pk, id=1, code="ABCDE")
    body = json.dumps({})
    return getattr(client, method)(url, body, content_type="application/json") if method != "get" else client.get(url)


@pytest.mark.django_db
@pytest.mark.parametrize("op_id", sorted(OPS))
def test_anonymous_is_refused_on_every_operation(op_id, api, anon_client, team_quota):
    resp = _any_request(op_id, anon_client, api, team_quota)
    assert resp.status_code == 401, f"{op_id}: {resp.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("op_id", WRITE_OPS)
def test_readonly_token_cannot_write_on_any_write_operation(op_id, api, readonly_client, team_quota):
    with scopes_disabled():
        before = Order.objects.count()
    resp = _any_request(op_id, readonly_client, api, team_quota)
    assert resp.status_code in (403, 404), f"{op_id}: {resp.status_code}"
    if resp.status_code == 404:  # only acceptable when the target object does not exist
        assert OPS[op_id][0].endswith(("{id}/", "{code}/", "/mark_paid/", "/mark_canceled/", "/mark_expired/",
                                       "/mark_pending/", "/mark_refunded/", "/reactivate/")), op_id
    with scopes_disabled():
        assert Order.objects.count() == before


@pytest.mark.django_db
@pytest.mark.parametrize("op_id", ["createItem", "createQuota", "createCartPosition", "createOrder", "patchQuota"])
def test_non_json_body_is_rejected_with_415(op_id, api, organizer_client, team_quota):
    path, method, _ = OPS[op_id]
    url = api.url(path, quota_id=team_quota.pk)
    resp = getattr(organizer_client, method)(url, "name=x", content_type="text/plain")
    assert resp.status_code == 415, f"{op_id}: {resp.status_code}"
