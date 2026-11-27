"""
Coverage quality gate for Area 1 (server-side business logic).

Reads a coverage.py JSON report (produced with --cov-branch) and FAILS (exit 1) unless every
function in SCOPE has 100 % statement and 100 % branch coverage. The only tolerated gap is
listed in JUSTIFIED_BRANCHES together with the reason; a new gap anywhere in scope fails the gate.

Usage (from the repository's src/ directory):
    pytest tests/team/zubair --cov=pretix.base.services.quotas --cov=pretix.base.models.orders \
        --cov=pretix.base.models.items --cov-branch --cov-report=json:coverage-area1.json
    python tests/team/zubair/coverage_gate.py coverage-area1.json
"""
import json
import os
import sys

# file (basename) -> functions that make up the business-rule logic under test.
# "*" means every function of the module.
SCOPE = {
    "quotas.py": "*",                                   # BR-1 capacity, BR-4 cart expiry (critical module)
    "items.py": ["Item.is_available", "Item.is_available_by_time"],   # BR-2 purchasability
    "orders.py": ["Order._can_be_paid"],                # BR-3 may the order be paid
}

# (file, from_line, to_line): justification. Kept deliberately tiny and reviewed in the viva.
JUSTIFIED_BRANCHES = {
    ("quotas.py", 361, 363): (
        "Infeasible branch: the query at L304-305 only returns order lines with status PAID or "
        "PENDING, so after `if status == PAID` the `elif status == PENDING` can never be False."
    ),
}


def main(path):
    data = json.load(open(path))
    failures, checked = [], 0
    for fname, fdata in data["files"].items():
        base = os.path.basename(fname)
        if base not in SCOPE:
            continue
        wanted = SCOPE[base]
        for func, fd in fdata.get("functions", {}).items():
            if not func or (wanted != "*" and func not in wanted):
                continue
            checked += 1
            for line in fd["missing_lines"]:
                failures.append(f"{base}:{line} statement not covered ({func})")
            for src, dst in fd.get("missing_branches", []):
                key = (base, src, dst)
                if key in JUSTIFIED_BRANCHES:
                    print(f"JUSTIFIED  {base}:{src}->{dst}  {JUSTIFIED_BRANCHES[key]}")
                else:
                    failures.append(f"{base}:{src}->{dst} branch not covered ({func})")
    expected_min = sum(1 for v in SCOPE.values() if v != "*") + 1
    if checked < expected_min:
        failures.append(f"only {checked} scoped functions found in the report - was --cov set correctly?")
    print(f"Scoped functions checked: {checked}")
    if failures:
        print("COVERAGE GATE FAILED")
        for f in failures:
            print("  -", f)
        return 1
    print("COVERAGE GATE PASSED: 100% statement and branch coverage on the business-rule scope")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "coverage-area1.json"))
