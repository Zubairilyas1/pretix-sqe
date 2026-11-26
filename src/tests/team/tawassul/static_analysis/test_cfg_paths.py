"""
Basis-path tests for ``Quota.availability()`` (see ``cfg_cyclomatic.md``).

One test per feasible path P1..P5 of the hand-drawn control flow graph.
Together they cover all 16 edges, including both outcomes of each
short-circuit condition (D1/D2 and D3/D4).
"""
import pytest
from django_scopes import scope

from pretix.base.models import Quota

pytestmark = pytest.mark.django_db(transaction=True)  # same mode as the live-server tests in this folder

AVAILABLE = (Quota.AVAILABILITY_OK, 10)


@pytest.fixture
def quota(team_organizer, team_quota):
    with scope(organizer=team_organizer):
        yield team_quota


def test_p1_no_cache_computes_and_returns(quota):
    # D1 F (None is falsy), D3 F, D5 F
    assert quota.availability(_cache=None) == AVAILABLE


def test_p2_empty_cache_is_filled(quota):
    # D1 F ({} is falsy), D3 T, D4 F, D5 T -> result stored
    cache = {}
    assert quota.availability(_cache=cache) == AVAILABLE
    assert cache[quota.pk] == AVAILABLE
    assert cache["_count_waitinglist"] is True


def test_p3_cached_value_is_returned_without_query(quota, django_assert_num_queries):
    # D1 T, D2 F, D3 T, D4 T -> early return, no database access at all
    sentinel = (Quota.AVAILABILITY_GONE, 0)
    cache = {quota.pk: sentinel, "_count_waitinglist": True}
    with django_assert_num_queries(0):
        assert quota.availability(_cache=cache) == sentinel


def test_p4_flag_change_clears_stale_cache(quota):
    # D1 T, D2 T -> clear, D3 T, D4 F, D5 T: a value computed under the other
    # waiting-list rule must not be reused (it could sell a seat that is gone)
    stale = (Quota.AVAILABILITY_GONE, 0)
    cache = {quota.pk: stale, 999999: stale, "_count_waitinglist": True}
    assert quota.availability(count_waitinglist=False, _cache=cache) == AVAILABLE
    assert 999999 not in cache                      # whole cache was cleared
    assert cache == {quota.pk: AVAILABLE, "_count_waitinglist": False}


def test_p5_cache_without_this_quota_is_extended(quota):
    # D1 T, D2 F, D3 T, D4 F, D5 T
    other = (Quota.AVAILABILITY_OK, 3)
    cache = {999999: other, "_count_waitinglist": True}
    assert quota.availability(_cache=cache) == AVAILABLE
    assert cache[999999] == other                   # unrelated entry kept
    assert cache[quota.pk] == AVAILABLE
