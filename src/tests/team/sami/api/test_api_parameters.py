"""
EP and 3-point BVA on every PATH, QUERY and HEADER parameter, driven by the generator output
(generator/test_data.json, cases that carry a "location").

For each case the request of the operation is sent with only that parameter changed:
  accept -> the operation's success status (and the documented effect)
  reject -> case["reject_status"] (404 unknown/ill-formed id or code, 403 unknown organizer/event,
            400 invalid header, 200 = invalid query value ignored)
Write operations that are rejected must not change anything (read-back of the shared records).

Integer ids additionally get BVA relative to the largest existing id: max_id-1 and max_id exist
(two objects are created), max_id+1 does not.
"""
import json
import os
from pathlib import Path

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import CartPosition, Order, Quota

DATA_PATH = Path(os.environ.get("SQE_TEST_DATA") or
                 Path(__file__).resolve().parent.parent / "generator" / "test_data.json")
DATA = json.loads(DATA_PATH.read_text("utf-8"))

SUCCESS = {"listItems": 200, "createItem": 201, "listQuotas": 200, "createQuota": 201, "getQuota": 200,
           "patchQuota": 200, "getQuotaAvailability": 200, "listCartPositions": 200, "createCartPosition": 201,
           "deleteCartPosition": 204, "listOrders": 200, "createOrder": 201, "getOrder": 200,
           "markOrderPaid": 200, "markOrderCanceled": 200, "markOrderExpired": 200, "markOrderPending": 200,
           "markOrderRefunded": 200, "reactivateOrder": 200}
ORDER_STATE_FOR = {"markOrderPending": "p", "markOrderRefunded": "p", "reactivateOrder": "c"}
W10 = "W-10: X-Idempotency-Key longer than 190 characters accepted (ApiCall.idempotency_key max_length=190)"
KNOWN_DEVIATIONS = {
    "createOrder.header:X-Idempotency-Key.BVA.len_max+1": W10,
    "createOrder.header:X-Idempotency-Key.EP.too_long": W10,
}


def _params(location, transactional):
    out = []
    for c in DATA["cases"]:
        if c.get("location") != location:
            continue
        if (c["param"] == "X-Idempotency-Key") != transactional:
            continue
        marks = [pytest.mark.xfail(strict=True, reason=KNOWN_DEVIATIONS[c["id"]])] if c["id"] in KNOWN_DEVIATIONS else []
        out.append(pytest.param(c, id=c["id"], marks=marks))
    return out


class Target:
    """Creates the objects an operation needs and resolves placeholders and runtime offsets."""

    def __init__(self, api, client, quota):
        self.api, self.client, self.quota = api, client, quota
        self.values = {"organizer": api.organizer.slug, "event": api.event.slug, "quota": quota.pk}

    def _order(self, state="n"):
        code = self.client.post(self.api.orders(), self.api.order_payload(1), format="json").data["code"]
        for step in {"n": [], "p": ["mark_paid"], "c": ["mark_canceled"]}[state]:
            self.client.post(self.api.orders(code, step), {"send_email": False}, format="json")
        return code

    def prepare(self, case):
        op = case["operation"]
        if "{code}" in case["path"]:
            self.values["order"] = self._order(ORDER_STATE_FOR.get(op, "n"))
        if "{id}" in case["path"]:
            r = self.client.post(self.api.carts(), {"item": self.api.item.pk, "price": "50.00"}, format="json")
            self.values["cartposition"] = r.data["id"]
        if case["value_kind"] == "relative_to_runtime":
            # two existing objects so that max_id-1 exists as well
            if case["param"] == "quota_id":
                with scopes_disabled():
                    second = Quota.objects.create(event=self.api.event, name="second", size=10)
                    second.items.add(self.api.item)
                self.values["quota"] = second.pk
            else:
                second = self.client.post(self.api.carts(), {"item": self.api.item.pk, "price": "50.00"},
                                          format="json").data["id"]
                self.values["cartposition"] = second

    def resolve(self, case):
        v = case["value"]
        kind = case["value_kind"]
        if kind == "relative_to_runtime":
            ref = "quota" if case["param"] == "quota_id" else "cartposition"
            return self.values[ref] + v
        if isinstance(v, str) and v.startswith("{{unknown_"):
            ref = v[len("{{unknown_"):-2]
            return {"organizer": "no-such-organizer", "event": "no-such-event", "order": "ZZZZZ9",
                    "quota": self.quota.pk + 100000, "cartposition": 999999}[ref]
        if isinstance(v, str) and v.startswith("{{"):
            return self.values[v[2:-2]]
        return v

    def url(self, case, value):
        values = {"organizer": self.values["organizer"], "event": self.values["event"],
                  "quota_id": self.values.get("quota"), "id": self.values.get("cartposition"),
                  "code": self.values.get("order")}
        if case["location"] == "path":
            values[case["param"]] = value
        path = case["path"]
        for k, v in values.items():
            path = path.replace("{" + k + "}", str(v))
        return "/api/v1" + path


