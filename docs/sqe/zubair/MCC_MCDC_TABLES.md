# MCC tables and MC/DC pairs (Area 1, Zubair)

Critical module: `src/pretix/base/services/quotas.py` (`QuotaAvailability`), plus the rule functions
`Item.is_available()` (BR-2) and `Order._can_be_paid()` (BR-3). Line numbers refer to the baseline commit.

**Method.** For every decision with two or more conditions, the MCC table lists every combination of
condition values (2^n rows). Each row is one parametrised test in
`src/tests/team/zubair/test_mcc_mcdc.py` whose test id is the row id (for example `test_mcc_q3_close_when_sold_out[Q3-5]`).
MC/DC pairs are then **read from the MCC table**: for each condition we pick two rows that differ only in
that condition and give different outcomes. `test_mcdc_pairs_are_valid` re-checks every pair automatically, so a
wrong pair fails the build.

Python evaluates `and` / `or` lazily, so in some rows a condition is not evaluated (marked "masked"). MCC still
requires the inputs of that row to be produced, which the tests do.

Run: `cd src && python -m pytest tests/team/zubair/test_mcc_mcdc.py -v`

---

## Q1 - REPEATABLE READ guard (L126)
`if not self._allow_repeatable_read and getattr(connection, "tx_in_repeatable_read", False): raise ValueError`

| Row | A: not allow_repeatable_read | B: tx in REPEATABLE READ | Outcome (raise) |
| :-: | :-: | :-: | :-: |
| Q1-1 | T | T | **T** |
| Q1-2 | T | F | F |
| Q1-3 | F | T (masked) | F |
| Q1-4 | F | F (masked) | F |

MC/DC: A -> (Q1-1, Q1-3); B -> (Q1-1, Q1-2).

## Q2 - Cache entry may be used (L151)
`if time.time() - int(data[2]) < 120 or allow_cache_stale:`

| Row | A: entry younger than 120 s | B: allow_cache_stale | Outcome (use cache) |
| :-: | :-: | :-: | :-: |
| Q2-1 | T | T (masked) | T |
| Q2-2 | T | F (masked) | T |
| Q2-3 | F | T | T |
| Q2-4 | F | F | **F** |

MC/DC: A -> (Q2-2, Q2-4); B -> (Q2-3, Q2-4).

## Q3 - Close a sold-out quota automatically (L221)
`if self.results[q][0] <= Quota.AVAILABILITY_ORDERED and q.close_when_sold_out and not q.closed:`

| Row | A: sold out (<= ORDERED) | B: close_when_sold_out | C: not closed | Outcome (close + log) |
| :-: | :-: | :-: | :-: | :-: |
| Q3-1 | T | T | T | **T** |
| Q3-2 | T | T | F | F |
| Q3-3 | T | F | T | F |
| Q3-4 | T | F | F | F |
| Q3-5 | F | T | T | F |
| Q3-6 | F | T | F | F |
| Q3-7 | F | F | T | F |
| Q3-8 | F | F | F | F |

MC/DC: A -> (Q3-1, Q3-5); B -> (Q3-1, Q3-3); C -> (Q3-1, Q3-2). Four tests (n + 1) are sufficient; MCC runs all eight.

## Q4 - Exited attendee frees capacity (L363)
`if q.release_after_exit and line['is_exited']:`

| Row | A: release_after_exit | B: position exited | Outcome (count as exited, not sold) |
| :-: | :-: | :-: | :-: |
| Q4-1 | T | T | **T** |
| Q4-2 | T | F | F |
| Q4-3 | F | T (masked) | F |
| Q4-4 | F | F (masked) | F |

MC/DC: A -> (Q4-1, Q4-3); B -> (Q4-1, Q4-2).

## Q5 - Order stage decides the verdict (L367)
`if size_left[q] <= 0 and q not in self.results:`

| Row | A: capacity exhausted | B: quota not yet decided | Outcome (set GONE/ORDERED) |
| :-: | :-: | :-: | :-: |
| Q5-1 | T | T | **T** |
| Q5-2 | T | F | F (earlier verdict kept) |
| Q5-3 | F | T (masked) | F |
| Q5-4 | F | F (masked) | F |

B = F is produced with `full_results=True` on a closed quota (decided by the early-out). MC/DC: A -> (Q5-1, Q5-3); B -> (Q5-1, Q5-2).

## Q6 - Cart stage decides the verdict (L454; same form at L417 vouchers and L490 waiting list)
`if q not in self.results and size_left[q] <= 0:`

