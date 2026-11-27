"""
Reset the perf instance to identical starting data before every k6 run.

    cd src
    set PRETIX_CONFIG_FILE=tests/team/tawassul/performance/perf_pretix.cfg
    ../.venv/Scripts/python manage.py shell -c "exec(open('tests/team/tawassul/performance/seed_perf_event.py').read())"

Creates organizer ``perf-org``, event ``perf-conf`` (live, bank transfer and
manual payment), item "Perf Ticket" 10.00 with a quota of 1 000 000 seats, and a
team API token written to ``.perf_token`` (git-ignored). Any orders and carts
from an earlier run are deleted, so every run starts from the same state.
"""
import datetime
from decimal import Decimal
from pathlib import Path

from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import (
    CartPosition, Event, Item, Order, Organizer, Quota, Team, User,
)

TOKEN_FILE = Path("tests/team/tawassul/performance/.perf_token")

with scopes_disabled():
    org, _ = Organizer.objects.get_or_create(slug="perf-org", defaults={"name": "Perf Organizer"})
    org.plugins = "pretix.plugins.banktransfer"
    org.save()
    ev, created = Event.objects.get_or_create(
        organizer=org, slug="perf-conf",
        defaults={"name": "Perf Conference", "currency": "EUR",
                  "date_from": now() + datetime.timedelta(days=60)},
    )
    ev.live = True
    ev.presale_start = None
    ev.presale_end = None
    ev.plugins = "pretix.plugins.banktransfer"
    ev.save()
    if created:
        ev.set_defaults()
    ev.settings.set("payment_banktransfer__enabled", True)
    ev.settings.set("payment_banktransfer_bank_details_type", "other")
    ev.settings.set("payment_banktransfer_bank_details", "perf test")

    # identical starting data: wipe everything a previous run created
    deleted_orders = 0
    for o in Order.objects.filter(event=ev):
        o.all_positions.all().delete()
        o.payments.all().delete()
        o.fees.all().delete()
        o.transactions.all().delete()
        o.delete()
        deleted_orders += 1
    CartPosition.objects.filter(event=ev).delete()

    item = Item.objects.filter(event=ev).first() or Item.objects.create(
        event=ev, name="Perf Ticket", default_price=Decimal("10.00"))
    quota = Quota.objects.filter(event=ev).first() or Quota.objects.create(event=ev, name="Perf quota", size=1)
    quota.size = 1_000_000
    quota.save()
    quota.items.set([item])

    team, _ = Team.objects.get_or_create(organizer=org, name="perf-api",
                                         defaults={"all_events": True, "all_event_permissions": True})
    # back-office login used for the Lighthouse / ZAP runs on the organizer pages
    admin = User.objects.filter(email="organizer@sqe.test").first()
    if admin is None:
        admin = User.objects.create_user("organizer@sqe.test", "Sqe-Organizer-2026!")
    team.members.add(admin)

    token = team.tokens.filter(active=True).first() or team.tokens.create(name="k6")
    TOKEN_FILE.write_text(token.token)

    print(f"seeded: event={org.slug}/{ev.slug} item={item.pk} quota={quota.pk} size={quota.size} "
          f"deleted_orders={deleted_orders}")