def _body(op, api):
    return {
        "createItem": {"name": {"en": "P"}, "default_price": "1.00"},
        "createQuota": {"name": "P", "size": 1, "items": [api.item.pk]},
        "patchQuota": {"size": 12},
        "createCartPosition": {"item": api.item.pk, "price": "50.00"},
        "createOrder": api.order_payload(1),
    }.get(op, {"send_email": False})


def _snapshot(api):
    with scopes_disabled():
        return (Order.objects.filter(event=api.event).count(),
                sorted(Order.objects.filter(event=api.event).values_list("code", "status")),
                CartPosition.objects.filter(event=api.event).count(),
                sorted(Quota.objects.filter(event=api.event).values_list("pk", "size")))


def _send(case, api, client, quota, headers=None):
    t = Target(api, client, quota)
    t.prepare(case)
    value = t.resolve(case)
    url = t.url(case, value)
    method = case["method"].lower()
    if case["location"] == "query":
        url += f"?{case['param']}={str(value).lower() if isinstance(value, bool) else value}"
    before = _snapshot(api)
    if method == "get":
        resp = client.get(url, **(headers or {}))
    else:
        resp = getattr(client, method)(url, _body(case["operation"], api), format="json", **(headers or {}))
    return resp, before


@pytest.mark.django_db
@pytest.mark.parametrize("case", _params("path", False))
def test_path_parameter(case, api, organizer_client, team_quota):
    resp, before = _send(case, api, organizer_client, team_quota)
    if case["expected"] == "accept":
        assert resp.status_code == SUCCESS[case["operation"]], f"{case['id']}: {resp.status_code} {resp.content[:200]!r}"
    else:
        assert resp.status_code == case["reject_status"], f"{case['id']}: {resp.status_code} {resp.content[:200]!r}"
        assert _snapshot(api) == before, f"{case['id']}: a rejected request changed data"


@pytest.mark.django_db
@pytest.mark.parametrize("case", _params("query", False))
def test_query_parameter(case, api, organizer_client, team_quota):
    resp, _ = _send(case, api, organizer_client, team_quota)
    assert resp.status_code == (200 if case["expected"] == "accept" else case["reject_status"])
    shown = "available_number" in resp.data["results"][0]
    assert shown is (case["value"] is True), f"{case['id']}: availability fields shown={shown}"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("case", _params("header", True))
def test_header_parameter(case, api, organizer_client, team_quota):
    headers = {"HTTP_X_IDEMPOTENCY_KEY": case["value"]} if case["value"] is not None else {}
    resp, before = _send(case, api, organizer_client, team_quota, headers)
    if case["expected"] == "accept":
        assert resp.status_code == 201
        # the same key again must replay the first response and create nothing new
        if case["value"]:
            again = organizer_client.post(api.orders(), api.order_payload(1), format="json", **headers)
            assert again.status_code == 201 and again.json()["code"] == resp.json()["code"]
            with scopes_disabled():
                assert Order.objects.filter(event=api.event).count() == before[0] + 1
    else:
        assert resp.status_code == case["reject_status"], f"{case['id']}: {resp.status_code}"
        assert _snapshot(api) == before


def test_every_parameter_of_the_spec_has_cases():
    import yaml
    spec = yaml.safe_load((Path(__file__).resolve().parent.parent / "openapi" / "pretix_orders_api.yaml").read_text("utf-8"))
    declared = set()
    for path, item in spec["paths"].items():
        for m, op in item.items():
            if m in ("get", "post", "patch", "delete"):
                for p in item.get("parameters", []) + op.get("parameters", []):
                    p = spec["components"]["parameters"][p["$ref"].split("/")[-1]] if "$ref" in p else p
                    declared.add((op["operationId"], p["in"], p["name"]))
    generated = {(c["operation"], c["location"], c["param"]) for c in DATA["cases"] if "location" in c}
    assert declared == generated
