"""
Tests added after the first Cosmic Ray run (docs/sqe/zubair/MUTATION_REPORT.md, section 4).
Each test names the surviving mutant(s) it kills: <line> <operator> <original> -> <mutant>.
"""
import datetime
import time
from decimal import Decimal
from types import SimpleNamespace

import fakeredis
import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import (
    CartPosition, Item, ItemVariation, Order, OrderPosition, Quota, Voucher,
    WaitingListEntry,
)
from pretix.base.services import quotas as quotas_module
from pretix.base.services.quotas import QuotaAvailability

OK, RESERVED, ORDERED, GONE = (
    Quota.AVAILABILITY_OK, Quota.AVAILABILITY_RESERVED, Quota.AVAILABILITY_ORDERED, Quota.AVAILABILITY_GONE,
)


@pytest.fixture
def ev(team_organizer, team_event):
    with scope(organizer=team_organizer):
        yield team_event


@pytest.fixture
def quota(ev, team_item):
    q = Quota.objects.create(event=ev, name="Q", size=5)
    q.items.add(team_item)
    return q


@pytest.fixture
def redis_at(monkeypatch):
    """fakeredis + a frozen clock for quotas.py (time.time() is only used for cache timestamps there)."""
    r = fakeredis.FakeRedis()
    clock = SimpleNamespace(now=1_800_000_000)
    monkeypatch.setattr(quotas_module, "settings", SimpleNamespace(
        HAS_REDIS=True, DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}}))
    monkeypatch.setattr(quotas_module, "django_redis", SimpleNamespace(get_redis_connection=lambda a: r))
    monkeypatch.setattr(quotas_module, "time", SimpleNamespace(time=lambda: clock.now))
    return r, clock


def _order(ev, item, qty, status=Order.STATUS_PAID):
    o = Order.objects.create(
        code=f"K{Order.objects.count():05d}", event=ev, email="k@example.org", status=status, locale="en",
        datetime=now(), expires=now() + datetime.timedelta(days=3), total=Decimal("10") * qty,
        sales_channel=ev.organizer.sales_channels.get(identifier="web"),
    )
    for i in range(qty):
        OrderPosition.objects.create(order=o, item=item, price=Decimal("10"), positionid=i + 1)
    return o


def _cart(ev, item, variation=None, voucher=None, cart_id="c"):
    return CartPosition.objects.create(event=ev, item=item, variation=variation, voucher=voucher, cart_id=cart_id,
                                       price=Decimal("10"), expires=now() + datetime.timedelta(minutes=10))


# ---------------------------------------------------------------- L151 cache age boundary (< 120 -> < 121 / <= 120)
@pytest.mark.django_db
@pytest.mark.parametrize("age, cache_used", [(119, True), (120, False), (121, False)])
def test_cache_age_boundary_bva(ev, quota, redis_at, age, cache_used):
    """3-point BVA on the 120-second cache freshness limit (kills L151 NumberReplacer 120->121)."""
    r, clock = redis_at
    r.hset(f"quotas:{ev.pk}:availabilitycache", str(quota.pk), f"0,0,{clock.now - age}")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute(allow_cache=True)
    assert qa.results[quota] == ((GONE, 0) if cache_used else (OK, 5))


# ---------------------------------------------------------------- L196 / L203-212 exact cache write contract
@pytest.mark.django_db
def test_cache_write_contract(ev, quota, redis_at):
    """Kills L196 ex=10->11/9 and L212 3600*24*7 variants (weak assertion `ttl > 0` before)."""
    r, clock = redis_at
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert r.ttl(f"quotas:availabilitycachewrite:{quota.pk}") == 10
    assert r.ttl(f"quotas:{ev.pk}:availabilitycache") == 7 * 24 * 3600
    assert r.hget(f"quotas:{ev.pk}:availabilitycache", str(quota.pk)).decode() == f"100,5,{clock.now}"


@pytest.mark.django_db
def test_write_lock_name_contains_all_quotas_sorted(ev, team_item, quota, redis_at):
    r, _ = redis_at
    other = Quota.objects.create(event=ev, name="Other", size=3)
    other.items.add(team_item)
    qa = QuotaAvailability()
    qa.queue(other, quota)
    qa.compute()
    a, b = sorted([quota.pk, other.pk])
    assert r.exists(f"quotas:availabilitycachewrite:{a}_{b}")


# ---------------------------------------------------------------- L221 SwapAvailabilityVerdict (custom operator 1)
@pytest.mark.django_db
def test_quota_sold_out_by_pending_orders_is_closed(ev, team_item, quota):
    """Verdict ORDERED (pending orders fill the quota) must also close the quota.
    Kills L221 `<= AVAILABILITY_ORDERED` -> `<= AVAILABILITY_GONE` (found by sqe/SwapAvailabilityVerdict)."""
    quota.close_when_sold_out = True
    quota.save()
    _order(ev, team_item, 5, status=Order.STATUS_PENDING)
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.results[quota] == (ORDERED, 0)
    quota.refresh_from_db()
    assert quota.closed is True


