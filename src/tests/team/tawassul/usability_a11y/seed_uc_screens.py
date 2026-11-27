"""
Extra data on the perf instance so that every use case has its key screen (run after seed_perf_event.py):
  UC-4  voucher SQE-VOUCHER-1 (10 % off)               -> /perf-org/perf-conf/redeem?voucher=SQE-VOUCHER-1
  UC-5  product "Sold-out Ticket" with a quota of 0     -> shop page shows it as sold out
  UC-6  a pending order                                 -> /perf-org/perf-conf/order/<code>/<secret>/cancel
Writes the order URL to usability_a11y/reports/uc_screens.json.

    cd src
    set PRETIX_CONFIG_FILE=tests/team/tawassul/performance/perf_pretix.cfg
    ../.venv/Scripts/python manage.py shell -c "exec(open('tests/team/tawassul/usability_a11y/seed_uc_screens.py').read())"
"""
import datetime
import json
from decimal import Decimal
from pathlib import Path

from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import Event, Item, Order, OrderPosition, Quota, Voucher

with scopes_disabled():
    ev = Event.objects.get(organizer__slug="perf-org", slug="perf-conf")
    ticket = Item.objects.filter(event=ev).order_by("pk").first()
    sold_out = next((i for i in Item.objects.filter(event=ev) if str(i.name) == "Sold-out Ticket"), None)
    if sold_out is None:
        sold_out = Item.objects.create(event=ev, name="Sold-out Ticket", default_price=Decimal("20.00"))
        q = Quota.objects.create(event=ev, name="Sold-out quota", size=0)
        q.items.add(sold_out)
    Voucher.objects.get_or_create(event=ev, code="SQE-VOUCHER-1",
                                  defaults={"price_mode": "percent", "value": Decimal("10.00"), "max_usages": 1000})
    order = Order.objects.create(
        event=ev, email="customer@sqe.test", status=Order.STATUS_PENDING, locale="en",
        datetime=now(), expires=now() + datetime.timedelta(days=7), total=Decimal("10.00"),
        sales_channel=ev.organizer.sales_channels.get(identifier="web"),
    )
    OrderPosition.objects.create(order=order, item=ticket, price=Decimal("10.00"), positionid=1)
    ev.settings.cancel_allow_user = True
    out = Path("tests/team/tawassul/usability_a11y/reports/uc_screens.json")
    out.write_text(json.dumps({"order_code": order.code, "order_secret": order.secret}), "utf-8")
    print("uc screens seeded:", order.code)
