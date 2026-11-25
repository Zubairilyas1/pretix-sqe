import pytest
from django_scopes import scope

from pretix.base.models import Quota


@pytest.mark.django_db
def test_team_fixtures_initialization(team_organizer, team_event, team_item, team_quota):
    """Verify that team fixtures create properly scoped models with expected invariants."""
    assert team_organizer.slug == 'sqe-org'
    assert team_event.slug == 'sqe-conf'
    assert team_item.name == 'General Admission Ticket'
    assert team_item.active is True
    assert team_quota.size == 10

    with scope(organizer=team_organizer):
        assert team_quota.items.count() == 1
        assert team_quota.items.first() == team_item
        # Baseline availability should be AVAILABILITY_OK with 10 tickets
        avail = team_quota.availability()
        assert avail[0] == Quota.AVAILABILITY_OK
        assert avail[1] == 10
