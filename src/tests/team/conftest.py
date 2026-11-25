import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import (
    CartPosition, Event, Item, ItemVariation, Order, OrderPosition, Organizer,
    Quota,
)


@pytest.fixture
def team_organizer(db):
    """Fixture providing a dedicated organizer for team test execution."""
    return Organizer.objects.create(name='SQE Team Organizer', slug='sqe-org')


@pytest.fixture
def team_event(team_organizer):
    """Fixture providing an active event scoped to team_organizer."""
    with scope(organizer=team_organizer):
        event = Event.objects.create(
            organizer=team_organizer,
            name='SQE Annual Conference',
            slug='sqe-conf',
            date_from=now() + datetime.timedelta(days=30),
            date_to=now() + datetime.timedelta(days=32),
            plugins='pretix.plugins.banktransfer'
        )
        return event


@pytest.fixture
def team_item(team_organizer, team_event):
    """Fixture providing an active ticket Item linked to team_event."""
    with scope(organizer=team_organizer):
        item = Item.objects.create(
            event=team_event,
            name='General Admission Ticket',
            default_price=Decimal('50.00'),
            active=True
        )
        return item


@pytest.fixture
def team_quota(team_organizer, team_event, team_item):
    """Fixture providing a Quota of size 10 linked to team_item."""
    with scope(organizer=team_organizer):
        quota = Quota.objects.create(
            event=team_event,
            name='Main Stage Quota',
            size=10
        )
        quota.items.add(team_item)
        return quota


@pytest.fixture
def make_order(team_organizer, team_event, team_item):
    """Factory fixture to create sample Orders with positions in different states."""
    def _maker(status=Order.STATUS_PENDING, quantity=1, price=Decimal('50.00'), code='SQE01'):
        with scope(organizer=team_organizer):
            order = Order.objects.create(
                code=code,
                event=team_event,
                email='attendee@example.com',
                status=status,
                locale='en',
                datetime=now(),
                expires=now() + datetime.timedelta(days=3),
                total=price * quantity,
                sales_channel=team_event.organizer.sales_channels.get(identifier="web")
            )
            for i in range(quantity):
                OrderPosition.objects.create(
                    order=order,
                    item=team_item,
                    price=price,
                    positionid=i + 1
                )
            return order
    return _maker


@pytest.fixture
def make_cart_position(team_organizer, team_event, team_item):
    """Factory fixture to create CartPositions simulating active/expired cart reservations."""
    def _maker(cart_id='test-session-123', dt=None):
        with scope(organizer=team_organizer):
            return CartPosition.objects.create(
                event=team_event,
                item=team_item,
                price=team_item.default_price,
                expires=dt or (now() + datetime.timedelta(minutes=30)),
                cart_id=cart_id
            )
    return _maker
