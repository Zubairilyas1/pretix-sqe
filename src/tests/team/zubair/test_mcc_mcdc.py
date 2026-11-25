import datetime
from decimal import Decimal

import pytest
from django.utils.timezone import now
from django_scopes import scope

from pretix.base.models import Item, Quota


def evaluate_purchasability(item: Item, quota: Quota, now_dt: datetime) -> bool:
    """
    Evaluates the compound Boolean decision for Business Rule 2:
    Decision D = A (active) and B (from_valid) and C (until_valid) and D_quota (quota_available)
    """
    cond_a = item.active
    cond_b = item.available_from is None or item.available_from <= now_dt
    cond_c = item.available_until is None or now_dt <= item.available_until
    avail = quota.availability(now_dt=now_dt)
    cond_d = avail[0] == Quota.AVAILABILITY_OK and (avail[1] is None or avail[1] > 0)
    return bool(cond_a and cond_b and cond_c and cond_d)


@pytest.mark.django_db
class TestMCCAndMCDCPurchasability:
    """
    Multiple Condition Coverage (MCC) and Modified Condition/Decision Coverage (MC/DC)
    Test Suite for Business Rule 2 (Item Purchasability Decision).
    Decision D = A and B and C and D_quota
    Number of conditions n = 4 -> Total MCC combinations = 2^4 = 16.
    Required MC/DC tests = n + 1 = 5 tests.
    """

    # Complete 16-Row MCC Truth Table Test Data
    # Format: (Row_ID, A_active, B_from_valid, C_until_valid, D_quota_stock, Expected_Outcome)
    MCC_TRUTH_TABLE = [
        (1, True, True, True, True, True),       # Row 1: All True -> TRUE
        (2, True, True, True, False, False),     # Row 2: Quota out -> FALSE (MC/DC Pair D with Row 1)
        (3, True, True, False, True, False),     # Row 3: Sales ended -> FALSE (MC/DC Pair C with Row 1)
        (4, True, True, False, False, False),    # Row 4
        (5, True, False, True, True, False),     # Row 5: Sales not started -> FALSE (MC/DC Pair B with Row 1)
        (6, True, False, True, False, False),    # Row 6
        (7, True, False, False, True, False),    # Row 7
        (8, True, False, False, False, False),   # Row 8
        (9, False, True, True, True, False),     # Row 9: Item inactive -> FALSE (MC/DC Pair A with Row 1)
        (10, False, True, True, False, False),   # Row 10
        (11, False, True, False, True, False),   # Row 11
        (12, False, True, False, False, False),  # Row 12
        (13, False, False, True, True, False),   # Row 13
        (14, False, False, True, False, False),  # Row 14
        (15, False, False, False, True, False),  # Row 15
        (16, False, False, False, False, False), # Row 16
    ]

    @pytest.mark.parametrize("row_id, a_active, b_from, c_until, d_quota, expected", MCC_TRUTH_TABLE)
    def test_mcc_all_16_combinations(
        self, team_organizer, team_event, row_id, a_active, b_from, c_until, d_quota, expected
    ):
        """Exhaustively execute all 16 rows of the Multiple Condition Coverage (MCC) truth table."""
        with scope(organizer=team_organizer):
            current_time = now()

            # Configure Condition A (active)
            item = Item.objects.create(
                event=team_event,
                name=f'MCC-Item-Row-{row_id}',
                default_price=Decimal('25.00'),
                active=a_active
            )

            # Configure Condition B (available_from)
            if b_from:
                item.available_from = current_time - datetime.timedelta(days=2)  # Started in the past
            else:
                item.available_from = current_time + datetime.timedelta(days=2)  # Starts in the future

            # Configure Condition C (available_until)
            if c_until:
                item.available_until = current_time + datetime.timedelta(days=5)  # Ends in the future
            else:
                item.available_until = current_time - datetime.timedelta(days=1)  # Ended in the past
            item.save()

            # Configure Condition D (quota availability)
            quota = Quota.objects.create(
                event=team_event,
                name=f'MCC-Quota-Row-{row_id}',
                size=10 if d_quota else 0  # 10 available if True, 0 if False
            )
            quota.items.add(item)

            # Evaluate decision
            actual_outcome = evaluate_purchasability(item, quota, current_time)
            assert actual_outcome == expected, (
                f"MCC Failure at Row {row_id}: A={a_active}, B={b_from}, C={c_until}, D={d_quota}. "
                f"Expected {expected}, got {actual_outcome}"
            )

    # -------------------------------------------------------------------------
    # Formal MC/DC Independence Pair Tests
    # -------------------------------------------------------------------------

    def test_mcdc_condition_a_active_independent_effect(self, team_organizer, team_event):
        """
        MC/DC Pair for Condition A (Active): (Row 1, Row 9)
        Condition A flips (True -> False) while B, C, D remain fixed (True).
        Decision D must flip from True -> False.
        """
        with scope(organizer=team_organizer):
            t = now()
            quota = Quota.objects.create(event=team_event, name='MCDC-Q-A', size=5)

            # Row 1: A=True, B=True, C=True, D=True -> Outcome = True
            item_r1 = Item.objects.create(
                event=team_event, name='R1-Item', default_price=Decimal('10.00'), active=True,
                available_from=t - datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=1)
            )
            quota.items.add(item_r1)
            assert evaluate_purchasability(item_r1, quota, t) is True

            # Row 9: A=False, B=True, C=True, D=True -> Outcome = False
            item_r9 = Item.objects.create(
                event=team_event, name='R9-Item', default_price=Decimal('10.00'), active=False,
                available_from=t - datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=1)
            )
            quota.items.add(item_r9)
            assert evaluate_purchasability(item_r9, quota, t) is False

    def test_mcdc_condition_b_from_date_independent_effect(self, team_organizer, team_event):
        """
        MC/DC Pair for Condition B (From Date): (Row 1, Row 5)
        Condition B flips (True -> False) while A, C, D remain fixed (True).
        Decision D must flip from True -> False.
        """
        with scope(organizer=team_organizer):
            t = now()
            quota = Quota.objects.create(event=team_event, name='MCDC-Q-B', size=5)

            # Row 1: B=True (started yesterday) -> True
            item_r1 = Item.objects.create(
                event=team_event, name='R1-Item-B', default_price=Decimal('10.00'), active=True,
                available_from=t - datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=1)
            )
            quota.items.add(item_r1)
            assert evaluate_purchasability(item_r1, quota, t) is True

            # Row 5: B=False (starts tomorrow) -> False
            item_r5 = Item.objects.create(
                event=team_event, name='R5-Item-B', default_price=Decimal('10.00'), active=True,
                available_from=t + datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=2)
            )
            quota.items.add(item_r5)
            assert evaluate_purchasability(item_r5, quota, t) is False

    def test_mcdc_condition_c_until_date_independent_effect(self, team_organizer, team_event):
        """
        MC/DC Pair for Condition C (Until Date): (Row 1, Row 3)
        Condition C flips (True -> False) while A, B, D remain fixed (True).
        Decision D must flip from True -> False.
        """
        with scope(organizer=team_organizer):
            t = now()
            quota = Quota.objects.create(event=team_event, name='MCDC-Q-C', size=5)

            # Row 1: C=True (ends tomorrow) -> True
            item_r1 = Item.objects.create(
                event=team_event, name='R1-Item-C', default_price=Decimal('10.00'), active=True,
                available_from=t - datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=1)
            )
            quota.items.add(item_r1)
            assert evaluate_purchasability(item_r1, quota, t) is True

            # Row 3: C=False (ended yesterday) -> False
            item_r3 = Item.objects.create(
                event=team_event, name='R3-Item-C', default_price=Decimal('10.00'), active=True,
                available_from=t - datetime.timedelta(days=2), available_until=t - datetime.timedelta(days=1)
            )
            quota.items.add(item_r3)
            assert evaluate_purchasability(item_r3, quota, t) is False

    def test_mcdc_condition_d_quota_stock_independent_effect(self, team_organizer, team_event):
        """
        MC/DC Pair for Condition D (Quota Stock): (Row 1, Row 2)
        Condition D flips (True -> False) while A, B, C remain fixed (True).
        Decision D must flip from True -> False.
        """
        with scope(organizer=team_organizer):
            t = now()
            item = Item.objects.create(
                event=team_event, name='MCDC-Item-D', default_price=Decimal('10.00'), active=True,
                available_from=t - datetime.timedelta(days=1), available_until=t + datetime.timedelta(days=1)
            )

            # Row 1: D=True (size=5 > 0) -> True
            quota_r1 = Quota.objects.create(event=team_event, name='MCDC-Q-D1', size=5)
            quota_r1.items.add(item)
            assert evaluate_purchasability(item, quota_r1, t) is True

            # Row 2: D=False (size=0) -> False
            quota_r2 = Quota.objects.create(event=team_event, name='MCDC-Q-D2', size=0)
            quota_r2.items.add(item)
            assert evaluate_purchasability(item, quota_r2, t) is False
