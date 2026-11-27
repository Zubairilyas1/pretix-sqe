"""
White-box unit tests for the critical business-rule module
``pretix/base/services/quotas.py`` (class ``QuotaAvailability``).

Goal: 100 % statement and 100 % branch coverage of the module.
Every test names the source lines / branches it is written for, so that the
coverage report can be traced back to a test (see docs/sqe/zubair/COVERAGE_REPORT.md).

Business rules exercised here:
  BR-1  Quota capacity limit (available = size - paid - pending - vouchers - carts - waiting list)
  BR-3  Paid vs pending orders give different sold-out verdicts (GONE vs ORDERED)
  BR-4  Cart reservations hold capacity only while ``expires >= now``

Test doubles used (no production code is modified):
  * ``FakeRedis`` from ``fakeredis`` replaces the Redis connection for the cache paths.
  * The module-level ``settings`` reference of ``quotas.py`` is replaced by a
    ``SimpleNamespace`` to switch ``HAS_REDIS`` and the database ENGINE string.
  * ``quota_availability.send`` is patched to simulate a plugin receiver.
"""
import datetime
import time
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import fakeredis
import pytest
from django.conf import settings as django_settings
from django.db import connection
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import (
    CartPosition, Checkin, CheckinList, ItemVariation, Order, OrderPosition,
    Quota, SubEvent, Voucher, WaitingListEntry,
)
from pretix.base.reldate import RelativeDateWrapper
from pretix.base.services import quotas as quotas_module
from pretix.base.services.quotas import QuotaAvailability, grouper

OK = Quota.AVAILABILITY_OK
RESERVED = Quota.AVAILABILITY_RESERVED
ORDERED = Quota.AVAILABILITY_ORDERED
GONE = Quota.AVAILABILITY_GONE


# --------------------------------------------------------------------------- helpers
def _order(event, item, status=Order.STATUS_PAID, qty=1, variation=None, subevent=None, code=None, **pos_kwargs):
    o = Order.objects.create(
        code=code or f"O{Order.objects.count():05d}",
        event=event, email="buyer@example.org", status=status, locale="en",
        datetime=now(), expires=now() + datetime.timedelta(days=3),
        total=Decimal("10.00") * qty,
        sales_channel=event.organizer.sales_channels.get(identifier="web"),
    )
    positions = []
    for i in range(qty):
        positions.append(OrderPosition.objects.create(
            order=o, item=item, variation=variation, subevent=subevent,
            price=Decimal("10.00"), positionid=i + 1, **pos_kwargs
        ))
    return o, positions


def _cart(event, item, expires, variation=None, subevent=None, voucher=None, cart_id="c1"):
    return CartPosition.objects.create(
        event=event, item=item, variation=variation, subevent=subevent, voucher=voucher,
        price=Decimal("10.00"), expires=expires, cart_id=cart_id,
    )


def _compute(*quotas, now_dt=None, **kwargs):
    qa = QuotaAvailability(**kwargs)
    qa.queue(*quotas)
    qa.compute(now_dt=now_dt)
    return qa


def _fake_settings(has_redis=False, engine=None):
    return SimpleNamespace(
        HAS_REDIS=has_redis,
        DATABASES={"default": {"ENGINE": engine or django_settings.DATABASES["default"]["ENGINE"]}},
    )


@pytest.fixture
def ev(team_organizer, team_event):
    with scope(organizer=team_organizer):
        yield team_event


@pytest.fixture
def item(ev, team_item):
    return team_item


@pytest.fixture
def quota(ev, item):
    q = Quota.objects.create(event=ev, name="Q", size=5)
    q.items.add(item)
    return q


@pytest.fixture
def fake_redis(monkeypatch):
    """Replace the redis connection + HAS_REDIS flag used inside quotas.py only."""
    r = fakeredis.FakeRedis()
    monkeypatch.setattr(quotas_module, "settings", _fake_settings(has_redis=True))
    monkeypatch.setattr(quotas_module, "django_redis", SimpleNamespace(get_redis_connection=lambda alias: r))
    return r