@pytest.mark.django_db
def test_quota_reserved_by_carts_is_not_closed(ev, team_item, quota):
    """RESERVED (only carts) is NOT sold out for `close_when_sold_out` (<= ORDERED is False for 20)."""
    quota.close_when_sold_out = True
    quota.save()
    for i in range(5):
        _cart(ev, team_item, cart_id=f"c{i}")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.results[quota] == (RESERVED, 0)
    quota.refresh_from_db()
    assert quota.closed is False


# ---------------------------------------------------------------- L434 voucher OR-chain (| -> ^)
@pytest.mark.django_db
def test_cart_with_non_blocking_and_expired_voucher_counts(ev, team_item, quota):
    """block_quota=False AND valid_until in the past: both alternatives true; original `|` counts the cart,
    mutant `^` (XOR) would drop it. Kills L434 ReplaceBinaryOperator BitOr->BitXor."""
    v = Voucher.objects.create(event=ev, item=team_item, block_quota=False, max_usages=1,
                               valid_until=now() - datetime.timedelta(minutes=1))
    _cart(ev, team_item, voucher=v)
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.count_cart[quota] == 1
    assert qa.results[quota] == (OK, 4)


# ---------------------------------------------------------------- item / variation filters (& -> |)
@pytest.mark.django_db
def test_carts_orders_waitinglist_of_other_products_are_ignored(ev, team_item, quota):
    """Positions for a product that is NOT in the quota must not consume it.
    Kills `Q(variation_id__isnull=True) & Q(item_id__in=...)` -> `|` in the order, cart and waiting-list filters."""
    other = Item.objects.create(event=ev, name="Other product", default_price=Decimal("5"))
    _order(ev, other, 2)
    _cart(ev, other)
    WaitingListEntry.objects.create(event=ev, item=other, email="o@example.org")
    qa = QuotaAvailability(full_results=True)
    qa.queue(quota)
    qa.compute()
    assert (qa.count_paid_orders[quota], qa.count_cart[quota], qa.count_waitinglist[quota]) == (0, 0, 0)
    assert qa.results[quota] == (OK, 5)


@pytest.mark.django_db
def test_variation_not_in_quota_is_ignored(ev, team_item):
    """Quota holds only variation Red; positions for variation Blue of the same item must not count."""
    red = ItemVariation.objects.create(item=team_item, value="Red")
    blue = ItemVariation.objects.create(item=team_item, value="Blue")
    q = Quota.objects.create(event=ev, name="Red only", size=3)
    q.variations.add(red)
    _cart(ev, team_item, variation=blue)
    WaitingListEntry.objects.create(event=ev, item=team_item, variation=blue, email="b@example.org")
    o = _order(ev, team_item, 0)
    OrderPosition.objects.create(order=o, item=team_item, variation=blue, price=Decimal("10"), positionid=1)
    qa = QuotaAvailability(full_results=True)
    qa.queue(q)
    qa.compute()
    assert (qa.count_paid_orders[q], qa.count_cart[q], qa.count_waitinglist[q]) == (0, 0, 0)
    assert qa.results[q] == (OK, 3)


# ---------------------------------------------------------------- L490 waiting list overshoot (<= 0 -> == 0)
@pytest.mark.django_db
def test_waitinglist_overshooting_capacity(ev, team_item, quota):
    """4 sold + 3 on the waiting list on size 5 -> size_left = -2. Original `<= 0` gives ORDERED;
    mutant `== 0` leaves the quota undecided and raises 'inconclusive quota'."""
    _order(ev, team_item, 4)
    for i in range(3):
        WaitingListEntry.objects.create(event=ev, item=team_item, email=f"w{i}@example.org")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.results[quota] == (ORDERED, 0)
    assert qa.count_waitinglist[quota] == 3


@pytest.mark.django_db
def test_carts_overshooting_capacity(ev, team_item, quota):
    """Same overshoot for carts (L454) and vouchers (L417)."""
    _order(ev, team_item, 4)
    for i in range(3):
        _cart(ev, team_item, cart_id=f"c{i}")
    v_quota = Quota.objects.create(event=ev, name="V", size=1)
    v_quota.items.add(team_item)
    Voucher.objects.create(event=ev, quota=v_quota, block_quota=True, max_usages=3)
    qa = QuotaAvailability()
    qa.queue(quota, v_quota)
    qa.compute()
    assert qa.results[quota] == (RESERVED, 0)
    assert qa.results[v_quota] == (GONE, 0)  # 4 paid already exceed size 1 -> decided by orders


@pytest.mark.django_db
def test_voucher_overshooting_capacity(ev, team_item):
    q = Quota.objects.create(event=ev, name="V", size=2)
    q.items.add(team_item)
    Voucher.objects.create(event=ev, item=team_item, block_quota=True, max_usages=5)
    qa = QuotaAvailability()
    qa.queue(q)
    qa.compute()
    assert qa.results[q] == (ORDERED, 0)
    assert qa.count_vouchers[q] == 5


def test_frozen_clock_fixture_does_not_leak():
    assert abs(quotas_module.time.time() - time.time()) < 5


