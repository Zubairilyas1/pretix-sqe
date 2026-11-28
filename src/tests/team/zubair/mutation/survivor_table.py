"""Build the survivor analysis table of MUTATION_REPORT.md from the two Cosmic Ray sessions.

A run-1 survivor is matched to run 2 by (operator, occurrence) - both sessions mutate the same file.
The classification per mutant is in CLASSIFY (reviewed by hand, see MUTATION_REPORT.md section 4); the script
refuses to print a table where a mutant classified "equivalent" was killed in run 2 or a "killable" one survived.
Usage: python src/tests/team/zubair/mutation/survivor_table.py > table.md
"""
import sqlite3
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
K = "test_mutation_killers.py::"
# (line, operator prefix) -> (class, reason / killing test)
CLASSIFY = {
    (121, "ReplaceFalseWithTrue"): ("Missing test", f"default `allow_cache_stale=False` never relied on - {K}test_cache_age_boundary_bva"),
    (151, "NumberReplacer"): ("Missing test", f"no test at the 120 s boundary - {K}test_cache_age_boundary_bva (119/120/121 s)"),
    (151, "ReplaceComparisonOperator_Lt_LtE"): ("Missing test", f"boundary 120 s - {K}test_cache_age_boundary_bva"),
    (151, "ReplaceBinaryOperator_Sub_Mod"): ("Equivalent", "`now % ts` equals `now - ts` for every timestamp ts > now/2, i.e. for every real cache entry"),
    (153, "ReplaceComparisonOperator_Eq_GtE"): ("Equivalent", "cached value is digits or 'None'; every digit string sorts before 'N', so `>=` and `==` agree"),
    (196, "NumberReplacer"): ("Weak assertion", f"lock TTL was not asserted - {K}test_cache_write_contract (ttl == 10)"),
    (212, "NumberReplacer"): ("Weak assertion", f"cache TTL only checked `> 0` - {K}test_cache_write_contract (ttl == 604800)"),
    (212, "ReplaceBinaryOperator"): ("Weak assertion", f"cache TTL only checked `> 0` - {K}test_cache_write_contract"),
    (221, "ReplaceComparisonOperator_LtE_Lt"): ("Missing test", f"no quota sold out by PENDING orders - {K}test_quota_sold_out_by_pending_orders_is_closed"),
    (221, "SwapAvailabilityVerdict"): ("Missing test (custom operator)", f"ORDERED verdict must also close the quota - {K}test_quota_sold_out_by_pending_orders_is_closed"),
    (243, "ZeroIterationForLoop"): ("Weak assertion", f"count dicts never compared as a whole - {K}test_counters_initialised_for_computed_quota"),
    (292, "NumberReplacer"): ("Equivalent", "size_left == 0 without a verdict is unreachable: every stage sets a verdict at <= 0"),
    (292, "ReplaceComparisonOperator_Gt_GtE"): ("Equivalent", "same reason as the line above"),
    (309, "ReplaceBinaryOperator_BitAnd_BitOr"): ("Equivalent", "SQL pre-filter only; rows are dispatched again through `_item_to_quotas`, so extra rows are ignored"),
    (311, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "alternatives are mutually exclusive (variation NULL vs variation in set), so OR == XOR"),
    (340, "NumberReplacer"): ("Equivalent", "`is_exited` is only used as a truth value and as a sort key; 1 and 2 behave the same"),
    (348, "NumberReplacer"): ("Equivalent", "branch only runs when no queued quota releases after exit, so `is_exited` is never read"),
    (357, "ReplaceComparisonOperator_Eq_Is"): ("Missing test", f"`is` works for cached small ints - {K}test_subevent_match_uses_value_equality_for_large_ids"),
    (358, "ReplaceComparisonOperator_Eq_GtE"): ("Equivalent", "query returns only status 'p' or 'n'; 'n' >= 'p' is False, so `>=` == `==`"),
    (361, "ReplaceComparisonOperator"): ("Equivalent", "only status 'n' reaches this elif (see infeasible branch 361->363)"),
    (368, "ReplaceComparisonOperator_Eq_GtE"): ("Equivalent", "only 'p' or 'n' possible; same as L358"),
    (389, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "`valid_until IS NULL` and `valid_until >= now` cannot both hold"),
    (392, "ReplaceBinaryOperator_BitAnd_BitOr"): ("Equivalent", "SQL pre-filter only; dispatch through `_item_to_quotas` ignores vouchers of other products"),
    (394, "ReplaceBinaryOperator"): ("Missing test", f"item linked directly and via a variation - {K}test_item_voucher_counts_when_item_is_in_quota_directly_and_via_variation"),
    (397, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "alternatives mutually exclusive (variation NULL vs variation in set)"),
    (399, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "a voucher is bound either to a product or to a quota (pretix validation), never both"),
    (414, "ReplaceComparisonOperator_Eq_Is"): ("Missing test", f"large ids - {K}test_subevent_match_uses_value_equality_for_large_ids"),
    (417, "ReplaceComparisonOperator_LtE_Eq"): ("Missing test", f"vouchers overshooting capacity - {K}test_voucher_overshooting_capacity"),
    (433, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "`voucher IS NULL` and `voucher.block_quota = False` cannot both hold"),
    (434, "ReplaceBinaryOperator_BitOr_BitXor"): ("Missing test", f"non-blocking AND expired voucher - {K}test_cart_with_non_blocking_and_expired_voucher_counts"),
    (438, "ReplaceBinaryOperator_BitAnd_BitOr"): ("Equivalent", "SQL pre-filter only, see L309"),
    (440, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "mutually exclusive alternatives, see L311"),
    (451, "ReplaceComparisonOperator_Eq_Is"): ("Missing test", f"large ids - {K}test_subevent_match_uses_value_equality_for_large_ids"),
    (454, "ReplaceComparisonOperator_LtE_Eq"): ("Missing test", f"carts overshooting capacity - {K}test_carts_overshooting_capacity"),
    (461, "ReplaceComparisonOperator_Gt_GtE"): ("Missing test", f"exact auto-disable instant - {K}test_waitinglist_auto_disable_exact_boundary"),
    (461, "ReplaceOrWithAnd"): ("Missing test", f"relative auto-disable date - {K}test_waitinglist_auto_disable_relative_to_event_date"),
    (476, "ReplaceBinaryOperator_BitAnd_BitOr"): ("Equivalent", "SQL pre-filter only, see L309"),
    (478, "ReplaceBinaryOperator_BitOr_BitXor"): ("Equivalent", "mutually exclusive alternatives, see L311"),
    (487, "ReplaceComparisonOperator_Eq_Is"): ("Missing test", f"large ids - {K}test_subevent_match_uses_value_equality_for_large_ids"),
    (490, "NumberReplacer"): ("Missing test", f"waiting list leaving exactly one seat - {K}test_waitinglist_leaving_one_seat_keeps_quota_available"),
    (490, "ReplaceComparisonOperator_LtE_Eq"): ("Missing test", f"waiting list overshooting - {K}test_waitinglist_overshooting_capacity"),
}