# =========================================================================== __init__ / queue
@pytest.mark.django_db
class TestInitAndGuards:

    @pytest.mark.parametrize("count_wl, ignore_closed, suffix", [
        (True, False, ""),            # L111 F, L113 F
        (False, False, ":nocw"),      # L111 T
        (True, True, ":igcl"),        # L113 T
        (False, True, ":nocw:igcl"),  # both
    ])
    def test_cache_key_suffix(self, count_wl, ignore_closed, suffix):
        qa = QuotaAvailability(count_waitinglist=count_wl, ignore_closed=ignore_closed)
        assert qa._cache_key_suffix == suffix

    def test_repeatable_read_is_rejected(self, quota, monkeypatch):
        """L126 True -> ValueError (guard: compute must not run under REPEATABLE READ)."""
        monkeypatch.setattr(connection, "tx_in_repeatable_read", True, raising=False)
        qa = QuotaAvailability()
        qa.queue(quota)
        with pytest.raises(ValueError, match="REPEATABLE READ"):
            qa.compute()
        assert qa.results == {}

    def test_repeatable_read_allowed_when_opted_in(self, quota, monkeypatch):
        """L126 False because allow_repeatable_read=True although tx is in REPEATABLE READ."""
        monkeypatch.setattr(connection, "tx_in_repeatable_read", True, raising=False)
        qa = _compute(quota, allow_repeatable_read=True)
        assert qa.results[quota] == (OK, 5)

    def test_empty_queue_returns_without_results(self):
        """L132 True -> early return, nothing computed."""
        qa = QuotaAvailability()
        qa.compute()
        assert qa.results == {}

    def test_grouper_pads_last_chunk(self):
        assert list(grouper("ABCDEFG", 3, "x")) == [("A", "B", "C"), ("D", "E", "F"), ("G", "x", "x")]


# =========================================================================== early outs (L493-500)
@pytest.mark.django_db
class TestEarlyOuts:

    def test_closed_quota_is_ordered(self, quota):
        quota.closed = True
        quota.save()
        assert _compute(quota).results[quota] == (ORDERED, 0)

    def test_closed_quota_ignored_when_ignore_closed(self, quota):
        """closed=True but ignore_closed=True -> falls through to a real count (L495 F via 2nd condition)."""
        quota.closed = True
        quota.save()
        assert _compute(quota, ignore_closed=True).results[quota] == (OK, 5)

    def test_unlimited_quota(self, quota):
        quota.size = None
        quota.save()
        qa = _compute(quota)
        assert qa.results[quota] == (OK, None)
        assert qa.count_paid_orders[quota] == 0  # early_out=True: no DB counting happened

    def test_zero_size_quota_is_gone(self, quota):
        quota.size = 0
        quota.save()
        assert _compute(quota).results[quota] == (GONE, 0)

    def test_early_out_disabled_still_counts_orders(self, ev, item, quota):
        """early_out=False (L236 F): unlimited quota still gets its paid orders counted (cache maintenance)."""
        quota.size = None
        quota.save()
        _order(ev, item, qty=2)
        qa = _compute(quota, early_out=False)
        assert qa.results[quota] == (OK, None)
        assert qa.count_paid_orders[quota] == 2

    def test_full_results_with_early_out_counts_everything(self, ev, item, quota):
        """early_out=True, full_results=True (L237 F) and final loop L291 F (result already known)."""
        quota.size = 0
        quota.save()
        _order(ev, item, qty=1)
        qa = _compute(quota, full_results=True)
        assert qa.results[quota] == (GONE, 0)
        assert qa.count_paid_orders[quota] == 1


