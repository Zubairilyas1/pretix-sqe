"""
Multiple Condition Coverage (MCC) and MC/DC on the REAL pretix decisions.

Every row of every MCC table in docs/sqe/zubair/MCC_MCDC_TABLES.md is one parametrised
test case here (test id = table row id). The MC/DC independence pairs listed in the
document are re-checked by ``test_mcdc_pairs_are_valid``: each pair must differ in exactly
one condition and must flip the decision outcome.

Decisions under test (source is NOT modified):
  quotas.py (critical module)
    Q1  L126  not allow_repeatable_read and tx_in_repeatable_read
    Q2  L151  (time.time() - ts < 120) or allow_cache_stale
    Q3  L221  result <= ORDERED and close_when_sold_out and not q.closed
    Q4  L363  q.release_after_exit and line['is_exited']
    Q5  L367  size_left[q] <= 0 and q not in results          (orders stage)
    Q6  L454  q not in results and size_left[q] <= 0          (carts stage, same form as L417/L490)
    Q7  L495  q.closed and not ignore_closed
  items.py  (BR-2, item purchasability)
    I1  Item.is_available() = active AND NOT(from set AND from > now) AND NOT(until set AND until < now)
  orders.py (BR-3, may an order be paid)
    O1  L1043 not accept_late and not ignore_date and not force
"""
import datetime
import time
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import fakeredis
import pytest
from django.db import connection
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import (
    CartPosition, Checkin, CheckinList, Item, Order, OrderPosition, Quota,
)
from pretix.base.services import quotas as quotas_module
from pretix.base.services.quotas import QuotaAvailability

OK, RESERVED, ORDERED, GONE = (
    Quota.AVAILABILITY_OK, Quota.AVAILABILITY_RESERVED, Quota.AVAILABILITY_ORDERED, Quota.AVAILABILITY_GONE,
)
T, F = True, False


# --------------------------------------------------------------------------- MCC tables
# (row_id, conditions..., expected decision outcome)
MCC_Q1 = [  # A = not allow_repeatable_read, B = tx_in_repeatable_read
    ("Q1-1", T, T, T),
    ("Q1-2", T, F, F),
    ("Q1-3", F, T, F),
    ("Q1-4", F, F, F),
]
MCC_Q2 = [  # A = cache entry younger than 120 s, B = allow_cache_stale
    ("Q2-1", T, T, T),
    ("Q2-2", T, F, T),
    ("Q2-3", F, T, T),
    ("Q2-4", F, F, F),
]
MCC_Q3 = [  # A = result <= ORDERED (sold out), B = close_when_sold_out, C = not closed
    ("Q3-1", T, T, T, T),
    ("Q3-2", T, T, F, F),
    ("Q3-3", T, F, T, F),
    ("Q3-4", T, F, F, F),
    ("Q3-5", F, T, T, F),
    ("Q3-6", F, T, F, F),
    ("Q3-7", F, F, T, F),
    ("Q3-8", F, F, F, F),
]
MCC_Q4 = [  # A = quota.release_after_exit, B = position has exited
    ("Q4-1", T, T, T),
    ("Q4-2", T, F, F),
    ("Q4-3", F, T, F),
    ("Q4-4", F, F, F),
]
MCC_Q5 = [  # A = size_left <= 0 after this order line, B = quota not yet decided
    ("Q5-1", T, T, T),
    ("Q5-2", T, F, F),
    ("Q5-3", F, T, F),
    ("Q5-4", F, F, F),
]
MCC_Q6 = [  # A = quota not yet decided, B = size_left <= 0 after this cart line
    ("Q6-1", T, T, T),
    ("Q6-2", T, F, F),
    ("Q6-3", F, T, F),
    ("Q6-4", F, F, F),
]
MCC_Q7 = [  # A = quota.closed, B = not ignore_closed
    ("Q7-1", T, T, T),
    ("Q7-2", T, F, F),
    ("Q7-3", F, T, F),
    ("Q7-4", F, F, F),
]
# I1: A = active, B = available_from set, C = available_from > now, D = available_until set, E = until < now
# Rows where a date is "not set" but "in future/past" are physically impossible (a NULL date
# has no ordering); they are listed in the document as infeasible and excluded here.
_I1_FEASIBLE = [
    (a, b, c, d, e)
    for a in (T, F) for b in (T, F) for c in (T, F) for d in (T, F) for e in (T, F)
    if (b or not c) and (d or not e)
]
MCC_I1 = [
    (f"I1-{i + 1:02d}", a, b, c, d, e, a and not (b and c) and not (d and e))
    for i, (a, b, c, d, e) in enumerate(_I1_FEASIBLE)
]
MCC_O1 = [  # A = not accept_late, B = not ignore_date, C = not force   -> True means "reject as late"
    ("O1-1", T, T, T, T),
    ("O1-2", T, T, F, F),
    ("O1-3", T, F, T, F),
    ("O1-4", T, F, F, F),
    ("O1-5", F, T, T, F),
    ("O1-6", F, T, F, F),
    ("O1-7", F, F, T, F),
    ("O1-8", F, F, F, F),
]

