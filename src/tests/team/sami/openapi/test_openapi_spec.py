"""
Checks that the hand-written OpenAPI spec is a trustworthy test basis:

1. It is a valid OpenAPI 3.0 document.
2. Every operation has a unique operationId (the generator and the coverage
   report refer to operations by this id).
3. Every request-body example (the generator's baseline payload) is valid
   against its own schema, so "vary one field" really produces exactly one
   invalid field.
4. Every path in the spec resolves to a real pretix URL route, so the spec
   cannot drift away from the system under test.
"""
from pathlib import Path

import pytest
import yaml
from django.urls import Resolver404, resolve
from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate

SPEC_PATH = Path(__file__).parent / "pretix_orders_api.yaml"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")


@pytest.fixture(scope="module")
def spec():
    with open(SPEC_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _operations(spec):
    for path, item in spec["paths"].items():
        for method in HTTP_METHODS:
            if method in item:
                yield path, method, item[method]


def _deref(spec, node):
    while "$ref" in node:
        parts = node["$ref"].lstrip("#/").split("/")
        node = spec
        for p in parts:
            node = node[p]
    return node


def _inline_refs(spec, node):
    """Return a copy of a schema with every $ref replaced by its target."""
    if isinstance(node, dict):
        node = _deref(spec, node)
        return {k: _inline_refs(spec, v) for k, v in node.items() if k != "example"}
    if isinstance(node, list):
        return [_inline_refs(spec, v) for v in node]
    return node


def _fill_placeholders(value):
    """Replace "{{...}}" runtime placeholders by a dummy integer id."""
    if isinstance(value, dict):
        return {k: _fill_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill_placeholders(v) for v in value]
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        return 1
    return value


def test_spec_is_valid_openapi_30(spec):
    validate(spec)  # raises on any structural error
    assert spec["openapi"].startswith("3.0")


def test_every_operation_has_unique_operation_id(spec):
    ids = [op.get("operationId") for _, _, op in _operations(spec)]
    assert None not in ids
    assert len(ids) == len(set(ids))


def test_request_examples_are_valid_against_their_schema(spec):
    checked = 0
    for path, method, op in _operations(spec):
        body = op.get("requestBody")
        if not body:
            continue
        schema = _deref(spec, body["content"]["application/json"]["schema"])
        example = schema.get("example")
        assert example is not None, f"{method.upper()} {path}: request schema has no baseline example"
        # Decimal fields are sent as strings; validate them as numbers.
        payload = _fill_placeholders(example)
        for name, prop in schema.get("properties", {}).items():
            if prop.get("format") == "decimal" and isinstance(payload.get(name), str):
                payload[name] = float(payload[name])
        OAS30Validator(_inline_refs(spec, schema)).validate(payload)
        checked += 1
    assert checked >= 6


@pytest.mark.parametrize("path", [
    p for p in yaml.safe_load(open(SPEC_PATH, encoding="utf-8"))["paths"]
])
def test_spec_path_exists_in_pretix_url_conf(path):
    concrete = (
        "/api/v1" + path
        .replace("{organizer}", "sqe-org")
        .replace("{event}", "sqe-conf")
        .replace("{quota_id}", "1")
        .replace("{id}", "1")
        .replace("{code}", "ABCDE")
    )
    try:
        match = resolve(concrete)
    except Resolver404:
        pytest.fail(f"Spec path {path} does not exist in pretix ({concrete})")
    assert match.func is not None
