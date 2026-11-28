import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Item, Order, OrderPosition, Quota


@pytest.mark.django_db
class TestWhiteboxQuotaRules:
    """
    White-Box Unit Test Suite for Business Rule 1 (Quota Capacity & Numerical Boundary Invariants).
    Targets: pretix.base.models.items.Quota & pretix.base.services.quotas.QuotaAvailability
    """

    def test_quota_unlimited_capacity(self, team_organizer, team_event, team_item):
        """Boundary test: Quota with size=None must return AVAILABILITY_OK with infinite (None) count."""
        with scope(organizer=team_organizer):
            unlimited_quota = Quota.objects.create(
                event=team_event,
                name='Unlimited Tier',
                size=None
            )
            unlimited_quota.items.add(team_item)

            avail = unlimited_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] is None

    def test_quota_partial_consumption_boundary(self, team_organizer, team_event, team_item, team_quota, make_order):
        """Boundary test: 4 sold tickets against a quota of 10 must leave exactly 6 available."""
        with scope(organizer=team_organizer):
            # Baseline is 10
            assert team_quota.availability()[1] == 10

            # Create paid order for 4 items
            make_order(status=Order.STATUS_PAID, quantity=4, code='ORDER01')

            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 6

    def test_quota_exact_capacity_reached(self, team_organizer, team_event, team_item, team_quota, make_order):
        """Boundary test: When sold tickets equal quota size exactly, status must flip to AVAILABILITY_GONE (0 available)."""
        with scope(organizer=team_organizer):
            # Sell all 10 tickets
            make_order(status=Order.STATUS_PAID, quantity=10, code='ORDERFULL')

            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_GONE
            assert avail[1] == 0

    def test_quota_active_cart_reservation_consumes_slots(
        self, team_organizer, team_event, team_item, team_quota, make_order, make_cart_position
    ):
        """Test interaction between orders and active cart reservations."""
        with scope(organizer=team_organizer):
            # 3 tickets purchased via paid order
            make_order(status=Order.STATUS_PAID, quantity=3, code='PAID03')

            # 2 tickets held in active cart reservations (expires in 30 minutes)
            make_cart_position(cart_id='cart-session-1')
            make_cart_position(cart_id='cart-session-2')

            # Remaining must be 10 - 3 - 2 = 5
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 5

    def test_quota_expired_cart_reservation_ignored(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Boundary test: Cart positions that have expired must NOT consume available quota."""
        with scope(organizer=team_organizer):
            # Active cart position (expires in 20 mins)
            make_cart_position(cart_id='active-cart', dt=now() + datetime.timedelta(minutes=20))

            # Expired cart position (expired 5 minutes ago)
            make_cart_position(cart_id='expired-cart', dt=now() - datetime.timedelta(minutes=5))

            # Only 1 slot should be deducted -> 10 - 1 = 9
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 9

    def test_quota_closed_status_immediately_ordered(self, team_organizer, team_event, team_item, team_quota):
        """Test that setting closed=True renders the quota AVAILABILITY_ORDERED with 0 available."""
        with scope(organizer=team_organizer):
            team_quota.closed = True
            team_quota.save()

            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_ORDERED
            assert avail[1] == 0

    def test_quota_shared_across_multiple_items(self, team_organizer, team_event, team_item, team_quota, make_order):
        """Test cross-item shared quota: 2 distinct items sharing 1 quota deplete the same pool."""
        with scope(organizer=team_organizer):
            vip_item = Item.objects.create(
                event=team_event,
                name='VIP Ticket',
                default_price=Decimal('150.00'),
                active=True
            )
            team_quota.items.add(vip_item)

            # Purchase 6 General tickets
            make_order(status=Order.STATUS_PAID, quantity=6, code='GEN06')

            # Purchase 4 VIP tickets
            order_vip = Order.objects.create(
                code='VIP04',
                event=team_event,
                email='vip@example.com',
                status=Order.STATUS_PAID,
                locale='en',
                datetime=now(),
                expires=now() + datetime.timedelta(days=3),
                total=Decimal('600.00'),
                sales_channel=team_event.organizer.sales_channels.get(identifier="web")
            )
            for i in range(4):
                OrderPosition.objects.create(
                    order=order_vip,
                    item=vip_item,
                    price=Decimal('150.00'),
                    positionid=i + 1
                )

            # Total consumed = 6 + 4 = 10 -> Quota must now be exhausted
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_GONE
            assert avail[1] == 0

    def test_quota_canceled_order_releases_capacity(
        self, team_organizer, team_event, team_item, team_quota, make_order
    ):
        """Test state release invariant: Canceled orders must free up their allocated quota slots."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PAID, quantity=5, code='TO_CANCEL')
            assert team_quota.availability()[1] == 5

            # Transition order to CANCELED
            order.status = Order.STATUS_CANCELED
            order.cancellation_date = now()
            order.save()

            # Quota must rebound back to 10
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 10
