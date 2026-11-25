"""Delivery rewards survive spending and stop at the per-item episode target."""

import pytest

from gamma import tasks


@pytest.mark.parametrize("item,scale", [("copper", 0.1), ("lead", 0.15)])
def test_machine_and_hand_deliveries_share_the_cap(item, scale):
    reward = tasks._income_gain(item, scale, 200)
    before = {"produced": {item: 190}, "hand_delivered": {item: 5}}
    after = {"produced": {item: 200}, "hand_delivered": {item: 10}}
    assert reward(before, after) == pytest.approx(5 * scale)
    assert reward(after, after) == 0
    assert reward(after, {"produced": {item: 300}}) == 0
    assert reward(after, {}) == 0  # counter reset never gives negative income reward


def test_loadout_spending_and_other_items_do_not_count_as_delivery():
    reward = tasks._income_gain("copper", 0.1, 200)
    assert reward({}, {"items": {"copper": 300}}) == 0
    before = {"items": {"copper": 300}, "produced": {"copper": 10}}
    assert reward(before, {**before, "items": {"copper": 0}}) == 0
    assert reward(before, {**before, "produced": {"copper": 10, "lead": 50}}) == 0
    assert reward({}, {"hand_delivered": {"copper": 7}}) == pytest.approx(0.7)


def test_build_payments_only_and_counter_reset():
    reward = tasks._build_copper_cost(0.01)
    before = {"build_copper_spent": 12}
    after = {"build_copper_spent": 15, "items": {"copper": 999}}
    assert reward(before, after) == pytest.approx(-0.03)
    assert reward(after, after) == 0
    assert reward(after, {"build_copper_spent": 0}) == 0


@pytest.mark.parametrize("before,after", [({}, {}), ({"build_copper_spent": 0}, {}),
                                         ({}, {"build_copper_spent": 0})])
def test_missing_build_counter_fails_clearly(before, after):
    with pytest.raises(RuntimeError, match="rebuild the bridge"):
        tasks._build_copper_cost(0.01)(before, after)
