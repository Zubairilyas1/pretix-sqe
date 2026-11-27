# EP / 3-point BVA test data generator

`generate_test_data.py` reads `../openapi/pretix_orders_api.yaml` and writes
`test_data.json`. The API tests in `../api/` load that file; they never use
hard-coded boundary values.

## Run
```bash
cd pretix-sqe/src
../.venv/Scripts/python tests/team/sami/generator/generate_test_data.py --summary
```
`--summary` prints every BVA case (id, value, expected result).

## What is derived from which spec keyword
| Keyword | Cases |
| :--- | :--- |
| `minimum` / `maximum` | BVA `min-1, min, min+1`, `max-1, max, max+1`; EP `below_min`, `above_max`, `valid` |
| `multipleOf` | step size for BVA (0.01 for prices); EP `too_many_decimals` |
| `minLength` / `maxLength` | BVA on string length; EP `too_short`, `too_long` |
| `minItems` / `maxItems` | BVA on list length (order positions) |
| `pattern`, `format: email`, `enum` | EP `pattern_mismatch`, `invalid_format`, one case per enum value, `not_in_enum` |
| `type`, `nullable`, `required` | EP `wrong_type`, `null`, `missing` |
| `x-business-limit` | BVA relative to runtime availability: `limit-1, limit, limit+1` |

## Changing a constraint (viva task)
1. Edit a constraint in the YAML, e.g. `OrderCreate.code.maxLength: 16 -> 12`.
2. Run the generator again.
3. `git diff test_data.json` shows the BVA triple moving from 15/16/17 to 11/12/13.
4. Run the API tests: the new `len_max` (12) and `len_max-1` cases pass, and the
   new `len_max+1` (13) case **fails**. The spec now says 13 must be rejected,
   but pretix still accepts up to 16. That failure is the expected
   spec-vs-implementation mismatch the exercise is about.

`test_generator.py::test_committed_test_data_matches_spec` fails if the spec
was changed without regenerating, so the data can never be stale.

A recorded run of two constraint changes is in `regeneration_demo/`.
