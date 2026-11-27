# Area 2: API testing and automated test-data generation (Sami)

Endpoints of the two workflows (19 operations): items, quotas (+ availability), cart positions, orders and the
order state actions. Specification: `openapi/pretix_orders_api.yaml` (OpenAPI 3.0.3, written from the serializers
and views at the baseline commit). Run from `src/`: `../.venv/bin/python -m pytest tests/team/sami -q`
-> **490 passed, 30 xfailed (strict)**, 0 failed. Every strict xfail is a tracked weakness (W-01..W-12).

## Generator
`generator/generate_test_data.py` reads the spec and writes `generator/test_data.json` (**322 cases: 234 EP, 88 BVA**;
186 body fields, 129 path, 3 query, 4 header). Derivation rules (only spec keywords are used):

| Spec keyword | Generated classes |
| :--- | :--- |
| `minimum` / `maximum` (+`multipleOf`) | 3-point BVA min-s, min, min+s / max-s, max, max+s; EP valid, below_min, above_max |
| `minLength` / `maxLength` | 3-point BVA on the length; EP too_short / too_long |
| `minItems` / `maxItems` | 3-point BVA on the list length |
| `pattern`, `enum`, `format: email`, decimals | EP pattern_mismatch, one case per enum value + not_in_enum, invalid_format, too_many_decimals |
| `type`, `nullable`, `required` | EP wrong_type, null, missing |
| array of objects | every property of the item object, varied in the first element (`positions[].price`) |
| parameters (path / query / header) | the same keywords, plus `x-runtime-ref` -> EP existing / unknown, and for integer ids BVA relative to the largest existing id; `x-reject-status` = status a rejected value must get |
| `x-business-limit` | BVA relative to runtime availability (available-1, available, available+1) |

Each case changes **exactly one** input of a valid baseline (the schema `example`). `test_generator.py` (15 tests)
checks the rules; `test_committed_test_data_matches_spec` fails if `test_data.json` is not regenerated after a spec change.

**Regeneration demo** (`generator/regeneration_demo/`): changes two constraints (order code maxLength 16 -> 12,
quota size maximum -> 1000), regenerates, lists the 9 changed cases and runs the affected tests
(`run_demo.py --verify`): the predicted failure `createOrder.code.BVA.len_max+1` is observed; C2 maps to the tracked W-05.

## Tests
| File | Technique / criterion | Tests |
| :--- | :--- | :-: |
| `openapi/test_openapi_spec.py` | spec is valid OAS 3.0, every path resolves in pretix's URL conf, examples match schemas | 17 |
| `api/test_api_ep_bva.py` | EP + 3-point BVA on every body field from the generator; read-back of stored value; nothing written on reject | 180 |
| `api/test_api_parameters.py` | EP + BVA on every path, query and header parameter from the generator; nothing written on reject | 137 |
| `api/test_api_status_coverage.py` | every documented (operation, status) pair incl. 409; 401 on all operations; 403 for read-only writes; 415 for non-JSON | 84 |
| `api/test_api_coverage.py` | every operation on its success path, response validated against the spec | 20 |
| `api/test_api_decision_tables.py` | decision tables DT-1 (BR-2: active x window x quota, 8 rules), DT-2 (BR-1 per-order limits) | 12 |
| `api/test_negative_rules.py` | rule rejections, state transitions (9 allowed, 11 disallowed), repeated requests, auth | 50 |
| `api/test_cross_workflow.py` | W1 changes the quota, W2 consumes it; read-back after success and rejection | 5 |

API coverage criteria met: every operation (19/19), every documented status code (47/47), every parameter
(path/query/header) and every body field incl. array items, authentication on every operation, content type.

## Weaknesses
`api/endpoint_weaknesses.md`: W-01..W-12 with evidence, root cause (file and line), impact, fix, severity and the
linked risk (`PR-API-xx` in `shared_management/RISK_REGISTER_5x5.md`). Filed as GitHub Issues (see the defect log).