# ---------------------------------------------------------------- L243 count dictionaries are initialised
@pytest.mark.django_db
def test_counters_initialised_for_computed_quota(quota):
    """Kills L243 ZeroIterationForLoop: every computed quota must appear in the count_* dicts with 0."""
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    for counter in (qa.count_paid_orders, qa.count_pending_orders, qa.count_cart,
                    qa.count_vouchers, qa.count_waitinglist):
        assert dict(counter) == {quota: 0}


# ---------------------------------------------------------------- `==` vs `is` on subevent ids (L357/L414/L451/L487)
@pytest.mark.django_db
def test_subevent_match_uses_value_equality_for_large_ids(ev, team_item):
    """Small ints are cached by CPython, so `q.subevent_id is line['subevent_id']` only differs from `==`
    for ids above 256. Kills the four ReplaceComparisonOperator_Eq_Is mutants."""
    from pretix.base.models import SubEvent
    ev.has_subevents = True
    ev.save()
    se = SubEvent.objects.create(id=50001, event=ev, name="Big id", date_from=now() + datetime.timedelta(days=5))
    q = Quota.objects.create(event=ev, subevent=se, name="Q-big", size=10)
    q.items.add(team_item)
    o = _order(ev, team_item, 0)
    OrderPosition.objects.create(order=o, item=team_item, subevent=se, price=Decimal("10"), positionid=1)
    Voucher.objects.create(event=ev, item=team_item, subevent=se, block_quota=True, max_usages=1)
    CartPosition.objects.create(event=ev, item=team_item, subevent=se, cart_id="big", price=Decimal("10"),
                                expires=now() + datetime.timedelta(minutes=10))
    WaitingListEntry.objects.create(event=ev, item=team_item, subevent=se, email="big@example.org")
    q = Quota.objects.get(pk=q.pk)  # fresh object: subevent_id is a new int, not the one used on creation
    qa = QuotaAvailability(full_results=True)
    qa.queue(q)
    qa.compute()
    assert (qa.count_paid_orders[q], qa.count_vouchers[q], qa.count_cart[q], qa.count_waitinglist[q]) == (1, 1, 1, 1)
    assert qa.results[q] == (OK, 6)


# ---------------------------------------------------------------- voucher item filters (L392, L394)
@pytest.mark.django_db
def test_voucher_for_other_product_is_ignored(ev, team_item, quota):
    """Kills L392 `Q(variation_id__isnull=True) & Q(item_id__in=...)` -> `|`."""
    other = Item.objects.create(event=ev, name="Other product", default_price=Decimal("5"))
    Voucher.objects.create(event=ev, item=other, block_quota=True, max_usages=3)
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.count_vouchers[quota] == 0
    assert qa.results[quota] == (OK, 5)


@pytest.mark.django_db
def test_item_voucher_counts_when_item_is_in_quota_directly_and_via_variation(ev, team_item, quota):
    """Item ids are the UNION of directly linked items and parents of linked variations.
    Kills L394 `|` -> `^` and `|` -> `-` (both drop an item that is in both sets)."""
    var = ItemVariation.objects.create(item=team_item, value="Red")
    quota.variations.add(var)
    Voucher.objects.create(event=ev, item=team_item, block_quota=True, max_usages=2)
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.count_vouchers[quota] == 2
    assert qa.results[quota] == (OK, 3)


# ---------------------------------------------------------------- waiting-list auto-disable boundary (L461)
@pytest.mark.django_db
def test_waitinglist_auto_disable_exact_boundary(ev, team_item, quota, monkeypatch):
    """At the exact auto-disable instant the waiting list is already off (`> now`, strict).
    Kills L461 `>` -> `>=` by freezing quotas.now()."""
    t = now().replace(microsecond=0)
    monkeypatch.setattr(quotas_module, "now", lambda: t)
    from pretix.base.reldate import RelativeDateWrapper
    ev.settings.waiting_list_auto_disable = RelativeDateWrapper(t)
    WaitingListEntry.objects.create(event=ev, item=team_item, email="w@example.org")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute(now_dt=t)
    assert qa.count_waitinglist[quota] == 0
    assert qa.results[quota] == (OK, 5)


@pytest.mark.django_db
def test_waitinglist_auto_disable_relative_to_event_date(ev, team_item, quota):
    """Relative date (1 day before the event start, 30 days away) needs the event as base:
    kills L461 `q.subevent or q.event` -> `and` (would resolve against None)."""
    from pretix.base.reldate import RelativeDate, RelativeDateWrapper
    ev.settings.waiting_list_auto_disable = RelativeDateWrapper(
        RelativeDate(days=1, time=None, base_date_name='event__date_from', minutes=None))
    WaitingListEntry.objects.create(event=ev, item=team_item, email="w@example.org")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.count_waitinglist[quota] == 1
    assert qa.results[quota] == (OK, 4)


# ---------------------------------------------------------------- waiting list leaves exactly one seat (L490 <= 0 -> <= 1)
@pytest.mark.django_db
def test_waitinglist_leaving_one_seat_keeps_quota_available(ev, team_item, quota):
    _order(ev, team_item, 3)
    WaitingListEntry.objects.create(event=ev, item=team_item, email="one@example.org")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute()
    assert qa.results[quota] == (OK, 1)