# =========================================================================== orders (BR-1 / BR-3)
@pytest.mark.django_db
class TestOrdersBoundary:
    """3-point BVA on the capacity limit (size = 5): sold = 4 / 5 / 6."""

    @pytest.mark.parametrize("sold, expected", [
        (4, (OK, 1)),     # just below the limit
        (5, (GONE, 0)),   # exactly at the limit  (size_left == 0)
        (6, (GONE, 0)),   # just above the limit  (oversold, size_left == -1)
    ])
    def test_paid_orders_bva(self, ev, item, quota, sold, expected):
        _order(ev, item, qty=sold)
        qa = _compute(quota)
        assert qa.results[quota] == expected
        assert qa.count_paid_orders[quota] == sold
        assert quota.cached_availability_paid_orders == sold

    def test_pending_orders_reaching_limit_are_ordered_not_gone(self, ev, item, quota):
        """BR-3: pending (unpaid) orders exhaust the quota with verdict ORDERED (L371), not GONE."""
        _order(ev, item, status=Order.STATUS_PENDING, qty=5)
        qa = _compute(quota)
        assert qa.results[quota] == (ORDERED, 0)
        assert qa.count_pending_orders[quota] == 5
        assert qa.count_paid_orders[quota] == 0

    def test_paid_counted_before_pending(self, ev, item, quota):
        """Lines are sorted so paid ('p') is processed before pending ('n'):
        3 paid + 2 pending -> the limit is reached on a pending line -> ORDERED."""
        _order(ev, item, qty=3)
        _order(ev, item, status=Order.STATUS_PENDING, qty=2)
        qa = _compute(quota)
        assert qa.results[quota] == (ORDERED, 0)
        assert (qa.count_paid_orders[quota], qa.count_pending_orders[quota]) == (3, 2)

    def test_canceled_and_expired_orders_do_not_count(self, ev, item, quota):
        _order(ev, item, status=Order.STATUS_CANCELED, qty=3)
        _order(ev, item, status=Order.STATUS_EXPIRED, qty=3)
        assert _compute(quota).results[quota] == (OK, 5)

    def test_blocked_position_ignored_from_quota(self, ev, item, quota):
        """Positions with ignore_from_quota_while_blocked and a block do not consume capacity."""
        _order(ev, item, qty=2, ignore_from_quota_while_blocked=True, blocked=["admin"])
        _order(ev, item, qty=1, ignore_from_quota_while_blocked=True)  # flag but not blocked -> counts
        assert _compute(quota).results[quota] == (OK, 4)

    def test_variation_order_counts_against_variation_quota(self, ev, item):
        """L352 True: order line with a variation is mapped through _var_to_quotas."""
        var = ItemVariation.objects.create(item=item, value="Red")
        vq = Quota.objects.create(event=ev, name="VarQ", size=3)
        vq.variations.add(var)  # deliberately NOT linked to the parent item
        _order(ev, item, qty=3, variation=var)
        qa = _compute(vq)
        assert qa.results[vq] == (GONE, 0)
        assert qa._item_to_quotas[item.pk] == {vq}  # L264: parent item linked defensively

    def test_release_after_exit_frees_capacity(self, ev, item, quota):
        """release_after_exit=True (L316 T): an exited attendee no longer counts (L363 T)."""
        quota.release_after_exit = True
        quota.save()
        cl = CheckinList.objects.create(event=ev, name="Door", allow_entry_after_exit=False)
        _, (p1,) = _order(ev, item, qty=1)
        _, (p2,) = _order(ev, item, qty=1)
        _, (p3,) = _order(ev, item, qty=1)
        t = now()
        # p1: entered then exited -> released
        Checkin.objects.create(position=p1, list=cl, type=Checkin.TYPE_ENTRY, datetime=t - datetime.timedelta(hours=2))
        Checkin.objects.create(position=p1, list=cl, type=Checkin.TYPE_EXIT, datetime=t - datetime.timedelta(hours=1))
        # p2: exited then re-entered -> still inside, counts
        Checkin.objects.create(position=p2, list=cl, type=Checkin.TYPE_EXIT, datetime=t - datetime.timedelta(hours=2))
        Checkin.objects.create(position=p2, list=cl, type=Checkin.TYPE_ENTRY, datetime=t - datetime.timedelta(hours=1))
        # p3: never checked in -> counts
        qa = _compute(quota)
        assert qa.count_exited_orders[quota] == 1
        assert qa.count_paid_orders[quota] == 3
        assert qa.results[quota] == (OK, 3)

    def test_exited_position_counts_when_quota_does_not_release(self, ev, item, quota):
        """release_after_exit False on this quota but True on another queued quota:
        annotation is computed (L316 T) yet L363 is False for this quota -> exited still counts."""
        other = Quota.objects.create(event=ev, name="Other", size=10, release_after_exit=True)
        other.items.add(item)
        cl = CheckinList.objects.create(event=ev, name="Door", allow_entry_after_exit=False)
        _, (p1,) = _order(ev, item, qty=1)
        t = now()
        Checkin.objects.create(position=p1, list=cl, type=Checkin.TYPE_ENTRY, datetime=t - datetime.timedelta(hours=2))
        Checkin.objects.create(position=p1, list=cl, type=Checkin.TYPE_EXIT, datetime=t - datetime.timedelta(hours=1))
        qa = _compute(quota, other)
        assert qa.results[quota] == (OK, 4)
        assert qa.results[other] == (OK, 10)
        assert qa.count_exited_orders[other] == 1

    def test_exited_orders_beyond_size_never_close_quota(self, ev, item, quota):
        """release_after_exit: 6 sold on size 5 but 2 exited -> 1 left; result decided in final loop (L293)."""
        quota.release_after_exit = True
        quota.save()
        cl = CheckinList.objects.create(event=ev, name="Door", allow_entry_after_exit=False)
        t = now()
        for i in range(6):
            _, (p,) = _order(ev, item, qty=1)
            if i < 2:
                Checkin.objects.create(position=p, list=cl, type=Checkin.TYPE_ENTRY, datetime=t - datetime.timedelta(hours=2))
                Checkin.objects.create(position=p, list=cl, type=Checkin.TYPE_EXIT, datetime=t - datetime.timedelta(hours=1))
        assert _compute(quota).results[quota] == (OK, 1)

    def test_inconclusive_quota_raises(self, ev, item, quota):
        """L295: size_left <= 0 but no rule produced a verdict -> ValueError('inconclusive quota').
        Reachable only with an inconsistent (negative) in-memory size, which PositiveIntegerField
        forbids in the DB; the guard is defensive. We set the size in memory only."""
        quota.size = -1
        with pytest.raises(ValueError, match="inconclusive quota"):
            _compute(quota)


