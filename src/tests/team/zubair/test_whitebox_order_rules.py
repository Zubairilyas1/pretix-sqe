import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Item, Order, OrderPosition, Quota


@pytest.mark.django_db
class TestWhiteboxOrderStateRules:
    """
    White-Box Unit Test Suite for Business Rule 3 (Order State Machine Transitions).
    Targets: pretix.base.models.orders.Order & Order._can_be_paid
    """

    def test_order_transition_pending_to_paid_allowed(self, team_organizer, team_event, team_item, make_order):
        """Test valid state transition: PENDING order is eligible for payment (returns True)."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PENDING, quantity=2, code='PENDING01')
            assert order.status == Order.STATUS_PENDING
            assert order._can_be_paid() is True

    def test_order_transition_pending_to_canceled_allowed(self, team_organizer, team_event, team_item, make_order):
        """Test valid state transition: PENDING order transitions to CANCELED with timestamp."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PENDING, quantity=1, code='TOCANCEL')
            order.status = Order.STATUS_CANCELED
            order.cancellation_date = now()
            order.save()

            reloaded = Order.objects.get(code='TOCANCEL')
            assert reloaded.status == Order.STATUS_CANCELED
            assert reloaded.cancellation_date is not None

    def test_order_transition_paid_to_refunded_allowed(self, team_organizer, team_event, team_item, make_order):
        """Test valid state transition: PAID order transitions to REFUNDED."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PAID, quantity=1, code='TOPAYANDREF')
            assert order.status == Order.STATUS_PAID

            # Refund order
            order.status = Order.STATUS_REFUNDED
            order.save()

            reloaded = Order.objects.get(code='TOPAYANDREF')
            assert reloaded.status == Order.STATUS_REFUNDED

    def test_order_invalid_transition_canceled_to_paid_rejected(self, team_organizer, team_event, team_item, make_order):
        """Invalid State Transition Guard: CANCELED orders must NOT be payable."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PENDING, quantity=1, code='CANCELED_ORDER')
            order.status = Order.STATUS_CANCELED
            order.cancellation_date = now()
            order.save()

            # Ensure late payments are disabled
            team_event.settings.set('payment_term_accept_late', False)

            # _can_be_paid must NOT return True (returns error message string)
            res = order._can_be_paid()
            assert res is not True
            assert 'no late payments' in str(res).lower()

    def test_order_invalid_transition_refunded_to_paid_rejected(self, team_organizer, team_event, team_item, make_order):
        """Invalid State Transition Guard: REFUNDED orders must NOT be payable."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_REFUNDED, quantity=1, code='REFUNDED_ORDER')

            # Ensure late payments are disabled
            team_event.settings.set('payment_term_accept_late', False)

            res = order._can_be_paid()
            assert res is not True
            assert 'no late payments' in str(res).lower()

    def test_order_unapproved_order_cannot_be_paid(self, team_organizer, team_event, team_item, make_order):
        """Business rule: An order requiring organizer approval cannot be paid until approved."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PENDING, quantity=1, code='NEED_APPROVAL')
            order.require_approval = True
            order.save()

            res = order._can_be_paid()
            assert res is not True
            assert 'not yet approved' in str(res).lower()

    def test_order_force_flag_bypasses_approval_check(self, team_organizer, team_event, team_item, make_order):
        """Test branch coverage: force=True allows paying unapproved orders for admin overrides."""
        with scope(organizer=team_organizer):
            order = make_order(status=Order.STATUS_PENDING, quantity=1, code='FORCE_PAID')
            order.require_approval = True
            order.save()

            # Calling with force=True must bypass require_approval
            assert order._can_be_paid(force=True) is True