def rows(db):
    con = sqlite3.connect(db)
    return {(op, occ): (row, out, diff) for op, occ, row, out, diff in con.execute(
        "select ms.operator_name, ms.occurrence, ms.start_pos_row, wr.test_outcome, wr.diff "
        "from mutation_specs ms join work_results wr using(job_id)")}


def classify(line, op):
    name = op.split("/")[1]
    for (ln, prefix), v in CLASSIFY.items():
        if ln == line and name.startswith(prefix):
            return v
    raise KeyError((line, name))


def changed(diff):
    lines = [x[1:].strip() for x in diff.splitlines() if x.startswith(("+", "-")) and not x.startswith(("+++", "---"))]
    return f"`{lines[0]}` -> `{lines[1]}`" if len(lines) == 2 else ""


def main():
    r1, r2 = rows(R / "run1_baseline/session.sqlite"), rows(R / "run2_after_kills/session.sqlite")
    surv = sorted([(v[0], k) for k, v in r1.items() if v[1] == "SURVIVED"])
    print("| # | Line | Operator | Mutation | Class | Reason / killing test | Run 2 |")
    print("| :-: | :-: | :--- | :--- | :--- | :--- | :-: |")
    counts = {}
    for i, (line, key) in enumerate(surv, 1):
        cls, why = classify(line, key[0])
        out2 = r2[key][1]
        base = cls.split(" (")[0]
        counts[base] = counts.get(base, 0) + 1
        if base == "Equivalent" and out2 != "SURVIVED":
            raise SystemExit(f"inconsistent: {key} classified equivalent but {out2} in run 2")
        if base != "Equivalent" and out2 != "KILLED":
            raise SystemExit(f"inconsistent: {key} classified killable but {out2} in run 2")
        mut = changed(r1[key][2]).replace("|", "\\|")
        print(f"| {i} | {line} | {key[0]} #{key[1]} | {mut} | {cls} | {why} | {out2.lower()} |")
    print()
    print("Totals: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
