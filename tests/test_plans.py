"""The unit's build queue: shown to the policy, and paid for before anything new is.

The queue arrives as `unit.plan_queue`, [x, y, block, copper, breaking]. Only the last
test needs a server, to see the bridge actually send it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gamma import env as env_module
from gamma import tasks
from gamma.env import DRILL, GLOBAL_FIELDS, MindustryEnv, committed_copper, nearest_plan


def unit(x: float = 100, y: float = 40, *queue) -> dict:
    return {"x": x, "y": y, "plans": len(queue), "plan_queue": [list(p) for p in queue]}


def test_the_nearest_plan_whatever_ordered_it() -> None:
    queue = [(140, 40, "conveyor", 1, 0), (95, 43, "router", 3, 0), (60, 10, "", 0, 1)]
    assert nearest_plan(unit(100, 40, *queue)) == (-5, 3)
    assert nearest_plan(unit(100, 40)) == (0, 0), "nothing queued, nowhere to go"


def test_what_the_queue_will_still_take() -> None:
    queue = [(1, 1, "conveyor", 1, 0), (2, 1, "mechanical-drill", 12, 0), (3, 1, "", 0, 1)]
    assert committed_copper(unit(0, 0, *queue)) == 13
    assert committed_copper({}) == 0


def test_the_queue_is_in_the_observation() -> None:
    env = MindustryEnv(tasks.T1_COPPER, bridge_port=7004)
    fields = [name for name, _ in GLOBAL_FIELDS]
    scale = dict(GLOBAL_FIELDS)
    queue = [(130, 40, "conveyor", 1, 0), (110, 30, "conveyor", 1, 0)]
    encoded = env._encode({"spatial": np.zeros((3, 4, 4), dtype=np.uint8),
                           "unit": unit(100, 40, *queue)})["global"]
    assert encoded[fields.index("plans")] == 2 / scale["plans"]
    assert encoded[fields.index("plan_dx")] == 10 / scale["plan_dx"]
    assert encoded[fields.index("plan_dy")] == -10 / scale["plan_dy"]


def test_free_copper_is_what_the_queue_has_not_spoken_for() -> None:
    env = MindustryEnv(tasks.T1_COPPER, bridge_port=7004)
    fields = [name for name, _ in GLOBAL_FIELDS]
    queue = [(130, 40, "conveyor", 1, 0), (110, 30, "mechanical-drill", 12, 0)]
    encoded = env._encode({"spatial": np.zeros((3, 4, 4), dtype=np.uint8),
                           "items": {"copper": 50}, "unit": unit(100, 40, *queue)})["global"]
    assert encoded[fields.index("free_copper")] == (50 - 13) / dict(GLOBAL_FIELDS)["free_copper"]


def test_a_drill_is_paid_for_out_of_what_the_queue_has_not_spoken_for() -> None:
    env = MindustryEnv(tasks.T1_COPPER, bridge_port=7004)
    drill = np.array([env.action_types.index(DRILL), 0, 5, 5, 0])

    env._last_obs = {"items": {"copper": 20}, "unit": unit(0, 0, (9, 9, "conveyor", 10, 0))}
    assert env._decode(drill) is None
    assert env._last_connect["reason"] == "can't afford"
    assert env._last_connect["committed"] == 10

    env._last_connect = None
    env._last_obs = {"items": {"copper": 20}, "unit": unit(0, 0, (9, 9, "conveyor", 8, 0))}
    assert env._decode(drill)["block"] == "mechanical-drill", "20 - 8 pays for 12"


def test_new_fields_come_last_so_an_old_checkpoint_widens_into_them() -> None:
    """`load_weights` copies the overlap from the front; a field inserted in the middle
    would shift every column after it onto the wrong input."""
    fields = [name for name, _ in env_module.GLOBAL_FIELDS]
    assert fields[12:14] == ["core_dx", "core_dy"]
    assert fields[14:] == ["plans", "plan_dx", "plan_dy", "free_copper"]


@pytest.fixture(scope="module")
def embodied(tmp_path_factory: pytest.TempPathFactory, bridge_jar: Path):
    """A unit to queue plans for; the session's environment has none."""
    environment = MindustryEnv(tasks.T1_COPPER, server_dir=str(tmp_path_factory.mktemp("plans")),
                               bridge_port=7864, game_port=6864, jar=str(bridge_jar),
                               embodied=True)
    try:
        yield environment
    finally:
        environment.close()


@pytest.fixture(scope="module")
def direct(tmp_path_factory: pytest.TempPathFactory, bridge_jar: Path):
    """Blocks placed at once, so a line is finished the step it is ordered."""
    environment = MindustryEnv(tasks.T1_COPPER, server_dir=str(tmp_path_factory.mktemp("connect")),
                               bridge_port=7866, game_port=6866, jar=str(bridge_jar),
                               embodied=False, window=0)
    try:
        yield environment
    finally:
        environment.close()


