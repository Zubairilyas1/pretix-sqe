#!/usr/bin/env python3
"""
Automated test data generator: OpenAPI 3.0 spec -> EP classes + 3-point BVA.

Author: Sami (Member 2), SE3002 SQE project, Area 2.

How it works
------------
1. Load the spec (default: ../openapi/pretix_orders_api.yaml).
2. For every operation with a JSON request body, inline all $refs in the
   request schema and take the schema's `example` as the VALID BASELINE.
3. Walk every property (one level of nesting, e.g. `name.en`) and derive
   test values purely from the constraint keywords in the spec:

     keyword                       -> technique
     ----------------------------- -----------------------------------------
     minimum / maximum (+multipleOf) 3-point BVA: min-s, min, min+s and
                                   max-s, max, max+s  (s = step)
                                   EP: valid, below_min, above_max
     minLength / maxLength         3-point BVA on the length, EP too_short /
                                   too_long
     minItems / maxItems           3-point BVA on the list length
     pattern                       EP pattern_mismatch
     enum                          EP one valid case per value + not_in_enum
     format: email                 EP invalid_format
     multipleOf (decimals)         EP too_many_decimals
     type                          EP wrong_type
     nullable                      EP null (accept if nullable else reject)
     required                      EP missing (reject)
     x-business-limit              BVA relative to a runtime value
                                   (available-1, available, available+1)

4. Each case says what the API SHOULD do (`expected`: accept / reject)
   according to the spec. Tests send baseline + exactly one changed field.

Output is deterministic (sorted, no timestamps) so that a spec change can be
shown as a clean diff of test_data.json.

Usage
-----
    python generate_test_data.py                       # default paths
    python generate_test_data.py --spec my.yaml --out data.json
    python generate_test_data.py --summary             # print BVA table
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE.parent / "openapi" / "pretix_orders_api.yaml"
DEFAULT_OUT = HERE / "test_data.json"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")

ACCEPT = "accept"
REJECT = "reject"

# A value of the "wrong" JSON type for each declared type. Chosen so that a
# lenient parser cannot coerce it (e.g. DRF turns 123 into "123" for strings,
# so strings get an object instead).
WRONG_TYPE = {
    "integer": "abc",
    "number": "abc",
    "string": {"not": "a string"},
    "boolean": "maybe",
    "array": "not-a-list",
    # not a string: pretix i18n fields legitimately accept a plain string
    "object": 12345,
}


# --------------------------------------------------------------------------
# Spec helpers
# --------------------------------------------------------------------------
def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve(spec, node):
    while isinstance(node, dict) and "$ref" in node:
        target = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def inline_refs(spec, node):
    """Copy of `node` with every $ref replaced by its target (recursively)."""
    node = _resolve(spec, node)
    if isinstance(node, dict):
        return {k: inline_refs(spec, v) for k, v in node.items()}
    if isinstance(node, list):
        return [inline_refs(spec, v) for v in node]
    return node


def request_operations(spec):
    """Yield (operation_id, method, path, request_schema) for JSON bodies."""
    for path, item in spec["paths"].items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if not op or "requestBody" not in op:
                continue
            schema = op["requestBody"]["content"]["application/json"]["schema"]
            yield op["operationId"], method.upper(), path, inline_refs(spec, schema)


# --------------------------------------------------------------------------
# Value helpers
# --------------------------------------------------------------------------
def _decimals(schema):
    """Number of decimal places implied by multipleOf (0 for integers)."""
    if schema.get("type") == "integer":
        return 0
    mult = schema.get("multipleOf")
    if mult is None:
        return 0
    return max(0, -Decimal(str(mult)).as_tuple().exponent)


def _step(schema):
    if schema.get("type") == "integer":
        return Decimal(1)
    mult = schema.get("multipleOf")
    return Decimal(str(mult)) if mult is not None else Decimal(1)


def _render_number(schema, value):
    """Integers as int; decimals as fixed-point strings (how pretix sends them)."""
    if schema.get("type") == "integer":
        return int(value)
    return f"{Decimal(value):.{_decimals(schema)}f}"


def _in_range(schema, value):
    lo, hi = schema.get("minimum"), schema.get("maximum")
    if lo is not None and Decimal(str(value)) < Decimal(str(lo)):
        return False
    if hi is not None and Decimal(str(value)) > Decimal(str(hi)):
        return False
    return True


def _filler_char(schema):
    """A character that satisfies the field's pattern when repeated."""
    pattern = schema.get("pattern")
    for ch in "ABCDEFGHJKLMNPQRSTUVWXYZabc123":
        if pattern is None or re.fullmatch(pattern, ch * 5):
            return ch
    raise ValueError(f"No filler char satisfies pattern {pattern!r}")