# MC/DC independence pairs derived from the tables above (see MCC_MCDC_TABLES.md)
MCDC_PAIRS = {
    "Q1": (MCC_Q1, {"A": ("Q1-1", "Q1-3"), "B": ("Q1-1", "Q1-2")}),
    "Q2": (MCC_Q2, {"A": ("Q2-2", "Q2-4"), "B": ("Q2-3", "Q2-4")}),
    "Q3": (MCC_Q3, {"A": ("Q3-1", "Q3-5"), "B": ("Q3-1", "Q3-3"), "C": ("Q3-1", "Q3-2")}),
    "Q4": (MCC_Q4, {"A": ("Q4-1", "Q4-3"), "B": ("Q4-1", "Q4-2")}),
    "Q5": (MCC_Q5, {"A": ("Q5-1", "Q5-3"), "B": ("Q5-1", "Q5-2")}),
    "Q6": (MCC_Q6, {"A": ("Q6-1", "Q6-3"), "B": ("Q6-1", "Q6-2")}),
    "Q7": (MCC_Q7, {"A": ("Q7-1", "Q7-3"), "B": ("Q7-1", "Q7-2")}),
    # B/C and D/E are coupled (a NULL date cannot be "in the future/past"): flipping B forces C,
    # flipping D forces E. Those pairs name the coupled condition as a third element.
    "I1": (MCC_I1, {"A": ("I1-05", "I1-14"), "B": ("I1-02", "I1-08", "C"), "C": ("I1-02", "I1-05"),
                    "D": ("I1-04", "I1-06", "E"), "E": ("I1-04", "I1-05")}),
    "O1": (MCC_O1, {"A": ("O1-1", "O1-5"), "B": ("O1-1", "O1-3"), "C": ("O1-1", "O1-2")}),
}


def _ids(table):
    return [r[0] for r in table]


@pytest.fixture
def ev(team_organizer, team_event):
    with scope(organizer=team_organizer):
        yield team_event


@pytest.fixture
def quota(ev, team_item):
    q = Quota.objects.create(event=ev, name="Q", size=2)
    q.items.add(team_item)
    return q


def _order(ev, item, qty=1, status=Order.STATUS_PAID):
    o = Order.objects.create(
        code=f"M{Order.objects.count():05d}", event=ev, email="m@example.org", status=status, locale="en",
        datetime=now(), expires=now() + datetime.timedelta(days=3), total=Decimal("10.00"),
        sales_channel=ev.organizer.sales_channels.get(identifier="web"),
    )
    ps = [OrderPosition.objects.create(order=o, item=item, price=Decimal("10.00"), positionid=i + 1) for i in range(qty)]
    return o, ps


# =========================================================================== Q1
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_not_allow, b_in_rr, raises", MCC_Q1, ids=_ids(MCC_Q1))
def test_mcc_q1_repeatable_read_guard(quota, monkeypatch, row, a_not_allow, b_in_rr, raises):
    monkeypatch.setattr(connection, "tx_in_repeatable_read", b_in_rr, raising=False)
    qa = QuotaAvailability(allow_repeatable_read=not a_not_allow)
    qa.queue(quota)
    if raises:
        with pytest.raises(ValueError):
            qa.compute()
    else:
        qa.compute()
        assert qa.results[quota] == (OK, 2)


