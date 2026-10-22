"""trace_belt.py: do buildings really vanish, or does only the recording say so?
 
Runs a checkpoint for one or more episodes and measures the same thing two ways every step:
 
  window   the agent's own buildings in the observation window (the `block_ally` channel,
           scaffolds included): a tile that held one last step and is empty now has vanished.
  scene    SceneEncoder's `removed` list, which is what the replays and the dashboard show.
 
If the two agree, buildings really are disappearing. If the scene reports removals while the
window still shows a building on that tile ("phantom"), the recording is wrong, not the game.
 
Also prints, for real vanishings, the distance to the unit, its build range, the build-plan
queue before and after, the action and the copper change.
 
`scene()` is a delta since its last call, so this script is its only caller: it turns on
capture_scene itself and does not run alongside the recorder on the same server.
 
Usage (from any folder; relative paths are taken from the project root):
    python debug/trace_belt.py checkpoints/beta.pt [episodes]
"""
# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
 
import numpy as np
import torch
 
from gamma import tasks
from gamma.env import MindustryEnv
from gamma.window import LocalWindow
from gamma.net import PolicyNet
from gamma.ppo import PPOConfig
from tools.evaluate import network_policy
 
CHECKPOINT = Path(sys.argv[1] if len(sys.argv) > 1 else "checkpoints/beta.pt")
EPISODES = int(sys.argv[2]) if len(sys.argv) > 2 else 1
PORT = 7710          # not 7700, in case a trace_run server is still alive
WINDOW = 48          # must match the --window used in training
CHANNELS = None      # must match the --channels used in training
TASK = "T1_copper"
 
 
def total(d):
    return sum(int(v) for v in (d or {}).values())
 
 
def decode_kind(env, action):
    for holder in (env, getattr(env, "env", None)):
        try:
            return holder.action_types[int(action[0])]
        except Exception:
            continue
    return None
 
 
def bridge_of(env):
    for holder in (env, getattr(env, "env", None)):
        bridge = getattr(holder, "_bridge", None)
        if bridge is not None:
            return bridge
    return None
 
 
def ally_tiles(raw, channels):
    """World coordinates of every tile in the window holding an ally building, plus the
    window rectangle (x0, y0, x1, y1) in world coordinates."""
    spatial = raw.get("spatial")
    if spatial is None or "block_ally" not in channels:
        return None, None
    plane = np.asarray(spatial[channels.index("block_ally")])
    ox, oy = (raw.get("window_origin") or (0, 0))
    ox, oy = int(ox), int(oy)
    rows, cols = plane.shape
    tiles = {(ox + int(x), oy + int(y)) for y, x in np.argwhere(plane > 0)}
    return tiles, (ox, oy, ox + cols, oy + rows)
 
 
def inside(rect, tile):
    return rect[0] <= tile[0] < rect[2] and rect[1] <= tile[1] < rect[3]
 
 
def unit_state(raw):
    u = raw.get("unit") or {}
    return (float(u.get("x", 0.0)), float(u.get("y", 0.0)),
            float(u.get("build_range", 0.0)), int(u.get("plans", 0)),
            bool(u.get("building", False)))
 
 
