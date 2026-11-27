"""
Unit tests for the EP/BVA test data generator (no database needed).

They prove the generator derives values from the spec rather than from
hard-coded numbers: every test builds a tiny spec, runs the generator and
checks the produced values. The last tests run it on the real spec.
"""
import json
from pathlib import Path

import pytest
from tests.team.sami.generator import generate_test_data as gen

REAL_SPEC = Path(gen.DEFAULT_SPEC)


def _mini_spec(props, required=(), example=None, extra=None):
    schema = {"type": "object", "properties": props, "required": list(required),
              "example": example or {}}
    schema.update(extra or {})
    return {
        "openapi": "3.0.3",
        "info": {"title": "t", "version": "1"},
        "paths": {"/x/": {"post": {
            "operationId": "op",
            "requestBody": {"content": {"application/json": {"schema": schema}}},
            "responses": {"200": {"description": "ok"}},
        }}},
    }


def _by_class(cases, field):
    return {c["class"]: c for c in cases if c["field"] == field}


def test_integer_three_point_bva_on_both_bounds():
    spec = _mini_spec({"qty": {"type": "integer", "minimum": 1, "maximum": 10}})
    c = _by_class(gen.generate(spec)["cases"], "qty")
    assert [c[k]["value"] for k in ("min-1", "min", "min+1")] == [0, 1, 2]
    assert [c[k]["value"] for k in ("max-1", "max", "max+1")] == [9, 10, 11]
    assert [c[k]["expected"] for k in ("min-1", "min", "min+1", "max-1", "max", "max+1")] == \
        ["reject", "accept", "accept", "accept", "accept", "reject"]


def test_changing_maximum_changes_bva_values():
    """The viva task: change a constraint, regenerate, values follow."""
    spec = _mini_spec({"qty": {"type": "integer", "minimum": 1, "maximum": 4}})
    c = _by_class(gen.generate(spec)["cases"], "qty")
    assert [c[k]["value"] for k in ("max-1", "max", "max+1")] == [3, 4, 5]


def test_decimal_step_comes_from_multiple_of():
    spec = _mini_spec({"price": {"type": "number", "format": "decimal", "minimum": 0,
                                 "maximum": 100, "multipleOf": 0.01}})
    c = _by_class(gen.generate(spec)["cases"], "price")
    assert [c[k]["value"] for k in ("min-1", "min", "min+1")] == ["-0.01", "0.00", "0.01"]
    assert [c[k]["value"] for k in ("max-1", "max", "max+1")] == ["99.99", "100.00", "100.01"]
    assert c["too_many_decimals"]["value"] == "0.011"
    assert c["too_many_decimals"]["expected"] == "reject"


def test_string_length_bva_and_pattern():
    spec = _mini_spec({"code": {"type": "string", "minLength": 5, "maxLength": 16,
                                "pattern": "^[A-H]+$"}})
    c = _by_class(gen.generate(spec)["cases"], "code")
    assert [len(c[k]["value"]) for k in ("len_min-1", "len_min", "len_min+1")] == [4, 5, 6]
    assert [len(c[k]["value"]) for k in ("len_max-1", "len_max", "len_max+1")] == [15, 16, 17]
    assert c["len_min-1"]["expected"] == "reject" and c["len_max+1"]["expected"] == "reject"
    # every generated length value obeys the pattern, so only the length differs
    assert set(c["len_max"]["value"]) <= set("ABCDEFGH")
    assert c["pattern_mismatch"]["expected"] == "reject"
    assert len(c["pattern_mismatch"]["value"]) == 5


def test_required_nullable_enum_and_type_classes():
    spec = _mini_spec(
        {"status": {"type": "string", "enum": ["n", "p"]},
         "size": {"type": "integer", "nullable": True}},
        required=["status"],
    )
    cases = gen.generate(spec)["cases"]
    status = _by_class(cases, "status")
    size = _by_class(cases, "size")
    assert status["missing"]["expected"] == "reject"
    assert status["enum_n"]["expected"] == status["enum_p"]["expected"] == "accept"
    assert status["not_in_enum"]["expected"] == "reject"
    assert status["null"]["expected"] == "reject"
    assert size["null"]["expected"] == "accept"
    assert "missing" not in size
    assert size["wrong_type"]["value"] == "abc"


def test_array_length_bva():
    spec = _mini_spec({"positions": {"type": "array", "minItems": 1, "maxItems": 3,
                                     "items": {"type": "object"}}})
    c = _by_class(gen.generate(spec)["cases"], "positions")
    assert [(c[k]["value"], c[k]["expected"]) for k in ("items_min-1", "items_min", "items_min+1")] == \
        [(0, "reject"), (1, "accept"), (2, "accept")]
    assert [(c[k]["value"], c[k]["expected"]) for k in ("items_max-1", "items_max", "items_max+1")] == \
        [(2, "accept"), (3, "accept"), (4, "reject")]
    assert all(c[k]["value_kind"] == "array_length" for k in c if k.startswith("items_"))


def test_business_limit_relative_bva():
    spec = _mini_spec({}, extra={"x-business-limit": {"quantity-source": "quota.available_number"}})
    c = _by_class(gen.generate(spec)["cases"], "__quantity__")
    assert [(c[k]["value"], c[k]["expected"]) for k in ("limit-1", "limit", "limit+1")] == \
        [(-1, "accept"), (0, "accept"), (1, "reject")]
    # the synthetic quantity field has no JSON type, so no null/wrong_type cases
    assert set(c) == {"limit-1", "limit", "limit+1"}


def test_refs_are_resolved_for_nested_schemas():
    spec = _mini_spec({"pos": {"$ref": "#/components/schemas/P"}})
    spec["components"] = {"schemas": {"P": {"type": "integer", "minimum": 3}}}
    c = _by_class(gen.generate(spec)["cases"], "pos")
    assert c["min"]["value"] == 3


def test_real_spec_output_is_deterministic_and_unique(tmp_path):
    a = gen.build_document(REAL_SPEC)
    b = gen.build_document(REAL_SPEC)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    ids = [c["id"] for c in a["cases"]]
    assert len(ids) == len(set(ids))


def test_committed_test_data_matches_spec():
    """test_data.json must be regenerated whenever the spec changes."""
    committed = json.loads((Path(gen.DEFAULT_OUT)).read_text(encoding="utf-8"))
    fresh = gen.build_document(REAL_SPEC)
    assert committed["meta"]["spec_sha256"] == fresh["meta"]["spec_sha256"], \
        "Spec changed: run generate_test_data.py and commit test_data.json"
    assert committed["cases"] == fresh["cases"]


@pytest.mark.parametrize("op", ["createItem", "createQuota", "patchQuota", "createCartPosition", "createOrder"])
def test_real_spec_covers_every_request_operation(op):
    doc = gen.build_document(REAL_SPEC)
    assert any(c["operation"] == op for c in doc["cases"])
    assert op in doc["baselines"]