# =========================================================================== Q2
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_fresh, b_stale_ok, use_cache", MCC_Q2, ids=_ids(MCC_Q2))
def test_mcc_q2_cache_freshness(ev, quota, monkeypatch, row, a_fresh, b_stale_ok, use_cache):
    r = fakeredis.FakeRedis()
    monkeypatch.setattr(quotas_module, "settings", SimpleNamespace(
        HAS_REDIS=True, DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}}))
    monkeypatch.setattr(quotas_module, "django_redis", SimpleNamespace(get_redis_connection=lambda a: r))
    ts = int(time.time()) - (10 if a_fresh else 500)
    r.hset(f"quotas:{ev.pk}:availabilitycache", str(quota.pk), f"0,0,{ts}")  # cached verdict: GONE
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute(allow_cache=True, allow_cache_stale=b_stale_ok)
    assert qa.results[quota] == ((GONE, 0) if use_cache else (OK, 2))


# =========================================================================== Q3
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_sold_out, b_flag, c_open, closes", MCC_Q3, ids=_ids(MCC_Q3))
def test_mcc_q3_close_when_sold_out(quota, row, a_sold_out, b_flag, c_open, closes):
    quota.close_when_sold_out = b_flag
    quota.closed = not c_open
    quota.save()
    qa = QuotaAvailability()
    qa.results[quota] = (GONE, 0) if a_sold_out else (RESERVED, 0)  # RESERVED (20) > ORDERED (10)
    qa._close([quota])
    quota.refresh_from_db()
    assert quota.closed is (closes or not c_open)
    assert quota.all_logentries().filter(action_type="pretix.event.quota.closed").count() == (1 if closes else 0)


# =========================================================================== Q4
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_release, b_exited, released", MCC_Q4, ids=_ids(MCC_Q4))
def test_mcc_q4_release_after_exit(ev, team_item, quota, row, a_release, b_exited, released):
    quota.release_after_exit = a_release
    quota.save()
    cl = CheckinList.objects.create(event=ev, name="Door", allow_entry_after_exit=False)
    _, (p,) = _order(ev, team_item)
    t = now()
    Checkin.objects.create(position=p, list=cl, type=Checkin.TYPE_ENTRY, datetime=t - datetime.timedelta(hours=2))
    if b_exited:
        Checkin.objects.create(position=p, list=cl, type=Checkin.TYPE_EXIT, datetime=t - datetime.timedelta(hours=1))
    qa = QuotaAvailability(early_out=False)
    qa.queue(quota)
    qa.compute()
    assert qa.count_exited_orders[quota] == (1 if released else 0)
    assert qa.results[quota] == (OK, 2 if released else 1)


# =========================================================================== Q5
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_limit_hit, b_undecided, sets_verdict", MCC_Q5, ids=_ids(MCC_Q5))
def test_mcc_q5_orders_verdict(ev, team_item, quota, row, a_limit_hit, b_undecided, sets_verdict):
    """B=False is produced with full_results=True on a CLOSED quota (decided by the early-out as ORDERED)."""
    if not b_undecided:
        quota.closed = True
        quota.save()
    _order(ev, team_item, qty=2 if a_limit_hit else 1)
    qa = QuotaAvailability(full_results=True)
    qa.queue(quota)
    qa.compute()
    if sets_verdict:
        assert qa.results[quota] == (GONE, 0)
    elif not b_undecided:
        assert qa.results[quota] == (ORDERED, 0)   # early-out verdict kept
    else:
        assert qa.results[quota] == (OK, 1)        # decided only in the final loop


# =========================================================================== Q6
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_undecided, b_limit_hit, sets_verdict", MCC_Q6, ids=_ids(MCC_Q6))
def test_mcc_q6_carts_verdict(ev, team_item, quota, row, a_undecided, b_limit_hit, sets_verdict):
    if not a_undecided:
        quota.closed = True
        quota.save()
    for i in range(2 if b_limit_hit else 1):
        CartPosition.objects.create(event=ev, item=team_item, price=Decimal("10"), cart_id=f"c{i}",
                                    expires=now() + datetime.timedelta(minutes=10))
    qa = QuotaAvailability(full_results=True)
    qa.queue(quota)
    qa.compute()
    assert qa.count_cart[quota] == (2 if b_limit_hit else 1)
    if sets_verdict:
        assert qa.results[quota] == (RESERVED, 0)
    elif not a_undecided:
        assert qa.results[quota] == (ORDERED, 0)
    else:
        assert qa.results[quota] == (OK, 1)


