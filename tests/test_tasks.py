"""What each curriculum task pays for.

A reward is the whole of what an agent is being asked to do, and it is the one part of a
run that no amount of watching will tell you is wrong: a policy learning nothing looks
exactly like a policy learning slowly. These run without a server, because the question is
arithmetic and not simulation.
"""

from __future__ import annotations

import pytest

from gamma import tasks

Observation = dict


def state(**fields) -> Observation:
    """A Ground Zero observation with everything at its starting value."""
    base = {"wave": 1, "core_health": 1100.0, "items": {"copper": 300, "lead": 300}}
    items = {**base["items"], **fields.pop("items", {})}
    return {**base, **fields, "items": items}


@pytest.fixture
def reward():
    return tasks.get("GZ_capture").reward


def test_standing_still_earns_nothing(reward) -> None:
    """The failure this task had for twenty-six generations: every episode scored the
    same, because the only term was a wave counter running on a timer."""
    assert reward(state(), state()) == 0.0


def test_a_wave_survived_is_worth_one(reward) -> None:
    assert reward(state(), state(wave=2)) == pytest.approx(1.0)


def test_damage_to_the_core_costs(reward) -> None:
    """The term that answers whether the defence held."""
    assert reward(state(), state(core_health=800.0)) < 0


def test_losing_the_core_costs_more_than_the_waves_it_bought(reward) -> None:
    """Otherwise letting the enemy through and collecting waves is a winning strategy."""
    lost = reward(state(), state(core_health=0.0, wave=2))
    assert lost < -2, lost


def test_a_repaired_core_pays_nothing_back(reward) -> None:
    """A core does not heal, but nothing should reward the appearance of it either: a
    term that pays both ways is a term an agent can pump."""
    assert reward(state(core_health=800.0), state()) == pytest.approx(0.0)


def test_banking_ore_is_worth_a_fraction_of_a_wave(reward) -> None:
    """Enough to give the first thousand steps a gradient, not enough to beat surviving."""
    banked = reward(state(), state(items={"copper": 400}))
    assert 0 < banked < reward(state(), state(wave=2))


def test_spending_ore_is_not_punished_into_paralysis(reward) -> None:
    """Building costs resources. A penalty as large as the reward would teach the agent to
    hoard, which is the opposite of the point."""
    spent = reward(state(), state(items={"copper": 200}))
    assert spent > -1


def test_capturing_the_sector_is_surviving_past_wave_ten(reward) -> None:
    task = tasks.get("GZ_capture")
    assert not task.succeeded({"wave": 10})
    assert task.succeeded({"wave": 11})


def test_no_task_pays_for_standing_still():
    """A step in which nothing changed must earn nothing, on every task.

    This is the invariant that separates a rate from a level, and it is not academic. The
    reward once paid `generation * 0.05` per step, meaning a generator bought once printed
    points for the remaining three thousand steps of the episode. The agent found it and
    the run looked healthy while it did: mean score climbing smoothly from +21 to +205 over
    two hundred updates, best episode +1577, and across 167 archived episodes exactly ONE
    conveyor line that ever reached a core.

    The rewards themselves gave it away, being exact multiples of 0.05 for thousands of
    consecutive steps, which is generation burning steadily while nothing else happened at
    all. Any term that reads a level rather than a difference fails here, immediately, on
    a static observation, without needing a training run to notice.
    """
    still = {
        "items": {"copper": 300, "lead": 300},
        "stats": {"enemy_units_destroyed": 4, "buildings_destroyed": 2},
        "produced": {"copper": 500},
        "placed": {"production": 3, "distribution": 9, "power": 2, "crafting": 1},
        "crafting": 12.5,
        "power": 11.0,
        "core_health": 900.0,
        "wave": 6,
        "has_core": True,
        "unit": {"carrying": 30},
    }

    for name, task in tasks.CURRICULUM.items():
        if name == "frontier_shaped":
            # Genuinely exempt, not excused. Potential-based shaping pays
            # `gamma * phi(after) - phi(before)`, so a static step pays
            # `(gamma - 1) * phi`, which is negative and cannot be collected: the sum over
            # an episode telescopes to `gamma^T * phi(last) - phi(first)` no matter what
            # the agent does in between. That is the theorem the whole design rests on.
            assert task.reward(still, still) <= 0.0
            continue

        assert task.reward(still, still) == pytest.approx(0.0), (
            f"{name} pays {task.reward(still, still)} for a step in which nothing changed, "
            "which an agent collects every step of the episode for free"
        )


