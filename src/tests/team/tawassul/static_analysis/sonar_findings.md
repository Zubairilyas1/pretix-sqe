# SonarQube Static Analysis: W1/W2 source files

| | |
| :--- | :--- |
| **Date** | 2026-11-26 |
| **Tool** | SonarQube Community Build 26.11 (Docker, local throw-away instance) with `sonar-scanner-cli` |
| **Script** | `sonar_scan.py` |
| **Raw export** | `evidence/sonar_measures.json` |
| **Scope** | the four files that implement W1 and W2: `base/services/cart.py`, `base/services/orders.py`, `base/models/items.py`, `control/views/item.py` |
| **Quality gate** | **Passed** (default "Sonar way" gate) |

## Project measures

| Measure | Value | Rating |
| :--- | :-: | :-: |
| Lines of code | 7 701 | |
| Cyclomatic complexity | 1 965 | |
| Cognitive complexity | 2 941 | |
| Bugs (reliability) | 3 | **C** (reliability rating 3.0) |
| Vulnerabilities | 0 | A |
| Security hotspots | 0 | A |
| Code smells | 5 | A (technical debt 27 min) |
| Duplicated lines | 1.2 % | |
| Coverage | not measured here | coverage is Area 1's deliverable (Zubair) |

The dashboard groups issues by software quality. One issue can affect both reliability and maintainability, so it shows Reliability 7 and Maintainability 5. The export contains **8 distinct issues**.

## Complexity per file

| File | LOC | Cyclomatic | Cognitive | Cognitive per 100 LOC |
| :--- | :-: | :-: | :-: | :-: |
| `base/services/orders.py` | 3 075 | 827 | **1 352** | 44 |
| `base/services/cart.py` | 1 469 | 458 | 860 | **59** |
| `base/models/items.py` | 1 723 | 375 | 415 | 24 |
| `control/views/item.py` | 1 434 | 305 | 314 | 22 |

`cart.py` is the densest file (59 cognitive-complexity points per 100 lines). This is where W2 reserves seats against the shared quota, so it is where defects are most likely. It is also the file with all three bugs.

## Issues, verified against the source

| # | Severity | Type | Rule | Location | Verdict |
| :-: | :-: | :-: | :--- | :--- | :--- |
| 1–3 | Major | Bug | S1656 useless self-assignment | `cart.py:1059, 1060, 1065` | **Real defect: A3-D06** (see below) |
| 4 | Critical | Code smell | S8510 loop variable shadows outer `k` | `cart.py:1410` | Not a bug: the outer `k` belongs to a generator expression, which has its own scope in Python 3. Readability only. |
| 5 | Blocker | Code smell | S1845 field name clashes with a constant | `items.py:128` (`cross_selling_condition` vs `CROSS_SELLING_CONDITION…`) | Naming only; Django uses this pattern for choice constants. Low risk. |
| 6–8 | Major | Code smell | S8500 missing comparison methods | `items.py:75, 1112, 1578` | Classes define `__lt__` without the others. Sorting works; `>`/`<=` comparisons would fail. Suggest `functools.total_ordering`. |

### A3-D06: add-on price correction in the cart does nothing (`cart.py:1056-1066`)

```python
# Fix positions with wrong price (TODO: happens out-of-cartmanager-transaction and therefore a little hacky)
for ca in current_addons[cp][a['item'], a['variation']]:
    if ca.listed_price != listed_price:
        ca.listed_price = ca.listed_price                    # assigns the OLD value back
        ca.price_after_voucher = ca.price_after_voucher      # same
        ca.save(update_fields=['listed_price', 'price_after_voucher'])
    if ca.custom_price_input != custom_price:
        ca.custom_price_input = custom_price
        ca.custom_price_input_is_net = self.event.settings.display_net_prices
        ca.price_after_voucher = ca.price_after_voucher      # same
        ca.save(update_fields=['custom_price_input', 'custom_price_input'])   # field listed twice;
                                                             # custom_price_input_is_net is never saved
```

- **What is wrong:** the block is meant to correct add-on cart positions whose price changed, but both assignments write the old value back. The intended code was clearly `ca.listed_price = listed_price`. In the second branch, `custom_price_input_is_net` is changed in memory but never saved, because `update_fields` lists `custom_price_input` twice.
- **Effect:** an add-on already in a cart keeps its stale listed price, and the net or gross flag of a custom price is lost. pretix recalculates prices when the order is created, which probably limits the money impact. The cart display and any logic that reads `listed_price` before checkout still see the wrong value.
- **Found by:** static analysis only. No test reproduces it yet; a white-box test through `CartManager` with an add-on whose price changes would confirm it (suggested to Area 1).
- **Severity:** Major (logic error), medium likelihood (needs add-ons and a price change during an open cart).
- **Fix:** assign `listed_price` and the recomputed price, and use `update_fields=['custom_price_input', 'custom_price_input_is_net', 'price_after_voucher']`.

## How to reproduce
```bash
cd src
../.venv/Scripts/python tests/team/tawassul/static_analysis/sonar_scan.py          # starts SonarQube, scans, exports
../.venv/Scripts/python tests/team/tawassul/static_analysis/sonar_scan.py --export-only
```
SonarQube's first start takes 5–10 minutes on a laptop. The script reuses a running instance.