# =========================================================================== series events / subevents
@pytest.fixture
def series(ev, item):
    ev.has_subevents = True
    ev.save()
    se1 = SubEvent.objects.create(event=ev, name="Day 1", date_from=now() + datetime.timedelta(days=10))
    se2 = SubEvent.objects.create(event=ev, name="Day 2", date_from=now() + datetime.timedelta(days=11))
    q1 = Quota.objects.create(event=ev, subevent=se1, name="Q-D1", size=2)
    q2 = Quota.objects.create(event=ev, subevent=se2, name="Q-D2", size=2)
    q1.items.add(item)
    q2.items.add(item)
    return se1, se2, q1, q2


@pytest.mark.django_db
class TestSubevents:
    """No quota without subevent in the batch -> `None in subevents` is False (L301/383/425/468 F).
    Lines for date 1 are skipped for the date-2 quota (q.subevent_id == line.subevent_id is False)."""

    def test_orders_only_count_for_their_date(self, ev, item, series):
        se1, se2, q1, q2 = series
        _order(ev, item, qty=2, subevent=se1)
        qa = _compute(q1, q2)
        assert qa.results[q1] == (GONE, 0)
        assert qa.results[q2] == (OK, 2)

    def test_vouchers_carts_waitinglist_only_count_for_their_date(self, ev, item, series):
        se1, se2, q1, q2 = series
        Voucher.objects.create(event=ev, item=item, subevent=se1, block_quota=True, max_usages=1)
        _cart(ev, item, now() + datetime.timedelta(minutes=10), subevent=se1)
        WaitingListEntry.objects.create(event=ev, item=item, subevent=se1, email="w@example.org")
        qa = _compute(q1, q2)
        assert qa.count_vouchers[q1] == 1 and qa.count_vouchers[q2] == 0
        assert qa.count_cart[q1] == 1 and qa.count_cart[q2] == 0
        assert qa.results[q1] == (RESERVED, 0)
        assert qa.results[q2] == (OK, 2)

    def test_waitinglist_only_counts_for_its_date(self, ev, item, series):
        se1, se2, q1, q2 = series
        WaitingListEntry.objects.create(event=ev, item=item, subevent=se1, email="w1@example.org")
        WaitingListEntry.objects.create(event=ev, item=item, subevent=se1, email="w2@example.org")
        qa = _compute(q1, q2)
        assert qa.results[q1] == (ORDERED, 0)
        assert qa.results[q2] == (OK, 2)
        assert qa.count_waitinglist[q2] == 0