def test_each_caller_gets_its_own_ledger():
    """A stateful reward must not be shared between environments.

    The curriculum is a module-level dictionary, so `get` used to hand every caller the
    same `Task` and therefore the same reward object. Harmless while a reward was a pure
    function; not harmless once it kept a per-episode ledger, because a training run puts
    twenty-four environments on twenty-four threads of one process.

    It surfaced as nonsense in the accounts rather than as a crash. Across 225 archived
    episodes the breakdown reported 1,515 core losses, up to nine in one episode, some on
    steps whose reward was exactly zero: one environment's itemisation read while another
    environment's step had overwritten it.
    """
    one, other = tasks.get("frontier"), tasks.get("frontier")
    assert one.reward is not other.reward

    still = {
        "wave": 1, "has_core": True, "core_health": 4000.0, "items": {}, "produced": {},
        "crafting": 0.0, "placed": {}, "stats": {}, "unit": {"carrying": 0},
    }
    one.reward(still, {**still, "produced": {"copper": 40}})

    assert one.reward.credited == pytest.approx(40.0)
    assert other.reward.credited == pytest.approx(0.0), (
        "a delivery credited in one environment was visible in another"
    )


def test_the_defensive_ladder_has_no_hole_where_the_agent_actually_dies():
    """A rung nobody can reach pays nothing, and the middle of the game had none.

    The economic rungs stepped 1, 100, 1k, 10k while the defensive ones jumped from one
    kill to twenty-five and from wave five to ten. The agent learned exactly that shape:
    140 items delivered per episode and dead at wave three. Measured over 183 episodes,
    124 ended at wave two or three, so every defensive rung above was out of reach.
    """
    waves = sorted(m.threshold for m in tasks.MILESTONES if m.name.startswith("wave_"))
    kills = sorted(m.threshold for m in tasks.MILESTONES
                   if "kill" in m.name or m.name == "held_a_wave")

    assert 3 in waves and 4 in waves, "the waves the agent dies on must be worth something"
    assert max(b / a for a, b in zip(waves, waves[1:])) <= 2.0, (
        "no defensive rung may be more than a doubling away from the one below")
    assert max(b / a for a, b in zip(kills, kills[1:])) <= 5.0, (
        "one kill straight to twenty-five is a hole, not a ladder")


def test_no_milestone_is_free():
    """A rung every episode crosses without trying is a payment, not a lesson."""
    assert all(m.threshold >= 1 for m in tasks.MILESTONES)
    waves = [m.threshold for m in tasks.MILESTONES if m.name.startswith("wave_")]
    assert min(waves) >= 3, "every episode reaches wave two, so it cannot be a rung"


def drills(*drills, plans=()) -> Observation:
    """drills as (x, y, connected); plans as (x, y, block)."""
    return {"drills": [[x, y, 1, c] for x, y, c in drills],
            "unit": {"plan_queue": [[x, y, block, 1, 0] for x, y, block in plans]}}


