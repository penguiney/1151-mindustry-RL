"""The Gymnasium environment behaves like one, and the baselines rank as expected."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from gymnasium import spaces

from gamma import env as env_module
from gamma import tasks
from gamma.alpha import AlphaPolicy
from gamma.env import ACTION_TYPES, GLOBAL_FIELDS, MindustryEnv
from gamma.policies import MaskedRandomPolicy, RandomPolicy, run_episode

def test_spaces_are_available_before_the_first_reset(env: MindustryEnv) -> None:
    """Gymnasium callers build policies from the spaces, so asking early must work."""
    assert isinstance(env.action_space, spaces.MultiDiscrete)
    assert isinstance(env.observation_space, spaces.Dict)
    # Against the environment's own list, not the module constant: the list grows with
    # what the environment offers, and comparing to the constant is how a whole action
    # type stayed unreachable for a day.
    assert env.action_space.nvec[0] == len(env.action_types)
    assert env.action_space.nvec[1] == len(env.blocks)


def test_reset_returns_an_observation_in_the_space(env: MindustryEnv) -> None:
    obs, info = env.reset()
    assert env.observation_space.contains(obs)
    assert obs["global"].shape == (len(GLOBAL_FIELDS),)
    assert "action_mask" in info


def test_step_returns_the_gym_five_tuple(env: MindustryEnv) -> None:
    env.reset()
    obs, reward, terminated, truncated, info = env.step(np.zeros(5, dtype=np.int64))
    assert env.observation_space.contains(obs)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)


def test_masks_cover_every_head(env: MindustryEnv) -> None:
    _, info = env.reset()
    mask = info["action_mask"]
    # Against `env.action_types` and not the module constant, which is what let a whole
    # action type go missing. The list grows a `stamp` entry as soon as a design is
    # loaded; the mask did not, and the network takes its type count from the mask.
    assert mask["type"].shape == (len(env.action_types),)
    assert mask["block"].shape == (len(env.blocks),)
    assert mask["position"].ndim == 2
    assert mask["type"][ACTION_TYPES.index("noop")], "doing nothing is always legal"


def test_observation_keys_survive_losing_the_core(env: MindustryEnv) -> None:
    """Fields must not appear and disappear.

    `items` used to be omitted when there was no core, which crashed consumers at the
    exact moment an episode was ending. A policy fed a vector that changes shape learns
    nothing from it either.
    """
    _, info = env.reset()
    raw = info["raw"]
    for field in ("items", "has_core", "core_x", "core_y", "map_width", "wave"):
        assert field in raw, f"{field} missing from the observation"


def test_illegal_action_is_reported_not_raised(env: MindustryEnv) -> None:
    env.reset()
    far = np.array([ACTION_TYPES.index("place"), 0, 0, 0, 0], dtype=np.int64)
    _, _, _, _, info = env.step(far)
    assert info["action"] is not None
    assert info["action"]["applied"] is False


def test_truncation_happens_at_the_step_limit(env: MindustryEnv) -> None:
    """Uses a shortened copy of the task so the check does not cost 450 steps."""
    from dataclasses import replace

    env.task = replace(tasks.T1_COPPER, max_steps=3)
    try:
        env.reset()
        flags = [env.step(np.zeros(5, dtype=np.int64))[3] for _ in range(3)]
        assert flags[-1] is True, "the episode never truncated"
        assert not any(flags[:-1]), "truncated too early"
    finally:
        env.task = tasks.T1_COPPER


@pytest.mark.perf
def test_alpha_beats_random_on_t1(env: MindustryEnv) -> None:
    """The baseline ordering the whole curriculum rests on.

    Marked perf because it plays several full episodes. If this inverts, either Alpha
    broke or the task stopped measuring anything.
    """
    # Both policies play the same world. Without the pin they do not: Mindustry paints
    # ore on at load time and re-randomises it every load, so this compared two policies
    # on two different maps and duly inverted, with random scoring 39 against Alpha's 16.
    from dataclasses import replace

    env.task = replace(tasks.T1_COPPER, world_seed=20260824)
    try:
        alpha = AlphaPolicy(env)
        alpha.reset()
        scripted = run_episode(env, alpha)
        chaotic = run_episode(env, MaskedRandomPolicy(env.action_space, seed=0, env=env))
    finally:
        env.task = tasks.T1_COPPER

    assert scripted["reward"] > chaotic["reward"]
    assert scripted["items"].get("copper", 0) > chaotic["items"].get("copper", 0)

    # On the share that lands, not on the count. A random policy that picks `connect`
    # spends one action on forty blocks, so once routing stopped refusing it the noise
    # out-counted the script while still scoring and mining far less. What this was
    # protecting is that Alpha's actions land, which is a rate.
    def landing(result):
        return result["applied"] / max(1, result["applied"] + result["refused"])

    assert landing(scripted) > landing(chaotic)


def test_a_loaded_design_is_reachable(env: MindustryEnv) -> None:
    """A design the policy cannot choose is a design that does not exist.

    `action_types` grows a `stamp` entry as soon as a design is loaded and the mask did
    not, so the head had six outputs while the environment named seven and the seventh was
    unreachable. Measured over 54 archived episodes: zero stamps in 39,456 actions. Not a
    choice the policy made, an option it never had, on every run that passed --designs.

    It is the mechanism built for the problem the project keeps hitting, which is that a
    conveyor line placed one tile at a time never gets finished: 5,719 conveyors across
    177 episodes and one line that ever met end to end.
    """
    from gamma.env import STAMP
    from gamma.library import load as load_designs

    designs = tuple(load_designs(Path("docs/designs.json")))
    assert designs, "no design to test with"

    was = env.designs
    try:
        env.designs = designs
        _, info = env.reset()
        types = env.action_types
        assert STAMP in types
        assert info["action_mask"]["type"].shape == (len(types),)
    finally:
        env.designs = was


def test_breaking_can_aim_at_something_breakable(env: MindustryEnv) -> None:
    """One position head serves four action types, so its mask must cover all of them.

    It was `free` alone: buildable, empty, not solid. Right for building and exactly
    inverted for breaking, because `free` and `owned` are disjoint by construction, so
    every tile the agent could aim at while choosing `break` was guaranteed to hold
    nothing. Measured over 30 archived episodes: 6,660 demolitions, 23 of which hit a
    building the agent had placed.
    """
    import numpy as np

    _, info = env.reset()
    mask = info["action_mask"]

    spatial = info["raw"]["spatial"]
    channels = env._bridge.channels
    owned = spatial[channels.index("block_ally")] > 0

    assert owned.any(), "the core is an ally building, so something must be breakable"
    assert (mask["position"] & owned).any(), (
        "no tile holding an ally building is aimable, so breaking cannot ever work"
    )


def test_every_way_of_building_is_remembered(env: MindustryEnv) -> None:
    """The churn penalty watches tiles the agent built, so it must know all of them.

    Only manual placements were noted at first and the penalty never fired once: measured
    over 30 episodes, not one demolition landed on a tile the agent had `place`d, because
    it had stopped placing by hand. Nearly everything it built came from `connect`, forty
    blocks at a time, and those were the buildings it was tearing down. A rule watching the
    wrong door is indistinguishable from no rule.
    """
    env._built_at.clear()
    env._steps = 10

    env._remember([(4, 5, "conveyor", 0), (6, 7, "mechanical-drill", 0)])
    assert env._built_at[(4, 5)] == 10 and env._built_at[(6, 7)] == 10

    # Breaking one of them soon after is churn; breaking it much later is revision.
    assert env._note_churn("break", 4, 5) is True

    env._remember([(8, 9, "conveyor", 0)])
    env._steps = 10 + env.CHURN_WINDOW + 1
    assert env._note_churn("break", 8, 9) is False


def _settle(env, applied: bool) -> None:
    env._settle_churn({"action": {"applied": applied}})


def test_a_refused_demolition_is_not_charged_and_the_tile_is_not_forgotten(
        env: MindustryEnv) -> None:
    """Charging a refused break prices an attempt that changed nothing.

    Worse, popping the tile on the way would let the demolition that does land a moment
    later go free, so a single refusal would launder the very behaviour being priced.
    """
    env._built_at.clear()
    env._steps = 10
    env._remember([(3, 3, "conveyor", 0)])

    env._churned = env._note_churn("break", 3, 3)
    env._breaking = (3, 3)
    assert env._churned is True
    _settle(env, applied=False)
    assert env._churned is False, "nothing was torn down, so nothing is owed"
    assert (3, 3) in env._built_at, "the tile still stands and is still the agent's"

    env._churned = env._note_churn("break", 3, 3)
    env._breaking = (3, 3)
    _settle(env, applied=True)
    assert env._churned is True
    assert (3, 3) not in env._built_at, "it is gone now, so the ledger lets it go"


def test_a_refused_placement_does_not_go_on_the_ledger(env: MindustryEnv) -> None:
    """Otherwise the agent is later charged for clearing a building it never owned."""
    env._built_at.clear()
    env._steps = 10

    env._note_churn("place", 7, 7)
    _settle(env, applied=False)
    assert (7, 7) not in env._built_at

    env._note_churn("place", 7, 7)
    _settle(env, applied=True)
    assert (7, 7) in env._built_at


def test_drill_and_link_are_not_offered_to_an_agent_that_cannot_pay(
        env: MindustryEnv, monkeypatch) -> None:
    """A refusal the agent cannot see coming teaches it nothing except that the action is
    bad. Measured on connect before it was split: 2,357 refusals out of 2,671 connects over
    eleven episodes, nearly all of them an agent too broke to pay for what it asked."""
    if not env.mining:
        pytest.skip("this build has no drill or link")

    env.reset()
    drill, link = env.action_types.index("drill"), env.action_types.index("link")
    channels = env._bridge.channels
    ore = next(name for name in channels if name.startswith("ore_"))
    spatial = np.zeros((len(channels), 8, 8), dtype=np.uint8)
    spatial[channels.index("buildable")] = 1
    spatial[channels.index(ore)][2:4, 2:4] = 1
    obs = {"spatial": spatial, "window_origin": (0, 0), "drills": [[5, 5, 0]],
           "unit": {"mine_tier": 1, "carrying": 0, "capacity": 10}}
    monkeypatch.setattr(env._bridge, "ore_hardness", [0] * 32)

    monkeypatch.setattr(env._bridge, "affordable_blocks", lambda: [])
    legal = env._masks(obs)["type"]
    assert not legal[drill] and not legal[link], "nothing to pay with, nothing offered"

    monkeypatch.setattr(env._bridge, "affordable_blocks", lambda: ["conveyor", "mechanical-drill"])
    legal = env._masks(obs)["type"]
    assert legal[drill], "ore in view and the copper for a drill"
    assert legal[link], "a drill of its own with nowhere to put its ore"

    obs["drills"] = [[5, 5, 1]]
    assert not env._masks(obs)["type"][link], "every drill already linked"


def ground(size: int, **cells: list[tuple[int, int]]) -> np.ndarray:
    """Bridge ground flags for a small map: blocked, building, carries, ours."""
    bits = {"blocked": 1, "building": 2, "carries": 4, "ours": 8}
    flags = np.zeros((size, size), dtype=np.uint8)
    for name, where in cells.items():
        for x, y in where:
            flags[y, x] |= bits[name]
    return flags


def test_a_line_may_run_through_the_agents_own_network() -> None:
    """Everything built counted as a wall, so the first line to the core sealed it.

    Every tile touching the core was then one of the agent's own conveyors, and no second
    line could ever arrive: the better the economy got, the more thoroughly it walled
    itself in. Measured over 179 episodes after the search itself was fixed, "no route"
    was still the leading refusal in the run, 15,181 connects and 9,523 stamps, and it was
    never the terrain.
    """
    belt, drill, theirs, rock = (1, 1), (2, 2), (3, 3), (5, 5)
    flags = ground(8, building=[belt, drill, theirs], ours=[belt, drill],
                   carries=[belt], blocked=[rock])
    passable, ours = MindustryEnv._passable(flags)

    assert passable[belt[1], belt[0]], "its own conveyor is something to run into"
    assert ours[belt[1], belt[0]], "and it is known to be occupied, so nothing is relaid"
    assert not passable[drill[1], drill[0]], "its own drill is not: a line ends at it"
    assert not passable[theirs[1], theirs[0]], "someone else's building is still a wall"
    assert not passable[rock[1], rock[0]], "and so is rock"
    assert passable[0, 0], "and open ground is open"


def test_a_line_goes_around_deep_water() -> None:
    """Deep water is not solid, so a search that only looked at `solid` and `block` ran
    belts straight across it. Every tile that landed in the water was refused and the line
    went down with a hole in it."""
    water, ground_tile = (4, 4), (2, 2)
    passable, _ = MindustryEnv._passable(ground(8, blocked=[water]))
    assert not passable[water[1], water[0]], "floor that takes no building is a wall"
    assert passable[ground_tile[1], ground_tile[0]], "and open ground is still open"


def test_ground_covers_the_whole_map_not_the_window(env: MindustryEnv) -> None:
    """A line runs up to sixty tiles and the window is forty-eight, so the ground has to
    come from the world rather than from the observation."""
    env.reset()
    passable, ours = env._ground()
    raw = env._last_obs
    assert passable.shape == (int(raw["map_height"]), int(raw["map_width"]))
    assert not passable.all(), "a real map has ground a belt cannot cross"


def test_ore_too_hard_for_the_unit_is_not_offered(env: MindustryEnv, monkeypatch) -> None:
    """The comment said the mask filtered by hardness and the code took every ore.

    That is worse than no comment: it read as done. Measured over 184 episodes, 9,584
    mining orders were refused, the largest single source of refused actions in the run
    once routing was fixed, and the whole cause was titanium and thorium being offered to
    a unit that cannot touch them.
    """
    observation, info = env.reset()
    channels = env._bridge.channels
    ores = [name for name in channels if name.startswith("ore_")]
    if len(ores) < 2:
        pytest.skip("this map carries a single ore, so hardness cannot discriminate")

    spatial = np.zeros((len(channels), 8, 8), dtype=np.uint8)
    spatial[channels.index("buildable")] = 1
    for offset, name in enumerate(ores):
        spatial[channels.index(name)][0, offset] = 1

    monkeypatch.setattr(env._bridge, "ore_hardness", [0] + [9] * (len(ores) - 1))
    # Mining belongs to the embodied action space, and the direct one returns before the
    # mask is even built. Two branches, one rule, which is how the affordability gate came
    # to be fixed in one and not the other.
    monkeypatch.setattr(env, "embodied", True)
    obs = {"spatial": spatial, "unit": {"mine_tier": 1, "carrying": 0, "capacity": 10}}

    mineable = env._masks(obs)["mineable"]
    assert mineable[0, 0], "the soft ore is on the table"
    assert not mineable[0, 1:len(ores)].any(), "and nothing the unit cannot touch is"


def test_the_agent_can_tell_where_its_core_is(env: MindustryEnv) -> None:
    """Nothing in the observation used to say where home was.

    The agent knew its own position and its core's health and never the core's position,
    so it could not tell how far from home it was nor which way home lay. The window is
    forty-eight tiles and follows the unit, so once it wandered the core was not in the
    picture at all. It went on building defences where it happened to be standing:
    measured over 174 lost cores, 9.4 turrets and 16.8 walls per episode, laid a median of
    60 tiles from the core and 105 on average.
    """
    fields = [name for name, _ in env_module.GLOBAL_FIELDS]
    assert "core_dx" in fields and "core_dy" in fields

    encoded = env._encode({
        "spatial": np.zeros((len(env._bridge.channels), 4, 4), dtype=np.uint8),
        "core_x": 100.0, "core_y": 40.0,
        "unit": {"x": 60, "y": 55},
    })
    scale = dict(env_module.GLOBAL_FIELDS)["core_dx"]
    assert encoded["global"][fields.index("core_dx")] == pytest.approx(40.0 / scale)
    assert encoded["global"][fields.index("core_dy")] == pytest.approx(-15.0 / scale)


def test_a_drill_can_be_aimed_only_where_its_whole_square_fits_on_ore(
        env: MindustryEnv, monkeypatch) -> None:
    """`drill` builds where the policy points, so the mask names the tiles a 2x2 drill
    can be anchored on: the whole square free, at least one tile of ore a mechanical drill
    can mine. Coal-like ore the unit cannot mine by hand still counts; ore a drill
    cannot mine does not."""
    env.reset()
    channels = env._bridge.channels
    ores = [name for name in channels if name.startswith("ore_")]
    if len(ores) < 2:
        pytest.skip("this map carries a single ore, so hardness cannot discriminate")

    spatial = np.zeros((len(channels), 10, 10), dtype=np.uint8)
    spatial[channels.index("buildable")] = 1
    drillable_ore, too_hard = ores[0], ores[1]
    spatial[channels.index(drillable_ore)][2, 2] = 1      # under the square at (1..2, 1..2)
    spatial[channels.index(too_hard)][6, 6] = 1
    spatial[channels.index("block")][2, 8] = 1             # ore under a building
    spatial[channels.index(drillable_ore)][2, 8] = 1

    # The first ore is too hard for the unit's hands but not for a drill.
    hardness = [2, 9] + [9] * (len(ores) - 2)
    monkeypatch.setattr(env._bridge, "ore_hardness", hardness)
    monkeypatch.setattr(env, "embodied", True)
    obs = {"spatial": spatial, "unit": {"mine_tier": 1, "carrying": 0, "capacity": 10}}

    masks = env._masks(obs)
    drillable = masks["position_sets"][env_module.POSITION_SETS.index("drillable")]
    anchors = {(int(x), int(y)) for y, x in zip(*np.nonzero(drillable))}
    assert anchors == {(1, 1), (2, 1), (1, 2), (2, 2)}, "every square that covers the ore"
    assert not masks["mineable"][2, 2], "and the unit could not have mined it by hand"


def test_drill_places_exactly_where_it_was_pointed(env: MindustryEnv) -> None:
    env.reset()
    where = env.action_types.index("drill")
    order = env._decode(np.array([where, 0, 4, 4, 3]))
    assert order is not None
    assert (order["block"], order["x"], order["y"], order["rotation"]) == (
        "mechanical-drill", 4, 4, 0), "the block and rotation heads have no say"


def test_place_cannot_put_down_a_drill(env: MindustryEnv, monkeypatch) -> None:
    """A drill placed by hand is one nothing will ever be asked to wire up, and that is
    the whole of what the ninth run learned to do: 110 drills an episode, none linked."""
    if not env.mining or "mechanical-drill" not in env.blocks:
        pytest.skip("this build has no drill action")
    observation, info = env.reset()
    monkeypatch.setattr(env._bridge, "affordable_blocks", lambda: list(env.blocks))
    blocks = env._masks(env._last_obs)["block"]
    assert not blocks[env.blocks.index("mechanical-drill")]
    assert blocks[env.blocks.index("conveyor")]


def test_link_routes_from_an_open_side_of_the_drill(env: MindustryEnv, monkeypatch) -> None:
    """A belt from a drill already standing, and from a side that is open: the tile below
    is rock, which used to be the only side a line could leave from."""
    env.reset()
    channels = env._bridge.channels
    size = 16
    spatial = np.zeros((len(channels), size, size), dtype=np.uint8)
    drill = [(x, y) for x in (4, 5) for y in (4, 5)]
    flags = ground(size, blocked=[(4, 3), (5, 3)], building=drill, ours=drill)
    import base64
    monkeypatch.setattr(env._bridge, "ground", lambda: {
        "width": size, "height": size, "flags": base64.b64encode(flags.tobytes()).decode()})

    asked = []
    monkeypatch.setattr(env._bridge, "act",
                        lambda action: asked.append(action) or {"action": {"applied": True}})
    env._last_obs = {"spatial": spatial, "map_width": size, "map_height": size,
                     "window_origin": (0, 0), "core_x": 12, "core_y": 12,
                     "drills": [[4, 4, 0]], "items": {"copper": 200}}

    env._link(4, 4)

    assert asked and all(a["block"] == "conveyor" for a in asked), "a line and no drill"
    belt = [(a["x"], a["y"]) for a in asked]
    assert (4, 3) not in belt and (5, 3) not in belt, "nothing is laid on the rock"
    assert not any(4 <= x <= 5 and 4 <= y <= 5 for x, y in belt), "nor on the drill"
    assert env._last_connect["applied"]


def test_link_is_refused_when_the_core_cannot_pay_for_the_whole_line(
        env: MindustryEnv, monkeypatch) -> None:
    """Queued anyway, the line stops where the copper runs out, and the half beside the
    drill makes it read as linked, so it is never asked for again."""
    env.reset()
    size = 16
    spatial = np.zeros((len(env._bridge.channels), size, size), dtype=np.uint8)
    drill = [(x, y) for x in (4, 5) for y in (4, 5)]
    flags = ground(size, building=drill, ours=drill)
    import base64
    monkeypatch.setattr(env._bridge, "ground", lambda: {
        "width": size, "height": size, "flags": base64.b64encode(flags.tobytes()).decode()})
    asked = []
    monkeypatch.setattr(env._bridge, "act",
                        lambda action: asked.append(action) or {"action": {"applied": True}})
    obs = {"spatial": spatial, "map_width": size, "map_height": size, "window_origin": (0, 0),
           "core_x": 12, "core_y": 12, "drills": [[4, 4, 0]]}

    env._last_obs = {**obs, "items": {"copper": 5}}
    env._link(4, 4)
    assert not asked, "nothing queued"
    assert env._last_connect["reason"] == "can't afford"
    need = env._last_connect["asked"]
    assert need > 5

    queued = {"plan_queue": [[1, 1, "conveyor", 7, 0]]}
    env._last_obs = {**obs, "items": {"copper": need}, "unit": queued}
    env._link(4, 4)
    assert not asked, "what the queue still owes is not there to spend"
    assert env._last_connect["committed"] == 7

    env._last_obs = {**obs, "items": {"copper": need}}
    env._link(4, 4)
    assert len(asked) == need, "exactly enough is enough"



@pytest.mark.parametrize("drills, reason", [([], "no drill"), ([[4, 4, 1]], "already linked")])
def test_link_names_a_drill_that_needs_it(env: MindustryEnv, drills, reason) -> None:
    env.reset()
    channels = env._bridge.channels
    spatial = np.zeros((len(channels), 8, 8), dtype=np.uint8)
    env._last_obs = {"spatial": spatial, "map_width": 8, "map_height": 8,
                     "window_origin": (0, 0), "core_x": 6, "core_y": 6, "drills": drills}
    env._link(4, 4)
    assert env._last_connect == {"applied": False, "type": "link", "reason": reason}


def test_the_unlinked_mask_marks_drill_anchors_in_the_window(env: MindustryEnv) -> None:
    obs = {"window_origin": (10, 20), "drills": [[12, 23, 0], [13, 21, 1], [99, 99, 0]]}
    mask = env._unlinked(obs, (8, 8))
    assert {(int(x), int(y)) for y, x in zip(*np.nonzero(mask))} == {(2, 3)}, (
        "only the unlinked drill inside the window, in window coordinates")