# =========================================================================== vouchers (L373-418)
@pytest.mark.django_db
class TestVouchers:

    def test_item_voucher_blocks_capacity(self, ev, item, quota):
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=3, redeemed=1)
        qa = _compute(quota)
        assert qa.count_vouchers[quota] == 2          # free = max_usages - redeemed
        assert qa.results[quota] == (OK, 3)

    def test_quota_voucher_exhausts_quota(self, ev, item, quota):
        """Voucher bound to the quota itself (item NULL) -> L412 branch; verdict ORDERED (L418)."""
        Voucher.objects.create(event=ev, quota=quota, block_quota=True, max_usages=5)
        qa = _compute(quota)
        assert qa.results[quota] == (ORDERED, 0)

    def test_variation_voucher(self, ev, item):
        var = ItemVariation.objects.create(item=item, value="Blue")
        vq = Quota.objects.create(event=ev, name="VarQ", size=2)
        vq.variations.add(var)
        Voucher.objects.create(event=ev, item=item, variation=var, block_quota=True, max_usages=1)
        qa = _compute(vq)
        assert qa.count_vouchers[vq] == 1
        assert qa.results[vq] == (OK, 1)

    def test_expired_or_non_blocking_vouchers_ignored(self, ev, item, quota):
        Voucher.objects.create(event=ev, item=item, block_quota=False, max_usages=5)
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=5,
                               valid_until=now() - datetime.timedelta(minutes=1))
        assert _compute(quota).results[quota] == (OK, 5)

    def test_fully_redeemed_voucher_blocks_nothing(self, ev, item, quota):
        """free = MAX(max_usages - redeemed, 0): over-redeemed voucher must not ADD capacity."""
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1, redeemed=3)
        qa = _compute(quota)
        assert qa.count_vouchers[quota] == 0
        assert qa.results[quota] == (OK, 5)

    def test_voucher_after_quota_already_decided(self, ev, item, quota):
        """full_results=True: quota already GONE from orders; voucher line is still counted
        but must not overwrite the verdict (L417 F because q in results)."""
        _order(ev, item, qty=5)
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1)
        qa = _compute(quota, full_results=True)
        assert qa.results[quota] == (GONE, 0)
        assert qa.count_vouchers[quota] == 1

    def test_greatest_function_on_non_sqlite_engine(self, ev, item, quota, monkeypatch):
        """L377-378: on PostgreSQL/MySQL the SQL function GREATEST is used instead of MAX.
        We point the module at a non-sqlite ENGINE string and register GREATEST in SQLite."""
        monkeypatch.setattr(quotas_module, "settings", _fake_settings(engine="django.db.backends.postgresql"))
        connection.ensure_connection()
        connection.connection.create_function(
            "GREATEST", -1, lambda *a: None if any(x is None for x in a) else max(a)
        )
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=2, redeemed=5)
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=2)
        qa = _compute(quota)
        assert qa.count_vouchers[quota] == 2
        assert qa.results[quota] == (OK, 3)


