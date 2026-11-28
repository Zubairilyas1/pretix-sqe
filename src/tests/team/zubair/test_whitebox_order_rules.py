"""
White-box unit tests for ``Order._can_be_paid`` (pretix/base/models/orders.py) - BR-3.

Branches of _can_be_paid (100 % statement + branch coverage target):
  B1 not force                 -> approval / last-date checks       (T: most tests, F: force tests)
  B2 require_approval          -> 'not yet approved'
  B3 term_last and not ignore_date
  B4 now > term_last           -> 'last date of payments ... is over'
  B5 status == PENDING         -> True
  B6 not accept_late and not ignore_date and not force -> 'no late payments'
  B7 otherwise                 -> delegate to _is_still_available()

Note: in pretix STATUS_REFUNDED is a deprecated alias of STATUS_CANCELED ("c").
"""
import datetime

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Order, Quota
from pretix.base.reldate import RelativeDateWrapper


@pytest.fixture
def ctx(team_organizer, team_event, team_item, team_quota):
    with scope(organizer=team_organizer):
        yield team_event


def _set_last_payment_date(event, days_from_now):
    event.settings.payment_term_last = RelativeDateWrapper(now() + datetime.timedelta(days=days_from_now))


@pytest.mark.django_db
class TestWhiteboxOrderStateRules:

    def test_pending_order_can_be_paid(self, ctx, make_order):
        """B1 T, B2 F, B3 F (no last date), B5 T."""
        order = make_order(status=Order.STATUS_PENDING, quantity=2, code='PENDING01')
        assert order._can_be_paid() is True

    def test_unapproved_order_cannot_be_paid(self, ctx, make_order):
        """B2 T."""
        order = make_order(status=Order.STATUS_PENDING, quantity=1, code='NEED_APPROVAL')
        order.require_approval = True
        order.save()
        res = order._can_be_paid()
        assert res is not True
        assert 'not yet approved' in str(res).lower()

    def test_force_bypasses_approval(self, ctx, make_order):
        """B1 F: force=True skips the approval and last-date checks."""
        order = make_order(status=Order.STATUS_PENDING, quantity=1, code='FORCE_PAID')
        order.require_approval = True
        order.save()
        assert order._can_be_paid(force=True) is True

    def test_last_payment_date_passed_rejects(self, ctx, make_order):
        """B3 T, B4 T: the last date of payment is over."""
        _set_last_payment_date(ctx, -2)
        order = make_order(status=Order.STATUS_PENDING, quantity=1, code='LASTDATE1')
        res = order._can_be_paid()
        assert 'last date of payments' in str(res)

    def test_last_payment_date_in_future_accepts(self, ctx, make_order):
        """B3 T, B4 F."""
        _set_last_payment_date(ctx, 2)
        order = make_order(status=Order.STATUS_PENDING, quantity=1, code='LASTDATE2')
        assert order._can_be_paid() is True

    def test_last_payment_date_ignored_with_ignore_date(self, ctx, make_order):
        """B3 F because ignore_date=True although a passed last date exists."""
        _set_last_payment_date(ctx, -2)
        order = make_order(status=Order.STATUS_PENDING, quantity=1, code='LASTDATE3')
        assert order._can_be_paid(ignore_date=True) is True

    def test_canceled_order_rejected_when_late_payments_disabled(self, ctx, make_order):
        """B5 F, B6 T."""
        ctx.settings.set('payment_term_accept_late', False)
        order = make_order(status=Order.STATUS_CANCELED, quantity=1, code='CANCELED_ORDER')
        res = order._can_be_paid()
        assert res is not True
        assert 'no late payments' in str(res).lower()

    def test_expired_order_rejected_when_late_payments_disabled(self, ctx, make_order):
        """B5 F, B6 T for the EXPIRED state."""
        ctx.settings.set('payment_term_accept_late', False)
        order = make_order(status=Order.STATUS_EXPIRED, quantity=1, code='EXPIRED_ORDER')
        assert 'no late payments' in str(order._can_be_paid()).lower()

    def test_expired_order_late_payment_checks_capacity(self, ctx, make_order):
        """B6 F (late payments accepted) -> B7: real _is_still_available() decides; capacity free -> True."""
        ctx.settings.set('payment_term_accept_late', True)
        order = make_order(status=Order.STATUS_EXPIRED, quantity=1, code='EXPIRED_OK')
        assert order._can_be_paid() is True

    def test_expired_order_late_payment_rejected_when_sold_out(self, ctx, team_quota, make_order):
        """B7 with exhausted capacity -> 'no longer available' message from _is_still_available()."""
        ctx.settings.set('payment_term_accept_late', True)
        order = make_order(status=Order.STATUS_EXPIRED, quantity=1, code='EXPIRED_NO')
        make_order(status=Order.STATUS_PAID, quantity=10, code='SOLDOUT')
        assert team_quota.availability()[0] == Quota.AVAILABILITY_GONE
        res = order._can_be_paid()
        assert res is not True
        assert 'no longer available' in str(res)
