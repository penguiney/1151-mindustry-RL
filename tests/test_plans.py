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
    assert fields[14:] == ["plans", "plan_dx", "plan_dy"]


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