def scene_removed(info, raw):
    """Tiles the scene reports as removed this step, as world (x, y)."""
    scene = info.get("scene")
    if not isinstance(scene, dict):
        return None
    width = int(raw.get("map_width", 0)) or 1
    return [(int(k) % width, int(k) // width) for k in (scene.get("removed") or [])]
 
 
def run_episode(env, policy, task, channels, stats):
    observation, info = env.reset()
    raw = info["raw"]
    tiles_prev, rect_prev = ally_tiles(raw, channels)
    if tiles_prev is None:
        #print("no spatial / block_ally in raw: cannot trace (channels:", channels, ")")
        return False
 
    _, _, brange, plans_prev, _ = unit_state(raw)
    placed_prev = total(raw.get("placed"))
    #print("step  action     window  scene  phantom  dist(max)  range  plans    copper  detail")
 
    for step in range(task.max_steps):
        action = policy(observation, info)
        kind = decode_kind(env, action)
        prev = raw
        observation, reward, term, trunc, info = env.step(action)
        raw = info["raw"]
 
        tiles_now, rect_now = ally_tiles(raw, channels)
        ux, uy, brange, plans_now, building = unit_state(raw)
        act = raw.get("action") or {}
        d_cu = int(raw["items"].get("copper", 0)) - int(prev["items"].get("copper", 0))
        d_placed = total(raw.get("placed")) - placed_prev
        placed_prev = total(raw.get("placed"))
 
        # A tile counts only if it was visible in both windows, so moving the window is
        # never mistaken for a building vanishing.
        both = lambda t: inside(rect_prev, t) and inside(rect_now, t)
        vanished = [t for t in tiles_prev if both(t) and t not in tiles_now]
        appeared = [t for t in tiles_now if both(t) and t not in tiles_prev]
 
        reported = scene_removed(info, raw)
        if reported is not None:
            stats["scene_steps"] += 1
            stats["scene_all"] += len(reported)
        visible = [t for t in (reported or []) if inside(rect_now, t)]
        phantom = [t for t in visible if t in tiles_now]          # scene says gone, window says there
        agree = [t for t in visible if t not in tiles_now]
 
        stats["steps"] += 1
        stats["appeared"] += len(appeared)
        stats["decon_counter"] += (int(raw.get("stats", {}).get("buildings_deconstructed", 0))
                                   - int(prev.get("stats", {}).get("buildings_deconstructed", 0)))
        stats["kinds"][kind] += 1
        stats["scene_visible"] += len(visible)
        stats["phantom"] += len(phantom)
        stats["agree"] += len(agree)
        stats["window_only"] += len([t for t in vanished if t not in set(visible)])
 
        if vanished:
            dists = [math.hypot(t[0] - ux, t[1] - uy) for t in vanished]
            far = sum(1 for d in dists if d > brange > 0)
            stats["vanish_steps"] += 1
            stats["vanished"] += len(vanished)
            stats["far"] += far
            stats["queue_drop_steps"] += int(plans_now < plans_prev)
            stats["by_kind"][kind] += 1
            stats["copper_on_vanish"] += d_cu
            for t in vanished:
                stats["per_tile"][t] += 1
            dist_text, far_text = f"{max(dists):9.1f}", f"far={far}"
        else:
            dist_text, far_text = f"{'-':>9}", ""
 
        #if vanished or visible:
        #    print(f"{step:4d}  {str(kind):<9} {len(vanished):6d} {len(visible):6d} "
         #         f"{len(phantom):8d}  {dist_text}  {brange:5.1f}  {plans_prev:>3}->{plans_now:<3} "
        #          f"{d_cu:+7d}  {far_text} placed+{d_placed} applied={act.get('applied')}")
 
        tiles_prev, rect_prev, plans_prev = tiles_now, rect_now, plans_now
        if term or trunc:
            break
 
    stats["final_copper"] = int(raw["items"].get("copper", 0))
    stats["final_produced"] = total(raw.get("produced"))
    return True
 
 
def main():
    jar = str(next((Path("bridge") / "build" / "libs").glob("*.jar")))
    task = tasks.get(TASK)
    env = LocalWindow(
        MindustryEnv(task, server_dir="server-trace-belt", bridge_port=PORT, game_port=PORT - 1000,
                     jar=jar, embodied=True, speed="max", evaluating=True, designs=(),
                     window=WINDOW, capture_scene=True),
        size=WINDOW, channels=CHANNELS,
    )
    try:
        observation, info = env.reset()
        net = PolicyNet(
            channels=observation["spatial"].shape[0], window=WINDOW,
            globals_size=observation["global"].shape[0],
            n_types=len(info["action_mask"]["type"]), n_blocks=len(info["action_mask"]["block"]),
            position_set_of_type=env.position_set_of_type,
            block_of_type=env.block_of_type, rotation_of_type=env.rotation_of_type,
        )
        device = PPOConfig().device
        net.load_state_dict(torch.load(CHECKPOINT, map_location=device)["net"])
        net.to(device).eval()
        policy = network_policy(net, device)
 
        bridge = bridge_of(env)
        channels = list(getattr(bridge, "channels", []) or [])
        #print("channels:", channels)
 
        stats = {"steps": 0, "appeared": 0, "decon_counter": 0, "vanish_steps": 0,
                 "vanished": 0, "far": 0, "queue_drop_steps": 0, "copper_on_vanish": 0,
                 "scene_steps": 0, "scene_all": 0, "scene_visible": 0, "phantom": 0,
                 "agree": 0, "window_only": 0,
                 "kinds": Counter(), "by_kind": Counter(), "per_tile": defaultdict(int)}
 
        for episode in range(EPISODES):
            #print(f"\n=== episode {episode + 1}/{EPISODES} ===")
            if not run_episode(env, policy, task, channels, stats):
                return
 
        print("\n--- summary ---")
        print(f"steps {stats['steps']}, tiles that appeared {stats['appeared']}, "
              f"engine deconstructed counter {stats['decon_counter']}")
        print(f"WINDOW: tiles vanished {stats['vanished']} over {stats['vanish_steps']} steps")
        if stats["scene_steps"]:
            print(f"SCENE : removed entries {stats['scene_all']} "
                  f"({stats['scene_visible']} inside the window)")
            print(f"        of those, tile really empty in the window: {stats['agree']}, "
                  f"still has an ally building (phantom): {stats['phantom']}")
            print(f"        vanished in the window but not reported by the scene: "
                  f"{stats['window_only']}")
        else:
            print("SCENE : info['scene'] was never present (capture_scene not honoured)")
        if stats["vanished"]:
            print(f"vanished tiles beyond the unit's build range: {stats['far']} "
                  f"({stats['far'] / stats['vanished']:.0%})")
            print(f"vanish steps where the plan queue shrank: {stats['queue_drop_steps']} "
                  f"of {stats['vanish_steps']}")
            print(f"net copper change over vanish steps: {stats['copper_on_vanish']:+d}")
            print("vanish steps by action:", dict(stats["by_kind"]))
            worst = sorted(stats["per_tile"].items(), key=lambda kv: -kv[1])[:5]
            print("tiles vanished most often:", worst)
        print("actions overall:", dict(stats["kinds"]))
        print(f"last episode: final copper {stats['final_copper']}, "
              f"produced {stats['final_produced']}")
    finally:
        env.close()
 
 
if __name__ == "__main__":
    main()
 