@pytest.mark.parametrize("before, after, paid", [
    (drills(), drills((10, 10, 0)), 0.0),
    (drills((10, 10, 0)), drills((10, 10, 0), (20, 10, 0)), -0.5),
    (drills((10, 10, 0), plans=[(12, 10, "conveyor")]),
     drills((10, 10, 0), (20, 10, 0), plans=[(12, 10, "conveyor")]), 0.0),
    (drills((10, 10, 1)), drills((10, 10, 1), (20, 10, 0)), 0.0),
    (drills(plans=[(10, 10, "mechanical-drill")]),
     drills(plans=[(10, 10, "mechanical-drill"), (20, 10, "mechanical-drill")]), -0.5),
    (drills((20, 10, 0), plans=[(10, 10, "mechanical-drill")]),
     drills((20, 10, 0), (10, 10, 0)), 0.0),
], ids=["first", "another unrouted", "line queued", "connected", "blueprint", "built"])
def test_a_drill_ordered_while_others_owe_a_line(before, after, paid) -> None:
    assert tasks._drill_while_unrouted(-0.5)(before, after) == paid


def test_some_drills_may_owe_a_line_at_once() -> None:
    penalty = tasks._drill_while_unrouted(-0.5, allowed=1)
    one, two = drills((10, 10, 0)), drills((10, 10, 0), (20, 10, 0))
    assert penalty(one, two) == 0.0
    assert penalty(two, drills((10, 10, 0), (20, 10, 0), (30, 10, 0))) == -0.5


@pytest.mark.parametrize("produced, hand, paid", [
    (0, 0, 1.0), (150, 49, 1.0), (150, 50, 0.0), (300, 0, 0.0),
], ids=["none", "one short", "hand counts", "past it"])
def test_a_term_stops_paying_once_its_item_reaches_the_target(produced, hand, paid) -> None:
    before = {"produced": {"copper": produced}, "hand_delivered": {"copper": hand}}
    assert tasks._until_income("copper", 200, lambda b, a: 1.0)(before, {}) == paid


@pytest.mark.parametrize("was, now, paid", [
    (0, 49, 0.0), (49, 50, 5.0), (50, 60, 0.0), (40, 160, 15.0), (0, 0, 0.0), (200, 300, 0.0),
], ids=["below", "reaches one", "already past", "crosses three", "nothing", "past the last"])
def test_an_income_rung_pays_once_when_reached(was, now, paid) -> None:
    rungs = tasks._income_rungs("lead", (50, 100, 150, 200), 5.0)
    income = lambda n: {"produced": {"lead": n - n // 4}, "hand_delivered": {"lead": n // 4}}
    assert rungs(income(was), income(now)) == paid


@pytest.mark.parametrize("was, now, paid", [
    ((300, 40), (400, 40), 0.0), ((300, 40), (300, 50), 5.0), ((40, 60), (60, 60), 5.0),
    ((40, 40), (160, 160), 15.0), ((0, 0), (200, 0), 0.0),
], ids=["only copper", "lead catches up", "copper catches up", "both cross three", "one alone"])
def test_a_joint_rung_pays_once_both_items_reach_it(was, now, paid) -> None:
    rungs = tasks._joint_income_rungs(("copper", "lead"), (50, 100, 150, 200), 5.0)
    income = lambda c, l: {"produced": {"copper": c, "lead": l}}
    assert rungs(income(*was), income(*now)) == paid


@pytest.mark.parametrize("turrets, paid", [
    ([], 0.0), ([(52, 50, 1)], 1.0), ([(52, 50, 0)], 0.5), ([(90, 50, 1)], 0.0),
    ([(51, 50, 0), (52, 50, 1), (53, 50, 1), (54, 50, 1)], 3.0),
], ids=["none", "armed", "unarmed", "too far", "capped, armed first"])
def test_turrets_by_the_core_pay_when_a_wave_lands(turrets, paid) -> None:
    guards = tasks._guards_at_wave(15, 3, 1.0, 0.5)
    obs = lambda wave: {"wave": wave, "has_core": True, "core_x": 50, "core_y": 50,
                        "turrets": [list(t) for t in turrets]}
    assert guards(obs(2), obs(3)) == paid
    assert guards(obs(3), obs(3)) == 0.0