# =========================================================================== carts (BR-4, L420-455)
@pytest.mark.django_db
class TestCartsBR4:
    """3-point BVA on the reservation expiry boundary: expires = now - 1s / now / now + 1s.
    Rule in code: CartPosition counts iff expires >= now (L430)."""

    @pytest.mark.parametrize("offset_s, counts", [(-1, False), (0, True), (1, True)])
    def test_cart_expiry_bva(self, ev, item, quota, offset_s, counts):
        t = now()
        _cart(ev, item, t + datetime.timedelta(seconds=offset_s))
        qa = _compute(quota, now_dt=t)
        assert qa.count_cart[quota] == (1 if counts else 0)
        assert qa.results[quota] == (OK, 4 if counts else 5)

    def test_carts_exhaust_quota_reserved(self, ev, item, quota):
        for i in range(5):
            _cart(ev, item, now() + datetime.timedelta(minutes=5), cart_id=f"c{i}")
        qa = _compute(quota)
        assert qa.results[quota] == (RESERVED, 0)
        assert qa.count_cart[quota] == 5

    def test_variation_cart(self, ev, item):
        var = ItemVariation.objects.create(item=item, value="Green")
        vq = Quota.objects.create(event=ev, name="VarQ", size=1)
        vq.variations.add(var)
        _cart(ev, item, now() + datetime.timedelta(minutes=5), variation=var)
        assert _compute(vq).results[vq] == (RESERVED, 0)

    def test_cart_with_blocking_voucher_not_double_counted(self, ev, item, quota):
        """A cart that uses a quota-blocking, still-valid voucher is already counted via the voucher."""
        v = Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1)
        _cart(ev, item, now() + datetime.timedelta(minutes=5), voucher=v)
        qa = _compute(quota)
        assert qa.count_vouchers[quota] == 1
        assert qa.count_cart[quota] == 0
        assert qa.results[quota] == (OK, 4)

    def test_cart_with_non_blocking_or_expired_voucher_counts(self, ev, item, quota):
        v1 = Voucher.objects.create(event=ev, item=item, block_quota=False, max_usages=1)
        v2 = Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1,
                                    valid_until=now() - datetime.timedelta(minutes=1))
        _cart(ev, item, now() + datetime.timedelta(minutes=5), voucher=v1, cart_id="a")
        _cart(ev, item, now() + datetime.timedelta(minutes=5), voucher=v2, cart_id="b")
        qa = _compute(quota)
        assert qa.count_cart[quota] == 2
        assert qa.results[quota] == (OK, 3)

    def test_cart_after_quota_already_decided(self, ev, item, quota):
        """full_results=True: quota GONE from orders, carts still counted, verdict unchanged (L454 F)."""
        _order(ev, item, qty=5)
        _cart(ev, item, now() + datetime.timedelta(minutes=5))
        qa = _compute(quota, full_results=True)
        assert qa.results[quota] == (GONE, 0)
        assert qa.count_cart[quota] == 1


# =========================================================================== waiting list (L457-491)
@pytest.mark.django_db
class TestWaitingList:

    def test_waitinglist_counts_and_exhausts(self, ev, item, quota):
        for i in range(5):
            WaitingListEntry.objects.create(event=ev, item=item, email=f"w{i}@example.org")
        qa = _compute(quota)
        assert qa.count_waitinglist[quota] == 5
        assert qa.results[quota] == (ORDERED, 0)

    def test_waitinglist_ignored_when_count_waitinglist_false(self, ev, item, quota):
        """L282 False: waiting list is not considered at all."""
        WaitingListEntry.objects.create(event=ev, item=item, email="w@example.org")
        qa = _compute(quota, count_waitinglist=False)
        assert qa.results[quota] == (OK, 5)
        assert qa.count_waitinglist[quota] == 0

    def test_waitinglist_entry_with_voucher_not_counted(self, ev, item, quota):
        v = Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1)
        WaitingListEntry.objects.create(event=ev, item=item, email="w@example.org", voucher=v)
        qa = _compute(quota)
        assert qa.count_waitinglist[quota] == 0
        assert qa.count_vouchers[quota] == 1

    def test_variation_waitinglist(self, ev, item):
        var = ItemVariation.objects.create(item=item, value="Gold")
        vq = Quota.objects.create(event=ev, name="VarQ", size=1)
        vq.variations.add(var)
        WaitingListEntry.objects.create(event=ev, item=item, variation=var, email="w@example.org")
        assert _compute(vq).results[vq] == (ORDERED, 0)

    @pytest.mark.parametrize("days, counted", [(1, True), (-1, False)])
    def test_waitinglist_auto_disable(self, ev, item, quota, days, counted):
        """L461: auto-disable date in the future -> list still counted; in the past -> quota filtered out."""
        ev.settings.waiting_list_auto_disable = RelativeDateWrapper(now() + datetime.timedelta(days=days))
        WaitingListEntry.objects.create(event=ev, item=item, email="w@example.org")
        qa = _compute(quota)
        assert qa.count_waitinglist[quota] == (1 if counted else 0)
        assert qa.results[quota] == (OK, 4 if counted else 5)

    def test_waitinglist_after_quota_already_decided(self, ev, item, quota):
        _order(ev, item, qty=5)
        WaitingListEntry.objects.create(event=ev, item=item, email="w@example.org")
        qa = _compute(quota, full_results=True)
        assert qa.results[quota] == (GONE, 0)
        assert qa.count_waitinglist[quota] == 1


