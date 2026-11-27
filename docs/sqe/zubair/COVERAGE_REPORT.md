# White-box coverage report (Area 1, Zubair)

## Scope: server-side business logic of the two workflows
| Rule | Code | Why it is the business logic |
| :--- | :--- | :--- |
| BR-1 capacity, BR-4 cart reservation | `pretix/base/services/quotas.py` - whole module (`QuotaAvailability`, `grouper`) | Computes the availability of the shared `Quota` record that W1 writes and W2 consumes. **Critical module.** |
| BR-2 purchasability | `Item.is_available`, `Item.is_available_by_time` (`models/items.py`) | Decides whether a product may be sold now |
| BR-3 order payment / state | `Order._can_be_paid` (`models/orders.py`) | Decides whether an order may move to PAID |

The rest of `items.py` / `orders.py` (model fields, admin helpers, invoices, e-mails) is not business logic of the two
workflows and is outside the 100 % target; it is why the per-file totals of those two files are below 100 %.

## Result (2026-11-27, `docs/sqe/zubair/evidence/`)
| Measure | Value |
| :--- | :--- |
| Tests in `src/tests/team/zubair/` | **218 passed**, 0 failed, 0 skipped (`area1-junit.xml`) |
| `quotas.py` statements | **239 / 239 = 100 %** |
| `quotas.py` branches | **143 / 144** - the missing one is infeasible (below) |
| `Item.is_available`, `Item.is_available_by_time`, `Order._can_be_paid` | **100 % statements, 100 % branches** |
| Coverage gate (`coverage_gate.py`) | **PASSED**, 15 scoped functions checked (`coverage_gate_output.txt`) |
| Raw output | `pytest_coverage_output.txt`, `coverage-area1.json`, HTML: `htmlcov_quotas/index.html` |

## Justified uncovered branch
`quotas.py` 361 -> 363:
```python
353  ... OrderPosition.objects.filter(order__status__in=[Order.STATUS_PAID, Order.STATUS_PENDING], ...)
358  if line['order__status'] == Order.STATUS_PAID:
...
361  elif line['order__status'] == Order.STATUS_PENDING:   # False branch 361->363 never taken
```
The query (L304-305) only returns PAID or PENDING lines, so whenever L361 is reached the status is PENDING and the
`elif` cannot be False. No input can produce that branch without changing the query; it is a defensive `elif`.
The gate allows exactly this branch and nothing else.

## How the target was reached
| Step | Coverage of `quotas.py` (statements / branches, measured) |
| :--- | :--- |
| Suite of 25 Nov (42 tests) | 61 % combined statement+branch (73 statements and 31 branch parts missing) |
| + `test_quota_availability_whitebox.py` (70 tests) | 100 % / 143 of 144 |
| + MCC, state transitions, mutation killers | unchanged (these target conditions and mutants, not lines) |

Techniques used for paths that need special conditions (no pretix code was modified):
| Path | How it is reached |
| :--- | :--- |
| Redis cache read/write, write lock, stale entries (L135-159, L175-212) | `fakeredis` and a replaced module-level `settings` object |
| PostgreSQL `GREATEST` branch (L377-378) | ENGINE string switched in the module's `settings`; SQL function `GREATEST` registered in SQLite |
| REPEATABLE READ guard (L126) | `connection.tx_in_repeatable_read` set by `monkeypatch` |
| Plugin signal receivers (L168-170) | `quota_availability.send` patched (test double) |
| `inconclusive quota` (L295) | negative size set on the in-memory object only (the DB forbids it) |
| Release after exit (L316-345, L363) | real check-in list with entry and exit scans |
| Subevent mismatch, `None in subevents` False | event series with two dates |

## Re-run
```bash
cd src
../.venv/bin/python -m pytest tests/team/zubair --cov=pretix.base.services.quotas --cov=pretix.base.models.orders \
    --cov=pretix.base.models.items --cov-branch --cov-report=json:coverage-area1.json
../.venv/bin/python tests/team/zubair/coverage_gate.py coverage-area1.json
```
