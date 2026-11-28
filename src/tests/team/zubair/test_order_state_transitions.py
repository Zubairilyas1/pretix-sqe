"""
BR-3 State-transition testing of the pretix order life cycle through the REAL service
functions (no direct ``order.status = ...`` writes).

States: PENDING (n), PAID (p), EXPIRED (e), CANCELED (c).

Allowed transitions tested (each also reads back the shared Quota record):
  T1 n -> p   OrderPayment.confirm()
  T2 n -> e   mark_order_expired()
  T3 n -> c   _cancel_order()
  T4 p -> c   _cancel_order()
  T5 e -> p   OrderPayment.confirm()   (late payment, capacity still free)
  T6 e -> c   _cancel_order()
  T7 c -> n   reactivate_order()
  T8 n(approval) -> n   approve_order()

Disallowed transitions (at least one from every state):
  X1 n -> c->n  reactivate a PENDING order         -> OrderError
  X2 p -> approve a PAID order                     -> OrderError
  X3 e -> p   late payment when the quota is gone  -> Quota.QuotaExceededException, stays EXPIRED
  X4 c -> c   cancel a CANCELED order              -> OrderError
  X5 c -> p   confirm a payment on a CANCELED order -> order stays CANCELED
  X6 n -> p   pay an order that still needs approval -> rejected, stays PENDING
"""
import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Order, OrderPayment, OrderPosition, Quota
from pretix.base.services.orders import (
    OrderError, _cancel_order, approve_order, mark_order_expired,
    reactivate_order,
)

OK, GONE, ORDERED = Quota.AVAILABILITY_OK, Quota.AVAILABILITY_GONE, Quota.AVAILABILITY_ORDERED


@pytest.fixture
def env(team_organizer, team_event, team_item):
    with scope(organizer=team_organizer):
        q = Quota.objects.create(event=team_event, name="Q", size=2)
        q.items.add(team_item)
        yield team_event, team_item, q


def _order(event, item, status=Order.STATUS_PENDING, qty=1, require_approval=False):
    o = Order.objects.create(
        code=f"ST{Order.objects.count():04d}", event=event, email="s@example.org", status=status, locale="en",
        datetime=now(), expires=now() + datetime.timedelta(days=3), total=Decimal("50.00") * qty,
        require_approval=require_approval,
        sales_channel=event.organizer.sales_channels.get(identifier="web"),
    )
    for i in range(qty):
        OrderPosition.objects.create(order=o, item=item, price=Decimal("50.00"), positionid=i + 1)
    return o


def _pay(order):
    p = order.payments.create(provider="manual", amount=order.total, state=OrderPayment.PAYMENT_STATE_CREATED)
    p.confirm(send_mail=False)
    order.refresh_from_db()
    return p


# =========================================================================== allowed
@pytest.mark.django_db
class TestAllowedTransitions:

    def test_t1_pending_to_paid(self, env):
        ev, item, q = env
        o = _order(ev, item)
        _pay(o)
        assert o.status == Order.STATUS_PAID
        assert q.availability() == (OK, 1)
        assert o.all_logentries().filter(action_type="pretix.event.order.paid").exists()

    def test_t2_pending_to_expired_releases_capacity(self, env):
        ev, item, q = env
        o = _order(ev, item, qty=2)
        assert q.availability() == (ORDERED, 0)
        mark_order_expired(o)
        o.refresh_from_db()
        assert o.status == Order.STATUS_EXPIRED
        assert q.availability() == (OK, 2)

    def test_t3_pending_to_canceled(self, env):
        ev, item, q = env
        o = _order(ev, item)
        _cancel_order(o.pk, send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_CANCELED
        assert o.cancellation_date is not None
        assert q.availability() == (OK, 2)

    def test_t4_paid_to_canceled(self, env):
        ev, item, q = env
        o = _order(ev, item, status=Order.STATUS_PAID, qty=2)
        assert q.availability() == (GONE, 0)
        _cancel_order(o.pk, send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_CANCELED
        assert q.availability() == (OK, 2)

    def test_t5_expired_to_paid_when_capacity_free(self, env):
        ev, item, q = env
        o = _order(ev, item)
        mark_order_expired(o)
        _pay(o)
        assert o.status == Order.STATUS_PAID
        assert q.availability() == (OK, 1)

    def test_t6_expired_to_canceled(self, env):
        ev, item, q = env
        o = _order(ev, item)
        mark_order_expired(o)
        _cancel_order(o.pk, send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_CANCELED

    def test_t7_canceled_reactivated_to_pending(self, env):
        ev, item, q = env
        o = _order(ev, item)
        _cancel_order(o.pk, send_mail=False)
        o.refresh_from_db()
        reactivate_order(o)
        o.refresh_from_db()
        assert o.status == Order.STATUS_PENDING
        assert o.cancellation_date is None
        assert q.availability() == (OK, 1)

    def test_t8_approve_pending_order(self, env):
        ev, item, q = env
        o = _order(ev, item, require_approval=True)
        approve_order(o, send_mail=False)
        o.refresh_from_db()
        assert o.require_approval is False
        assert o.status == Order.STATUS_PENDING
        assert o._can_be_paid() is True


# =========================================================================== disallowed
@pytest.mark.django_db
class TestDisallowedTransitions:

    def test_x1_reactivate_pending_rejected(self, env):
        ev, item, q = env
        o = _order(ev, item)
        with pytest.raises(OrderError, match="not canceled"):
            reactivate_order(o)
        o.refresh_from_db()
        assert o.status == Order.STATUS_PENDING

    def test_x2_approve_paid_rejected(self, env):
        ev, item, q = env
        o = _order(ev, item, status=Order.STATUS_PAID)
        with pytest.raises(OrderError, match="not pending approval"):
            approve_order(o, send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_PAID

    def test_x3_expired_to_paid_rejected_when_quota_gone(self, env):
        ev, item, q = env
        o = _order(ev, item)
        mark_order_expired(o)
        _order(ev, item, status=Order.STATUS_PAID, qty=2)  # someone else bought the remaining capacity
        p = o.payments.create(provider="manual", amount=o.total)
        with pytest.raises(Quota.QuotaExceededException):
            p.confirm(send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_EXPIRED
        assert q.availability() == (GONE, 0)  # no oversell

    def test_x4_cancel_canceled_rejected(self, env):
        ev, item, q = env
        o = _order(ev, item)
        _cancel_order(o.pk, send_mail=False)
        with pytest.raises(OrderError, match="cannot cancel"):
            _cancel_order(o.pk, send_mail=False)

    def test_x5_payment_on_canceled_order_does_not_revive_it(self, env):
        ev, item, q = env
        o = _order(ev, item)
        _cancel_order(o.pk, send_mail=False)
        o.refresh_from_db()
        p = o.payments.create(provider="manual", amount=o.total)
        p.confirm(send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_CANCELED
        assert q.availability() == (OK, 2)

    def test_x6_unapproved_order_cannot_be_paid(self, env):
        ev, item, q = env
        o = _order(ev, item, require_approval=True)
        p = o.payments.create(provider="manual", amount=o.total)
        with pytest.raises(Quota.QuotaExceededException, match="not yet approved"):
            p.confirm(send_mail=False)
        o.refresh_from_db()
        assert o.status == Order.STATUS_PENDING