# =========================================================================== early returns in _compute
@pytest.mark.django_db
class TestComputeShortCircuits:
    """Each stage removes decided quotas; when none are left the method returns (L240/271/278/286)."""

    def test_return_after_orders(self, ev, item, quota):
        _order(ev, item, qty=5)
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=1)
        qa = _compute(quota)
        assert qa.results[quota] == (GONE, 0)
        assert qa.count_vouchers[quota] == 0  # voucher stage never ran

    def test_return_after_vouchers(self, ev, item, quota):
        Voucher.objects.create(event=ev, item=item, block_quota=True, max_usages=5)
        _cart(ev, item, now() + datetime.timedelta(minutes=5))
        qa = _compute(quota)
        assert qa.results[quota] == (ORDERED, 0)
        assert qa.count_cart[quota] == 0      # cart stage never ran

    def test_return_after_carts(self, ev, item, quota):
        for i in range(5):
            _cart(ev, item, now() + datetime.timedelta(minutes=5), cart_id=f"c{i}")
        WaitingListEntry.objects.create(event=ev, item=item, email="w@example.org")
        qa = _compute(quota)
        assert qa.results[quota] == (RESERVED, 0)
        assert qa.count_waitinglist[quota] == 0  # waiting list stage never ran

    def test_two_quotas_one_decided_early(self, ev, item, quota):
        """L238: one quota decided by early-out, the other one goes through the DB stages."""
        closed = Quota.objects.create(event=ev, name="Closed", size=5, closed=True)
        closed.items.add(item)
        _order(ev, item, qty=2)
        qa = _compute(quota, closed)
        assert qa.results[closed] == (ORDERED, 0)
        assert qa.results[quota] == (OK, 3)
        assert closed not in qa.count_paid_orders


# =========================================================================== plugin signal + auto close
@pytest.mark.django_db
class TestSignalAndClose:

    def test_plugin_signal_overrides_result(self, quota):
        """L168-170: a plugin receiver of `quota_availability` may replace the result."""
        with mock.patch.object(quotas_module.quota_availability, "send",
                               return_value=[(object(), (GONE, 0))]) as send:
            qa = _compute(quota)
        assert qa.results[quota] == (GONE, 0)
        send.assert_called_once()
        assert send.call_args.kwargs["result"] == (OK, 5)  # original result handed to the plugin

    @pytest.mark.parametrize("close_when_sold_out, already_closed, sold, should_close", [
        (True, False, 5, True),    # sold out + flag + open      -> closes and logs
        (True, False, 4, False),   # not sold out                -> stays open
        (False, False, 5, False),  # sold out but no flag        -> stays open
        (True, True, 0, False),    # already closed              -> no second log entry
    ])
    def test_close_when_sold_out(self, ev, item, quota, close_when_sold_out, already_closed, sold, should_close):
        quota.close_when_sold_out = close_when_sold_out
        quota.closed = already_closed
        quota.save()
        if sold:
            _order(ev, item, qty=sold)
        _compute(quota)
        quota.refresh_from_db()
        assert quota.closed is (should_close or already_closed)
        logged = quota.all_logentries().filter(action_type="pretix.event.quota.closed").count()
        assert logged == (1 if should_close else 0)