| Row | A: not yet decided | B: capacity exhausted | Outcome (set RESERVED) |
| :-: | :-: | :-: | :-: |
| Q6-1 | T | T | **T** |
| Q6-2 | T | F | F |
| Q6-3 | F | T (masked) | F |
| Q6-4 | F | F (masked) | F |

MC/DC: A -> (Q6-1, Q6-3); B -> (Q6-1, Q6-2).

## Q7 - Closed quota early-out (L495)
`if q.closed and not self._ignore_closed:`

| Row | A: closed | B: not ignore_closed | Outcome (ORDERED, 0) |
| :-: | :-: | :-: | :-: |
| Q7-1 | T | T | **T** |
| Q7-2 | T | F | F |
| Q7-3 | F | T (masked) | F |
| Q7-4 | F | F (masked) | F |

MC/DC: A -> (Q7-1, Q7-3); B -> (Q7-1, Q7-2).

---

## I1 - BR-2 product purchasability (`Item.is_available` + `is_available_by_time`)
Decision: `active AND NOT(from_set AND from > now) AND NOT(until_set AND until < now)`.
Conditions: A active, B available_from set, C available_from > now, D available_until set, E available_until < now.
C cannot be true when B is false (a missing date has no order) and the same for E/D; these **coupled** combinations
are infeasible, leaving 2 x 3 x 3 = **18 feasible rows** of the 32.

| Row | A | B | C | D | E | Available |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| I1-01 | T | T | T | T | T | F |
| I1-02 | T | T | T | T | F | F |
| I1-03 | T | T | T | F | F | F |
| I1-04 | T | T | F | T | T | F |
| I1-05 | T | T | F | T | F | **T** |
| I1-06 | T | T | F | F | F | **T** |
| I1-07 | T | F | F | T | T | F |
| I1-08 | T | F | F | T | F | **T** |
| I1-09 | T | F | F | F | F | **T** |
| I1-10 | F | T | T | T | T | F |
| I1-11 | F | T | T | T | F | F |
| I1-12 | F | T | T | F | F | F |
| I1-13 | F | T | F | T | T | F |
| I1-14 | F | T | F | T | F | F |
| I1-15 | F | T | F | F | F | F |
| I1-16 | F | F | F | T | T | F |
| I1-17 | F | F | F | T | F | F |
| I1-18 | F | F | F | F | F | F |

MC/DC (unique-cause; B/C and D/E are coupled, so flipping B also flips C, and flipping D also flips E):

| Condition | Pair | Outcome |
| :-: | :-: | :-: |
| A | I1-05 / I1-14 | T / F |
| B (with C) | I1-02 / I1-08 | F / T |
| C | I1-02 / I1-05 | F / T |
| D (with E) | I1-04 / I1-06 | F / T |
| E | I1-04 / I1-05 | F / T |

Boundary values for the sale window (3-point BVA, `test_bva_i1_sale_window_boundaries`): from = now-1 s / now / now+1 s
gives T / T / F; until = now-1 s / now / now+1 s gives F / T / T.

## O1 - BR-3 late payment rule (`Order._can_be_paid`, L1043)
`if not self.event.settings.get('payment_term_accept_late') and not ignore_date and not force: return 'late'`
(only reached when the order is not PENDING).

| Row | A: late payments not accepted | B: not ignore_date | C: not force | Outcome (reject as late) |
| :-: | :-: | :-: | :-: | :-: |
| O1-1 | T | T | T | **T** |
| O1-2 | T | T | F | F |
| O1-3 | T | F | T | F |
| O1-4 | T | F | F | F |
| O1-5 | F | T | T | F |
| O1-6 | F | T | F | F |
| O1-7 | F | F | T | F |
| O1-8 | F | F | F | F |

MC/DC: A -> (O1-1, O1-5); B -> (O1-1, O1-3); C -> (O1-1, O1-2).
When the outcome is F the test asserts that the decision fell through to `_is_still_available()` (patched with a test double
that returns a marker), so a wrong outcome is visible.

## Summary
| Decision | Conditions | MCC rows run | MC/DC pairs |
| :--- | :-: | :-: | :-: |
| Q1 | 2 | 4 | 2 |
| Q2 | 2 | 4 | 2 |
| Q3 | 3 | 8 | 3 |
| Q4 | 2 | 4 | 2 |
| Q5 | 2 | 4 | 2 |
| Q6 | 2 | 4 | 2 |
| Q7 | 2 | 4 | 2 |
| I1 | 5 | 18 feasible (14 infeasible, coupled) | 5 |
| O1 | 3 | 8 | 3 |
| **Total** | | **58** | **23** |
