"""
API coverage: every operation in the spec is called at least once on its
success path, and the response body is validated against the response schema
declared in the spec. A test also fails if the spec gains an operation that
this file does not exercise, so coverage cannot silently drop.
"""
from pathlib import Path

import pytest
import yaml
from openapi_schema_validator import OAS30Validator

from tests.team.sami.generator.generate_test_data import inline_refs

SPEC = yaml.safe_load((Path(__file__).resolve().parent.parent / "openapi" / "pretix_orders_api.yaml")
                      .read_text("utf-8"))

ALL_OPERATIONS = {
    op["operationId"]
    for item in SPEC["paths"].values()
    for m, op in item.items() if m in ("get", "post", "patch", "put", "delete")
}


def _operation(op_id):
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if isinstance(op, dict) and op.get("operationId") == op_id:
                return path, method, op
    raise KeyError(op_id)


def _check(resp, op_id, expected_status):
    assert resp.status_code == expected_status, f"{op_id}: {resp.status_code} {resp.content[:300]!r}"
    _, _, op = _operation(op_id)
    declared = op["responses"][str(expected_status)]
    content = declared.get("content", {}).get("application/json")
    if content:
        OAS30Validator(inline_refs(SPEC, content["schema"])).validate(resp.json())


def _run(op_id, api, c, team_quota, code_factory):
    """Call one operation on its success path; returns (response, expected status)."""
    q = team_quota.pk
    if op_id == "listItems":
        return c.get(api.items()), 200
    if op_id == "createItem":
        return c.post(api.items(), {"name": {"en": "Cov"}, "default_price": "1.00"}, format="json"), 201
    if op_id == "listQuotas":
        return c.get(api.quotas()), 200
    if op_id == "createQuota":
        return c.post(api.quotas(), {"name": "Cov", "size": 1, "items": [api.item.pk]}, format="json"), 201
    if op_id == "getQuota":
        return c.get(api.quotas(q)), 200
    if op_id == "getQuotaAvailability":
        return c.get(api.quotas(q) + "availability/"), 200
    if op_id == "patchQuota":
        return c.patch(api.quotas(q), {"size": 11}, format="json"), 200
    if op_id == "listCartPositions":
        return c.get(api.carts()), 200
    if op_id == "createCartPosition":
        return c.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json"), 201
    if op_id == "deleteCartPosition":
        cp = c.post(api.carts(), {"item": api.item.pk, "price": "50.00"}, format="json").data["id"]
        return c.delete(api.carts(cp)), 204
    if op_id == "listOrders":
        return c.get(api.orders()), 200
    if op_id == "createOrder":
        return c.post(api.orders(), api.order_payload(1), format="json"), 201
    if op_id == "getOrder":
        return c.get(api.orders(code_factory("n"))), 200
    actions = {
        "markOrderPaid": ("n", "mark_paid"), "markOrderCanceled": ("n", "mark_canceled"),
        "markOrderExpired": ("n", "mark_expired"), "markOrderPending": ("p", "mark_pending"),
        "markOrderRefunded": ("p", "mark_refunded"), "reactivateOrder": ("c", "reactivate"),
    }
    state, action = actions[op_id]
    return c.post(api.orders(code_factory(state), action), {"send_email": False}, format="json"), 200


COVERED = sorted([
    "listItems", "createItem", "listQuotas", "createQuota", "getQuota", "getQuotaAvailability", "patchQuota",
    "listCartPositions", "createCartPosition", "deleteCartPosition",
    "listOrders", "createOrder", "getOrder",
    "markOrderPaid", "markOrderCanceled", "markOrderExpired", "markOrderPending",
    "markOrderRefunded", "reactivateOrder",
])


def test_every_spec_operation_is_covered():
    assert set(COVERED) == ALL_OPERATIONS, (
        f"not covered: {ALL_OPERATIONS - set(COVERED)}; unknown: {set(COVERED) - ALL_OPERATIONS}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("op_id", COVERED)
def test_operation_success_path_matches_spec(op_id, api, organizer_client, team_quota):
    def code_in(state):
        code = organizer_client.post(api.orders(), api.order_payload(1), format="json").data["code"]
        steps = {"n": [], "p": ["mark_paid"], "c": ["mark_canceled"]}[state]
        for s in steps:
            organizer_client.post(api.orders(code, s), {"send_email": False}, format="json")
        return code

    resp, expected = _run(op_id, api, organizer_client, team_quota, code_in)
    _check(resp, op_id, expected)
