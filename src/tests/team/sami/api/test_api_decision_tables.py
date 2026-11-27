"""
Decision-table testing at API level (POST orders/) for every rule with two or more conditions.

DT-1  Business Rule 2 - a product may be ordered iff
        C1 product active  AND  C2 now inside the sale window  AND  C3 product has a quota with capacity
      2^3 = 8 rules (columns). Expected outcome per the rule; rows where pretix deviates are strict xfail (W-07).

DT-2  Business Rule 1 - per-order limits, number of positions n with min_per_order=2, max_per_order=3:
        C1 n >= min  AND  C2 n <= max
      (C1=F, C2=F) is infeasible because min <= max; the 3 feasible rules are tested. Deviations: W-08.

Every row reads back the shared record: on rejection no order exists and the quota availability is unchanged.
"""
import datetime

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import Order, Quota

W07 = "W-07: order API ignores the sale window"
W08 = "W-08: order API ignores min/max per order"

# (rule id, C1 active, C2 in window, C3 has quota, expected)
DT1 = [
    ("R1", True, True, True, "accept"),
    ("R2", True, True, False, "reject"),
    ("R3", True, False, True, "reject"),
    ("R4", True, False, False, "reject"),
    ("R5", False, True, True, "reject"),
    ("R6", False, True, False, "reject"),
    ("R7", False, False, True, "reject"),
    ("R8", False, False, False, "reject"),
]
DT1_DEVIATIONS = {"R3": W07}   # only the window condition alone decides -> pretix accepts


def _dt1_params():
    return [pytest.param(*r, id=f"DT1-{r[0]}-active{r[1]:d}-window{r[2]:d}-quota{r[3]:d}",
                         marks=[pytest.mark.xfail(strict=True, reason=DT1_DEVIATIONS[r[0]])] if r[0] in DT1_DEVIATIONS else [])
            for r in DT1]


@pytest.mark.django_db
@pytest.mark.parametrize("rule, active, in_window, has_quota, expected", _dt1_params())
def test_dt1_purchasability(rule, active, in_window, has_quota, expected, api, organizer_client, team_item, team_quota):
    with scopes_disabled():
        team_item.active = active
        if not in_window:
            team_item.available_until = now() - datetime.timedelta(days=1)
        team_item.save()
        if not has_quota:
            team_quota.items.remove(team_item)
        before_orders = Order.objects.filter(event=api.event).count()
        before_avail = Quota.objects.get(pk=team_quota.pk).availability()
    resp = organizer_client.post(api.orders(), api.order_payload(1), format="json")
    with scopes_disabled():
        after_orders = Order.objects.filter(event=api.event).count()
        after_avail = Quota.objects.get(pk=team_quota.pk).availability()
    if expected == "accept":
        assert resp.status_code == 201, resp.content
        assert after_orders == before_orders + 1
        assert after_avail[1] == before_avail[1] - 1
    else:
        assert resp.status_code == 400, f"{rule}: {resp.status_code} {resp.content[:200]!r}"
        assert after_orders == before_orders
        assert after_avail == before_avail


# (rule id, n positions, C1 n>=min, C2 n<=max, expected)
DT2 = [
    ("R1", 2, True, True, "accept"),    # n = min
    ("R2", 4, True, False, "reject"),   # n = max + 1
    ("R3", 1, False, True, "reject"),   # n = min - 1
]
DT2_DEVIATIONS = {"R2": W08, "R3": W08}


@pytest.mark.django_db
@pytest.mark.parametrize("rule, n, c_min, c_max, expected", [
    pytest.param(*r, id=f"DT2-{r[0]}-n{r[1]}-min{r[2]:d}-max{r[3]:d}",
                 marks=[pytest.mark.xfail(strict=True, reason=DT2_DEVIATIONS[r[0]])] if r[0] in DT2_DEVIATIONS else [])
    for r in DT2])
def test_dt2_per_order_limits(rule, n, c_min, c_max, expected, api, organizer_client, team_item, team_quota):
    with scopes_disabled():
        team_item.min_per_order = 2
        team_item.max_per_order = 3
        team_item.save()
        before = Order.objects.filter(event=api.event).count()
    resp = organizer_client.post(api.orders(), api.order_payload(n), format="json")
    with scopes_disabled():
        after = Order.objects.filter(event=api.event).count()
    if expected == "accept":
        assert resp.status_code == 201
        assert after == before + 1
    else:
        assert resp.status_code == 400, f"{rule}: {resp.status_code}"
        assert after == before


def test_dt2_infeasible_rule_is_rejected_by_configuration(api, organizer_client, team_item, db):
    """The 4th combination (n < min AND n > max) needs min > max, which pretix refuses to store via the API."""
    resp = organizer_client.patch(api.items() + f"{team_item.pk}/", {"min_per_order": 5, "max_per_order": 3},
                                  format="json")
    assert resp.status_code == 400
