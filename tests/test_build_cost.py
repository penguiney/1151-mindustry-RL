"""Actual construction payments, not orders, income, refunds or starting stock."""

from pathlib import Path
import shutil

import numpy as np
import pytest

from gamma import tasks
from gamma.bridge import Bridge
from gamma.server import ServerProcess, install_plugin


def test_cost_is_independent_of_income_and_inventory():
    reward = tasks.get("T2_copper_lead_income").reward
    before = {"items": {"copper": 300}, "build_copper_spent": 0,
              "drill_full_penalty_intervals": 0}
    after = {"items": {"copper": 300}, "produced": {"copper": 12},
             "build_copper_spent": 12, "drill_full_penalty_intervals": 0}
    assert reward(before, after) == pytest.approx(1.2 - 0.12)
    assert reward(after, after) == 0
    assert reward(after, {**after, "items": {"copper": 400}}) == 0


def test_old_bridge_is_rejected_instead_of_silently_ignoring_cost():
    with pytest.raises(RuntimeError, match="rebuild the bridge"):
        tasks.get("T2_copper_lead_income").reward({}, {})


@pytest.fixture(scope="module")
def cost_bridge(tmp_path_factory):
    """Use the existing local game jar; never download or touch training servers."""
    root = Path(__file__).resolve().parents[1]
    sources = list((root / "mindustry-beta").glob("env*/server-release.jar"))
    if not sources:
        pytest.skip("a local Mindustry server jar is required")
    folder = tmp_path_factory.mktemp("cost-server")
    shutil.copy2(sources[0], folder / "server-release.jar")
    install_plugin(folder, root / "bridge/build/libs/mindustry-ai-bridge.jar")
    with ServerProcess(folder, jvm_args=["-Dmindustryai.port=7898"], port=6898) as server:
        server.wait_for_bridge(7898, timeout=60)
        server.command("bridge-speed max", r"speed set")
        with Bridge(port=7898, tensor=True) as client:
            yield client


def free_tiles(client, obs):
    s = obs["spatial"]
    free = ((s[client.channels.index("buildable")] > 0)
            & (s[client.channels.index("block")] == 0)
            & (s[client.channels.index("solid")] == 0))
    ys, xs = np.where(free)
    return sorted(zip(xs.tolist(), ys.tolist()),
                  key=lambda p: (p[0] - obs["core_x"]) ** 2 + (p[1] - obs["core_y"]) ** 2)


@pytest.mark.parametrize("block,cost", [("conveyor", 1), ("router", 3),
                                         ("copper-wall", 6), ("mechanical-drill", 12)])
def test_direct_build_cost_and_reset(cost_bridge, block, cost):
    client = cost_bridge
    obs = client.reset("Ancient_Caldera", "survival", seed=1)
    assert obs["build_copper_spent"] == 0
    for x, y in free_tiles(client, obs):
        after = client.act({"type": "place", "block": block, "x": x, "y": y})
        if after["action"]["applied"]:
            break
    else:
        pytest.fail("no legal placement found")
    assert after["build_copper_spent"] == cost
    assert obs["items"]["copper"] - after["items"]["copper"] == cost
    refused = client.act({"type": "place", "block": block, "x": -1, "y": -1})
    assert not refused["action"]["applied"]
    assert refused["build_copper_spent"] == cost
    assert client.step(repeat=30)["build_copper_spent"] == cost
    assert client.reset("Ancient_Caldera", "survival", seed=1)["build_copper_spent"] == 0


def test_embodied_cost_follows_actual_construction(cost_bridge):
    client = cost_bridge
    obs = client.reset("Ancient_Caldera", "survival", seed=1)
    client.embody()
    x, y = free_tiles(client, obs)[0]
    queued = client.act({"type": "build", "block": "router", "x": x, "y": y, "rotation": 0})
    assert queued["action"]["applied"]
    assert queued["build_copper_spent"] == 0
    for _ in range(100):
        after = client.step(repeat=1)
        assert after["build_copper_spent"] == obs["items"]["copper"] - after["items"]["copper"]
        if after["build_copper_spent"] == 3:
            break
    assert after["build_copper_spent"] == 3
    assert client.step(repeat=60)["build_copper_spent"] == 3
