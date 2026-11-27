"""
WCAG 2.1 AA scan with axe-core (Task 3.2.2) on the key screens of W1 and W2.

Each scan writes ``reports/axe_<screen>.json`` (the raw axe result) so the
findings table in ``a11y_findings.md`` can be traced back to evidence. The
remediated rule (see ``screen_remediation/``) is asserted to have zero
violations, so a regression fails the suite.

Run:  cd src && ../.venv/Scripts/python -m pytest tests/team/tawassul/usability_a11y/test_axe_scan.py -s
"""
import json
from pathlib import Path

import pytest
from axe_playwright_python.sync_playwright import Axe

from ..flows import add_to_cart, proceed_to_checkout

pytestmark = pytest.mark.django_db(transaction=True)

REPORTS = Path(__file__).parent / "reports"
WCAG_AA = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}}


def scan(page, screen):
    """Run axe on the current page, save the report and return the violations."""
    result = Axe().run(page, options=WCAG_AA)
    violations = result.response["violations"]
    REPORTS.mkdir(exist_ok=True)
    summary = [
        {"rule": v["id"], "impact": v["impact"], "wcag": [t for t in v["tags"] if t.startswith("wcag")],
         "help": v["help"], "nodes": [n["target"][0] if n["target"] else "" for n in v["nodes"]]}
        for v in violations
    ]
    (REPORTS / f"axe_{screen}.json").write_text(
        json.dumps({"url": page.url, "violations": summary}, indent=2), "utf-8")
    print(f"\n[axe] {screen}: {len(violations)} rules violated, "
          f"{sum(len(v['nodes']) for v in violations)} elements")
    for s in summary:
        print(f"   {s['impact']:>8}  {s['rule']:<28} {len(s['nodes'])} x  {s['help']}")
    return violations


def test_axe_customer_shop_page(page, shop_url, shop):
    page.goto(shop_url)
    scan(page, "shop")


def test_axe_customer_checkout_page(page, shop_url, shop, team_item):
    add_to_cart(page, shop_url, team_item)
    proceed_to_checkout(page)
    scan(page, "checkout_questions")


def test_axe_organizer_item_create_page(control_login, live_url, shop):
    control_login.goto(f"{live_url}/control/event/sqe-org/sqe-conf/items/add")
    scan(control_login, "control_item_add")


# Rules fixed in screen_remediation/ (pretixcontrol/base.html). Before the fix the
# organizer item page violated all three; they must stay at zero.
REMEDIATED = ("html-has-lang", "image-alt", "link-name")


@pytest.mark.parametrize("rule", REMEDIATED)
def test_remediated_rule_stays_fixed_on_organizer_page(control_login, live_url, shop, rule):
    control_login.goto(f"{live_url}/control/event/sqe-org/sqe-conf/items/add")
    result = Axe().run(control_login, options={"runOnly": {"type": "rule", "values": [rule]}})
    nodes = [n["target"] for v in result.response["violations"] for n in v["nodes"]]
    assert nodes == [], f"{rule} regressed on: {nodes}"
