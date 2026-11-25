import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import CartPosition, Item, Quota
from pretix.base.services.cart import (
    CartError, clear_cart, extend_cart_reservation, remove_cart_position,
)


@pytest.mark.django_db
class TestWhiteboxCartRules:
    """
    White-Box Unit Test Suite for Business Rule 4 (Cart Reservation Expiration & Quota Management).
    Targets: CartPosition, QuotaAvailability._compute_carts, and services/cart operations.
    """

    def test_active_cart_reservation_locks_quota_slot(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Active cart positions hold a reservation lock, decrementing available quota."""
        with scope(organizer=team_organizer):
            # Quota starts with 10 available
            assert team_quota.availability()[1] == 10

            # User adds 3 tickets to cart with 30 min expiration
            make_cart_position(cart_id='active-session-1')
            make_cart_position(cart_id='active-session-1')
            make_cart_position(cart_id='active-session-1')

            # Remaining quota must be exactly 7
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 7

    def test_expired_cart_reservation_releases_quota_immediately(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Cart positions that pass their expiration timestamp must immediately release quota."""
        with scope(organizer=team_organizer):
            # Add 2 items that expired 10 minutes ago
            make_cart_position(cart_id='expired-session', dt=now() - datetime.timedelta(minutes=10))
            make_cart_position(cart_id='expired-session', dt=now() - datetime.timedelta(minutes=10))

            # Since carts expired, quota availability should still be the full 10
            avail = team_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_OK
            assert avail[1] == 10

    def test_clear_cart_releases_all_reserved_quota(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Invoking clear_cart deletes cart positions and frees all held quota."""
        with scope(organizer=team_organizer):
            cart_id = 'user-cart-to-clear'
            make_cart_position(cart_id=cart_id)
            make_cart_position(cart_id=cart_id)
            assert team_quota.availability()[1] == 8

            # Clear cart (Celery task expects event.pk)
            clear_cart.apply(args=(team_event.pk, cart_id))

            # Cart positions deleted & quota restored to 10
            assert CartPosition.objects.filter(cart_id=cart_id).count() == 0
            assert team_quota.availability()[1] == 10

    def test_remove_single_cart_item_partially_restores_quota(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Removing one item from a cart of 3 positions frees exactly 1 slot."""
        with scope(organizer=team_organizer):
            cart_id = 'partial-cart'
            cp1 = make_cart_position(cart_id=cart_id)
            cp2 = make_cart_position(cart_id=cart_id)
            cp3 = make_cart_position(cart_id=cart_id)
            assert team_quota.availability()[1] == 7

            # Remove position 1 (Celery task expects event.pk)
            remove_cart_position.apply(args=(team_event.pk, cp1.pk, cart_id))

            # 2 remaining positions -> available quota is now 8
            assert CartPosition.objects.filter(cart_id=cart_id).count() == 2
            assert team_quota.availability()[1] == 8

    def test_extend_cart_reservation_pushes_expiry_forward(
        self, team_organizer, team_event, team_item, team_quota, make_cart_position
    ):
        """Extending a cart reservation pushes the expires timestamp forward."""
        with scope(organizer=team_organizer):
            cart_id = 'extend-session'
            initial_expiry = now() + datetime.timedelta(minutes=5)
            cp = make_cart_position(cart_id=cart_id, dt=initial_expiry)

            # Extend reservation (Celery task expects event.pk)
            extend_cart_reservation.apply(args=(team_event.pk, cart_id))

            cp.refresh_from_db()
            assert cp.expires > initial_expiry

    def test_competing_carts_quota_exhaustion_boundary(
        self, team_organizer, team_event, team_item, make_cart_position
    ):
        """Boundary test: With only 1 ticket left in quota, cart reservation flips status to AVAILABILITY_RESERVED (20)."""
        with scope(organizer=team_organizer):
            tight_quota = Quota.objects.create(event=team_event, name='Tight Quota', size=1)
            tight_quota.items.add(team_item)

            # Cart A claims the single remaining ticket
            make_cart_position(cart_id='cart-a')

            # Quota is held in cart -> status is AVAILABILITY_RESERVED (20), available count is 0
            avail = tight_quota.availability()
            assert avail[0] == Quota.AVAILABILITY_RESERVED
            assert avail[1] == 0