def copper_spot(env: MindustryEnv, raw: dict) -> tuple[int, int]:
    """A free 2x2 square all on copper with two free tiles east of it, nearest the core
    without touching it."""
    spatial = raw["spatial"]
    channels = env._bridge.channels
    ox, oy = raw.get("window_origin") or (0, 0)
    ore = spatial[channels.index("ore_copper")] > 0
    free = ((spatial[channels.index("buildable")] > 0) & (spatial[channels.index("block")] == 0)
            & (spatial[channels.index("solid")] == 0))
    ok = ore & free
    full = np.zeros_like(ok)
    full[:-1, :-3] = (ok[:-1, :-3] & ok[1:, :-3] & ok[:-1, 1:-2] & ok[1:, 1:-2]
                      & free[:-1, 2:-1] & free[:-1, 3:])
    ys, xs = np.nonzero(full)
    cx, cy = int(raw["core_x"]), int(raw["core_y"])
    spots = sorted((abs(x + ox - cx) + abs(y + oy - cy), int(x + ox), int(y + oy))
                   for x, y in zip(xs, ys))
    return next((x, y) for d, x, y in spots if d > 6)


def drill_at(raw: dict, x: int, y: int) -> list[int]:
    return next(d for d in raw["drills"] if (d[0], d[1]) == (x, y))


def test_a_drill_is_connected_the_step_its_line_is_finished(direct: MindustryEnv) -> None:
    """It used to wait for the drill to mine past its buffer as well."""
    _, info = direct.reset()
    x, y = copper_spot(direct, info["raw"])
    noop = np.zeros(5, dtype=np.int64)

    direct._bridge.act({"type": "place", "block": "mechanical-drill", "x": x, "y": y, "rotation": 0})
    *_, info = direct.step(noop)
    assert drill_at(info["raw"], x, y)[3] == 0, "nothing takes its ore yet"

    direct._link(x, y)
    assert direct._last_connect["applied"], direct._last_connect
    line = direct._last_connect["cells"]
    *_, info = direct.step(noop)
    raw = info["raw"]
    assert drill_at(raw, x, y)[3] == 1
    assert len(raw["connected_drills"]) == 1
    mined = raw.get("drill_mined", {}).get("copper", {}).get(raw["connected_drills"][0], 0)
    assert mined < 10, "credited before the buffer could have filled"
    tiles = raw["connected_drill_tiles"]["copper"]

    # Credited once: breaking the line takes nothing back.
    direct._bridge.act({"type": "break", "x": line[0][0], "y": line[0][1]})
    *_, info = direct.step(noop)
    assert drill_at(info["raw"], x, y)[3] == 1
    assert info["raw"]["connected_drill_tiles"]["copper"] == tiles


def test_a_belt_into_nothing_never_connects_a_drill(direct: MindustryEnv) -> None:
    _, info = direct.reset()
    x, y = copper_spot(direct, info["raw"])
    noop = np.zeros(5, dtype=np.int64)

    direct._bridge.act({"type": "place", "block": "mechanical-drill", "x": x, "y": y, "rotation": 0})
    for dx in (2, 3):
        placed = direct._bridge.act({"type": "place", "block": "conveyor", "x": x + dx, "y": y,
                                     "rotation": 0}).get("action") or {}
        assert placed.get("applied"), placed
    for _ in range(5):
        *_, info = direct.step(noop)
    linked, connected = drill_at(info["raw"], x, y)[2:4]
    assert linked == 1, "a belt stands beside it"
    assert connected == 0, "and leads nowhere"
    assert not info["raw"].get("connected_drill_tiles", {}).get("copper")


def test_the_queue_comes_back_with_where_each_plan_is_and_what_it_still_costs(
        embodied: MindustryEnv) -> None:
    """Only its length used to be sent, so where an unbuilt line lay was nobody's to know."""
    _, info = embodied.reset()
    raw = info["raw"]
    spatial = raw["spatial"]
    channels = embodied._bridge.channels
    ox, oy = raw.get("window_origin") or (0, 0)
    ux, uy = raw["unit"]["x"], raw["unit"]["y"]
    free = (spatial[channels.index("buildable")] > 0) & (spatial[channels.index("block")] == 0)
    ys, xs = np.nonzero(free)
    far = np.hypot(xs + ox - ux, ys + oy - uy) > raw["unit"]["build_range"] + 5
    assert far.any(), "somewhere out of reach to queue a belt"
    x, y = int(xs[far][0] + ox), int(ys[far][0] + oy)

    embodied._bridge.act({"type": "build", "block": "conveyor", "x": x, "y": y, "rotation": 0})
    _, _, _, _, info = embodied.step(np.zeros(5, dtype=np.int64))
    queue = [list(p) for p in info["raw"]["unit"]["plan_queue"]]
    assert [x, y, "conveyor", 1, 0] in queue
    assert committed_copper(info["raw"]["unit"]) >= 1
