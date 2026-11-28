"""
Regression test for defect D-Z01 (found by white-box review of quotas.py, Area 1):
QuotaAvailability.compute(now_dt=...) evaluates vouchers and carts at ``now_dt`` but decides whether the
waiting list is still active with the real ``now()`` (quotas.py L461). Availability computed for another
point in time (time machine, cart service) therefore counts or ignores waiting-list entries wrongly.
"""
import datetime

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Quota, WaitingListEntry
from pretix.base.reldate import RelativeDateWrapper
from pretix.base.services.quotas import QuotaAvailability


@pytest.fixture
def quota(team_organizer, team_event, team_item):
    with scope(organizer=team_organizer):
        q = Quota.objects.create(event=team_event, name="Q", size=5)
        q.items.add(team_item)
        yield q


@pytest.mark.django_db
@pytest.mark.parametrize("compute_at_days, wl_counted", [
    (0, True),    # computed now: waiting list disabled only tomorrow -> still counted
    (2, False),   # computed for the day after tomorrow: waiting list already disabled -> must not count
])
def test_dz01_waitinglist_auto_disable_uses_now_dt(team_event, team_item, quota, compute_at_days, wl_counted):
    team_event.settings.waiting_list_auto_disable = RelativeDateWrapper(now() + datetime.timedelta(days=1))
    WaitingListEntry.objects.create(event=team_event, item=team_item, email="w@example.org")
    qa = QuotaAvailability()
    qa.queue(quota)
    qa.compute(now_dt=now() + datetime.timedelta(days=compute_at_days))
    assert qa.count_waitinglist[quota] == (1 if wl_counted else 0)
    assert qa.results[quota] == (Quota.AVAILABILITY_OK, 4 if wl_counted else 5)
