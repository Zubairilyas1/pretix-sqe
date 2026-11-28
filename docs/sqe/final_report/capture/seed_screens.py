"""
Starting data for the report screenshots (run with manage.py shell, see capture_pretix.py).

Only the organizer account, the event and the roles are created here. The product and its quota (W1) are created
through the real back-office UI by capture_pretix.py, and orders (W2) through the real shop.
"""
import datetime
from decimal import Decimal

from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import Event, Item, Organizer, Quota, Team, User

with scopes_disabled():
    org, _ = Organizer.objects.get_or_create(slug="sqe-org", defaults={"name": "SQE Events"})
    org.plugins = "pretix.plugins.banktransfer"
    org.save()
    ev, created = Event.objects.get_or_create(
        organizer=org, slug="sqe-conf",
        defaults={"name": "SQE Annual Conference 2026", "currency": "EUR",
                  "date_from": now() + datetime.timedelta(days=45), "location": "Islamabad"},
    )
    ev.live = True
    ev.presale_start = now() - datetime.timedelta(days=1)
    ev.presale_end = now() + datetime.timedelta(days=40)
    ev.plugins = "pretix.plugins.banktransfer"
    ev.save()
    if created:
        ev.set_defaults()
    for k, v in {"locale": "en", "locales": ["en"], "payment_banktransfer__enabled": True,
                 "payment_banktransfer_bank_details_type": "other",
                 "payment_banktransfer_bank_details": "SQE test bank account",
                 "cancel_allow_user": True, "attendee_names_asked": False}.items():
        ev.settings.set(k, v)

    # a second category with exactly one seat, used for the sold-out screen (UC-5)
    vip = next((i for i in Item.objects.filter(event=ev) if str(i.name) == "VIP Ticket"), None)
    if vip is None:
        vip = Item.objects.create(event=ev, name="VIP Ticket", default_price=Decimal("120.00"), position=5)
        q = Quota.objects.create(event=ev, name="VIP Quota", size=1)
        q.items.add(vip)

    organizer = User.objects.filter(email="organizer@sqe.test").first() or \
        User.objects.create_user("organizer@sqe.test", "Sqe-Organizer-2026!", fullname="SQE Organizer")
    t, _ = Team.objects.get_or_create(organizer=org, name="Organizers", defaults={
        "all_events": True, "all_event_permissions": True, "all_organizer_permissions": True})
    t.members.add(organizer)

    viewer = User.objects.filter(email="viewer@sqe.test").first() or \
        User.objects.create_user("viewer@sqe.test", "Sqe-Viewer-2026!", fullname="SQE Viewer")
    vt, _ = Team.objects.get_or_create(organizer=org, name="Viewers (read-only orders)",
                                       defaults={"all_events": True})
    vt.limit_event_permissions = {"event.orders:read": True}
    vt.save()
    vt.members.add(viewer)
    print("seeded", org.slug, ev.slug, "vip item", vip.pk)