def _string_of_length(schema, n):
    if n < 0:
        return None
    if schema.get("format") == "email":
        domain = "@example.org"
        local = max(1, n - len(domain))
        return "a" * local + domain
    return _filler_char(schema) * n


def _pattern_mismatch(schema):
    """A value of valid length that violates the pattern."""
    pattern = schema["pattern"]
    length = max(schema.get("minLength", 1), 1)
    for ch in ("I", "O", "!", "a", " ", "#"):
        candidate = _string_of_length(schema, length - 1) + ch if length > 1 else ch
        if not re.fullmatch(pattern, candidate):
            return candidate
    raise ValueError(f"Could not build mismatch for {pattern!r}")


# --------------------------------------------------------------------------
# Case generation
# --------------------------------------------------------------------------
def _case(op_id, method, path, field, technique, label, value, expected, note, kind="value"):
    return {
        "id": f"{op_id}.{field}.{technique}.{label}",
        "operation": op_id,
        "method": method,
        "path": path,
        "field": field,
        "technique": technique,      # EP or BVA
        "class": label,
        "value_kind": kind,          # value | array_length | relative_to_runtime | missing
        "value": value,
        "expected": expected,
        "note": note,
    }


def cases_for_field(op_id, method, path, field, schema, required):
    c = []
    add = lambda *a, **k: c.append(_case(op_id, method, path, field, *a, **k))  # noqa: E731
    ftype = schema.get("type")

    # ---- required / null / type (EP) ----
    if required:
        add("EP", "missing", None, REJECT, "required field omitted", kind="missing")
    if ftype is not None and ftype != "object":
        if schema.get("nullable"):
            add("EP", "null", None, ACCEPT, "nullable field set to null")
        else:
            add("EP", "null", None, REJECT, "non-nullable field set to null")
    if ftype in WRONG_TYPE:
        add("EP", "wrong_type", WRONG_TYPE[ftype], REJECT, f"value is not of type {ftype}")

    # ---- numbers: EP + 3-point BVA ----
    if ftype in ("integer", "number"):
        step = _step(schema)
        lo, hi = schema.get("minimum"), schema.get("maximum")
        if lo is not None:
            lo = Decimal(str(lo))
            for label, v in (("min-1", lo - step), ("min", lo), ("min+1", lo + step)):
                add("BVA", label, _render_number(schema, v),
                    ACCEPT if _in_range(schema, v) else REJECT, f"lower bound {lo}")
            add("EP", "below_min", _render_number(schema, lo - 100 * step), REJECT,
                "representative of the invalid partition below the minimum")
        if hi is not None:
            hi = Decimal(str(hi))
            for label, v in (("max-1", hi - step), ("max", hi), ("max+1", hi + step)):
                add("BVA", label, _render_number(schema, v),
                    ACCEPT if _in_range(schema, v) else REJECT, f"upper bound {hi}")
            add("EP", "above_max", _render_number(schema, hi + 100 * step), REJECT,
                "representative of the invalid partition above the maximum")
        if lo is not None or hi is not None:
            mid = ((lo if lo is not None else hi - 100 * step) + (hi if hi is not None else lo + 100 * step)) / 2
            mid = (mid // step) * step
            add("EP", "valid", _render_number(schema, mid), ACCEPT, "representative of the valid partition")
        if ftype == "number" and _decimals(schema) > 0:
            base = Decimal(str(lo)) if lo is not None else Decimal(0)
            extra = base + step + Decimal(1).scaleb(-(_decimals(schema) + 1))
            add("EP", "too_many_decimals", f"{extra:.{_decimals(schema) + 1}f}", REJECT,
                f"more than {_decimals(schema)} decimal places")

    # ---- strings: EP + 3-point BVA on length ----
    if ftype == "string":
        mn, mx = schema.get("minLength"), schema.get("maxLength")
        if mn is not None:
            for label, n in (("len_min-1", mn - 1), ("len_min", mn), ("len_min+1", mn + 1)):
                if n < 0:
                    continue
                add("BVA", label, _string_of_length(schema, n),
                    ACCEPT if n >= mn and (mx is None or n <= mx) else REJECT, f"minLength {mn}")
            if mn > 1:
                add("EP", "too_short", _string_of_length(schema, 1), REJECT, "shorter than minLength")
        if mx is not None:
            for label, n in (("len_max-1", mx - 1), ("len_max", mx), ("len_max+1", mx + 1)):
                add("BVA", label, _string_of_length(schema, n),
                    ACCEPT if n <= mx and (mn is None or n >= mn) else REJECT, f"maxLength {mx}")
            add("EP", "too_long", _string_of_length(schema, mx + 10), REJECT, "longer than maxLength")
        if "pattern" in schema:
            add("EP", "pattern_mismatch", _pattern_mismatch(schema), REJECT, f"violates pattern {schema['pattern']}")
        if schema.get("format") == "email":
            add("EP", "invalid_format", "not-an-email", REJECT, "not a valid e-mail address")
        if "enum" in schema:
            for v in schema["enum"]:
                add("EP", f"enum_{v}", v, ACCEPT, "allowed enum value")
            add("EP", "not_in_enum", "zz", REJECT, f"not one of {schema['enum']}")

    # ---- booleans ----
    if ftype == "boolean":
        add("EP", "true", True, ACCEPT, "boolean true")
        add("EP", "false", False, ACCEPT, "boolean false")

    # ---- arrays: 3-point BVA on number of items ----
    if ftype == "array":
        mn, mx = schema.get("minItems"), schema.get("maxItems")
        if mn is not None:
            for label, n in (("items_min-1", mn - 1), ("items_min", mn), ("items_min+1", mn + 1)):
                if n >= 0:
                    add("BVA", label, n, ACCEPT if n >= mn else REJECT, f"minItems {mn}", kind="array_length")
        if mx is not None:
            for label, n in (("items_max-1", mx - 1), ("items_max", mx), ("items_max+1", mx + 1)):
                add("BVA", label, n, ACCEPT if n <= mx else REJECT, f"maxItems {mx}", kind="array_length")

    # ---- business limits that depend on runtime data (Rule 1) ----
    if "x-business-limit" in schema:
        src = schema["x-business-limit"]["quantity-source"]
        for label, off in (("limit-1", -1), ("limit", 0), ("limit+1", 1)):
            add("BVA", label, off, ACCEPT if off <= 0 else REJECT,
                f"quantity relative to {src}", kind="relative_to_runtime")
    return c


def generate(spec):
    cases = []
    for op_id, method, path, schema in request_operations(spec):
        required = set(schema.get("required", []))
        for name, prop in schema.get("properties", {}).items():
            if prop.get("type") == "object" and "properties" in prop:
                # one level of nesting, e.g. Item.name.en
                cases += cases_for_field(op_id, method, path, name, {"type": "object"}, name in required)
                for sub, subprop in prop["properties"].items():
                    cases += cases_for_field(op_id, method, path, f"{name}.{sub}", subprop,
                                             sub in set(prop.get("required", [])))
            else:
                cases += cases_for_field(op_id, method, path, name, prop, name in required)
        if "x-business-limit" in schema:
            cases += cases_for_field(op_id, method, path, "__quantity__",
                                     {"x-business-limit": schema["x-business-limit"]}, False)

    baselines = {op_id: copy.deepcopy(schema.get("example", {}))
                 for op_id, _, _, schema in request_operations(spec)}
    cases.sort(key=lambda x: x["id"])
    ids = [x["id"] for x in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate case ids: {sorted(dupes)}")
    return {"baselines": baselines, "cases": cases}


def build_document(spec_path):
    # normalise line endings so a CRLF checkout on Windows hashes the same
    raw = Path(spec_path).read_bytes().replace(b"\r\n", b"\n")
    spec = yaml.safe_load(raw)
    data = generate(spec)
    return {
        "meta": {
            "generator": "tests/team/sami/generator/generate_test_data.py",
            "spec": Path(spec_path).name,
            "spec_version": spec["info"]["version"],
            "spec_sha256": hashlib.sha256(raw).hexdigest(),
            "total_cases": len(data["cases"]),
            "by_technique": {
                t: sum(1 for c in data["cases"] if c["technique"] == t) for t in ("EP", "BVA")
            },
        },
        **data,
    }


def print_summary(doc):
    print(f"Spec {doc['meta']['spec']} v{doc['meta']['spec_version']} "
          f"-> {doc['meta']['total_cases']} cases {doc['meta']['by_technique']}")
    print(f"{'case id':70} {'value':>24}  expected")
    for c in doc["cases"]:
        if c["technique"] == "BVA":
            v = c["value"] if not isinstance(c["value"], str) or len(c["value"]) < 24 else f"<str len {len(c['value'])}>"
            print(f"{c['id']:70} {str(v):>24}  {c['expected']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", action="store_true", help="print the BVA table")
    args = ap.parse_args(argv)

    doc = build_document(args.spec)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {doc['meta']['total_cases']} cases to {args.out}")
    if args.summary:
        print_summary(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