# =========================================================================== redis cache (L135-159, L175-212)
@pytest.mark.django_db
class TestRedisCache:

    def test_allow_cache_with_full_results_rejected(self, quota):
        qa = QuotaAvailability(full_results=True)
        qa.queue(quota)
        with pytest.raises(ValueError, match="full_results and allow_cache"):
            qa.compute(allow_cache=True)

    def test_allow_cache_without_redis_computes_normally(self, quota, monkeypatch):
        """L139 False: no redis configured -> cache silently skipped."""
        monkeypatch.setattr(quotas_module, "settings", _fake_settings(has_redis=False))
        qa = QuotaAvailability()
        qa.queue(quota)
        qa.compute(allow_cache=True)
        assert qa.results[quota] == (OK, 5)

    def test_compute_writes_cache_and_next_call_reads_it(self, ev, item, quota, fake_redis):
        qa = _compute(quota)
        key = f"quotas:{ev.pk}:availabilitycache"
        raw = fake_redis.hget(key, str(quota.pk)).decode().split(",")
        assert raw[:2] == ["100", "5"]
        assert fake_redis.ttl(key) > 0
        # Sell everything; the fresh cache entry (< 120 s) must still be returned when allow_cache=True
        _order(ev, item, qty=5)
        qa = QuotaAvailability()
        qa.queue(quota)
        qa.compute(allow_cache=True)
        assert qa.results[quota] == (OK, 5)
        assert qa.count_paid_orders[quota] == 0  # served from cache, nothing counted

    def test_cached_unlimited_value_decoded_as_none(self, ev, quota, fake_redis):
        fake_redis.hset(f"quotas:{ev.pk}:availabilitycache", str(quota.pk), f"100,None,{int(time.time())}")
        qa = QuotaAvailability()
        qa.queue(quota)
        qa.compute(allow_cache=True)
        assert qa.results[quota] == (OK, None)

    @pytest.mark.parametrize("stale_allowed, expected", [(False, (OK, 5)), (True, (GONE, 0))])
    def test_stale_cache_entry(self, ev, quota, fake_redis, stale_allowed, expected):
        """Entry older than 120 s is ignored unless allow_cache_stale=True (L151)."""
        fake_redis.hset(f"quotas:{ev.pk}:availabilitycache", str(quota.pk), f"0,0,{int(time.time()) - 500}")
        qa = QuotaAvailability()
        qa.queue(quota)
        qa.compute(allow_cache=True, allow_cache_stale=stale_allowed)
        assert qa.results[quota] == expected

    def test_cache_miss_for_one_quota(self, ev, item, quota, fake_redis):
        """L148: one quota cached, the other is not -> only the missing one is computed."""
        other = Quota.objects.create(event=ev, name="Other", size=7)
        other.items.add(item)
        fake_redis.hset(f"quotas:{ev.pk}:availabilitycache", str(quota.pk), f"10,0,{int(time.time())}")
        qa = QuotaAvailability()
        qa.queue(quota, other)
        qa.compute(allow_cache=True)
        assert qa.results[quota] == (ORDERED, 0)
        assert qa.results[other] == (OK, 7)

    def test_write_lock_prevents_concurrent_cache_write(self, ev, quota, fake_redis):
        """L194: another worker holds the write lock -> this worker does not write."""
        fake_redis.set(f"quotas:availabilitycachewrite:{quota.pk}", "1", ex=10)
        _compute(quota)
        assert fake_redis.hget(f"quotas:{ev.pk}:availabilitycache", str(quota.pk)) is None

    def test_write_cache_with_no_quotas_is_noop(self, fake_redis):
        qa = QuotaAvailability()
        qa._write_cache([], now())
        assert fake_redis.keys() == []

    def test_cache_suffix_used_in_keys(self, ev, quota, fake_redis):
        _compute(quota, count_waitinglist=False, ignore_closed=True)
        assert fake_redis.hget(f"quotas:{ev.pk}:availabilitycache:nocw:igcl", str(quota.pk)) is not None
