"""
Fixtures for Sami's API and integration tests.

Builds on the shared team fixtures in tests/team/conftest.py
(team_organizer, team_event, team_item, team_quota) and adds:

  * organizer_client : API client with a full-permission team token (Role A)
  * readonly_client  : API client whose team may only read orders (limited role)
  * anon_client      : API client without credentials
  * api              : small helper with URL building and read-back functions
  * test_data        : the generator output (test_data.json)
"""
import copy
import json
from pathlib import Path

import pytest
from django_scopes import scopes_disabled
from rest_framework.test import APIClient

from pretix.base.models import Order, Quota, Team

TEST_DATA_PATH = Path(__file__).resolve().parent.parent / "generator" / "test_data.json"


@pytest.fixture(scope="session")
def test_data():
    with open(TEST_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _token_client(team):
    client = APIClient()
    token = team.tokens.create(name=f"sqe-{team.name}")
    client.credentials(HTTP_AUTHORIZATION="Token " + token.token)
    return client


@pytest.fixture
def organizer_client(team_organizer, team_event):
    with scopes_disabled():
        team = Team.objects.create(
            organizer=team_organizer, name="SQE Organizers",
            all_events=True, all_event_permissions=True, all_organizer_permissions=True,
        )
    return _token_client(team)


@pytest.fixture
def readonly_client(team_organizer, team_event):
    with scopes_disabled():
        team = Team.objects.create(
            organizer=team_organizer, name="SQE Read Only",
            all_events=True, all_event_permissions=False, all_organizer_permissions=False,
            limit_event_permissions={"event.orders:read": True},
        )
    return _token_client(team)


@pytest.fixture
def anon_client():
    return APIClient()


class Api:
    """URL builder + read-back helpers so tests read like the workflow."""

    def __init__(self, organizer, event, item):
        self.organizer, self.event, self.item = organizer, event, item
        self.base = f"/api/v1/organizers/{organizer.slug}/events/{event.slug}/"

    # ----- URLs -----
    def url(self, path_template, **kw):
        """Turn a spec path like /organizers/{organizer}/events/{event}/quotas/{quota_id}/ into a URL."""
        path = path_template.replace("{organizer}", self.organizer.slug).replace("{event}", self.event.slug)
        for k, v in kw.items():
            path = path.replace("{" + k + "}", str(v))
        return "/api/v1" + path

    def items(self):
        return self.base + "items/"

    def quotas(self, pk=None):
        return self.base + "quotas/" + (f"{pk}/" if pk else "")

    def carts(self, pk=None):
        return self.base + "cartpositions/" + (f"{pk}/" if pk else "")

    def orders(self, code=None, action=None):
        url = self.base + "orders/"
        if code:
            url += f"{code}/"
        if action:
            url += f"{action}/"
        return url

    # ----- payloads -----
    def fill(self, value):
        """Replace {{item_id}} placeholders from the spec examples."""
        if isinstance(value, dict):
            return {k: self.fill(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.fill(v) for v in value]
        if value == "{{item_id}}":
            return self.item.pk
        return value

    def order_payload(self, n_positions=1, **overrides):
        payload = {
            "email": "buyer@example.org",
            "locale": "en",
            "payment_provider": "manual",
            "send_email": False,
            "positions": [{"item": self.item.pk} for _ in range(n_positions)],
        }
        payload.update(overrides)
        return payload

    # ----- read-back of the shared record -----
    def availability(self, client, quota_id):
        """Full read-back of the shared record: GET quotas/{id}/availability/."""
        r = client.get(self.quotas(quota_id) + "availability/")
        assert r.status_code == 200, r.content
        return r.data

    def available(self, client, quota):
        return self.availability(client, quota.pk)["available_number"]

    def db_available(self, quota):
        with scopes_disabled():
            q = Quota.objects.get(pk=quota.pk)
            return q.availability()[1]

    def order_count(self):
        with scopes_disabled():
            return Order.objects.filter(event=self.event).count()


@pytest.fixture
def api(team_organizer, team_event, team_item, team_quota):
    """team_quota (size 10) is always present so the item is purchasable."""
    return Api(team_organizer, team_event, team_item)


def apply_case(baseline, case):
    """
    Return the baseline payload with exactly one field changed as the case says.
    Supports nested fields written as "name.en".
    """
    payload = copy.deepcopy(baseline)
    *parents, leaf = case["field"].split(".")
    target = payload
    for p in parents:
        target = target.setdefault(p, {})
    kind = case["value_kind"]
    if kind == "missing":
        target.pop(leaf, None)
    elif kind == "array_length":
        template = target[leaf][0]
        target[leaf] = [copy.deepcopy(template) for _ in range(case["value"])]
    else:
        target[leaf] = case["value"]
    return payload