# =========================================================================== Q7
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_closed, b_not_ignore, early_verdict", MCC_Q7, ids=_ids(MCC_Q7))
def test_mcc_q7_closed_early_out(quota, row, a_closed, b_not_ignore, early_verdict):
    quota.closed = a_closed
    quota.save()
    qa = QuotaAvailability(ignore_closed=not b_not_ignore)
    qa.queue(quota)
    qa.compute()
    assert qa.results[quota] == ((ORDERED, 0) if early_verdict else (OK, 2))


# =========================================================================== I1 (BR-2)
@pytest.mark.parametrize("row, a_active, b_from_set, c_from_future, d_until_set, e_until_past, available",
                         MCC_I1, ids=_ids(MCC_I1))
def test_mcc_i1_item_is_available(row, a_active, b_from_set, c_from_future, d_until_set, e_until_past, available):
    t = now()
    item = Item(
        active=a_active,
        available_from=(t + datetime.timedelta(days=1) if c_from_future else t - datetime.timedelta(days=1))
        if b_from_set else None,
        available_until=(t - datetime.timedelta(days=1) if e_until_past else t + datetime.timedelta(days=1))
        if d_until_set else None,
    )
    assert item.is_available(now_dt=t) is available


@pytest.mark.parametrize("field, offset_s, available", [
    ("available_from", -1, True), ("available_from", 0, True), ("available_from", 1, False),
    ("available_until", -1, False), ("available_until", 0, True), ("available_until", 1, True),
])
def test_bva_i1_sale_window_boundaries(field, offset_s, available):
    """3-point BVA on both ends of the sale window (BR-2): from > now is closed, until < now is closed."""
    t = now()
    item = Item(active=True, **{field: t + datetime.timedelta(seconds=offset_s)})
    assert item.is_available(now_dt=t) is available


def test_i1_default_now_uses_time_machine():
    """now_dt omitted -> time_machine_now() is used (default-argument branch)."""
    assert Item(active=True).is_available() is True
    assert Item(active=True, available_until=now() - datetime.timedelta(days=1)).is_available_by_time() is False


# =========================================================================== O1 (BR-3)
@pytest.mark.django_db
@pytest.mark.parametrize("row, a_not_accept_late, b_not_ignore_date, c_not_force, rejected_late", MCC_O1, ids=_ids(MCC_O1))
def test_mcc_o1_late_payment_rule(ev, team_item, row, a_not_accept_late, b_not_ignore_date, c_not_force, rejected_late):
    """Order is EXPIRED (so the PENDING shortcut is not taken) and has no last payment date."""
    ev.settings.payment_term_accept_late = not a_not_accept_late
    o, _ = _order(ev, team_item, status=Order.STATUS_EXPIRED)
    with mock.patch.object(Order, "_is_still_available", return_value="AVAILABILITY-CHECK") as still:
        res = o._can_be_paid(ignore_date=not b_not_ignore_date, force=not c_not_force)
    if rejected_late:
        assert "no late payments" in str(res)
        still.assert_not_called()
    else:
        assert res == "AVAILABILITY-CHECK"
        still.assert_called_once()


# =========================================================================== MC/DC pair validation
@pytest.mark.parametrize("decision", sorted(MCDC_PAIRS))
def test_mcdc_pairs_are_valid(decision):
    """For every condition the declared pair differs ONLY in that condition and flips the outcome."""
    table, pairs = MCDC_PAIRS[decision]
    rows = {r[0]: r[1:] for r in table}
    n = len(table[0]) - 2
    names = "ABCDE"[:n]
    assert set(pairs) == set(names), "every condition needs an independence pair"
    for cond, (r1, r2, *coupled) in pairs.items():
        c1, c2 = rows[r1][:n], rows[r2][:n]
        differing = [names[i] for i in range(n) if c1[i] != c2[i]]
        assert differing == sorted([cond, *coupled]), (
            f"{decision}: pair {r1}/{r2} differs in {differing}, expected only {[cond, *coupled]}")
        assert rows[r1][n] != rows[r2][n], f"{decision}: pair {r1}/{r2} does not flip the outcome"
