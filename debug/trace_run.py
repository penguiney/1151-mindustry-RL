"""trace_run.py: run one episode of a checkpoint and report what was built, what vanished,
and whether the torn / churn terms ever fired.
 
Usage (from any folder; relative paths are taken from the project root):
    python debug/trace_run.py checkpoints/beta.pt
"""
# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import sys
from collections import Counter
from pathlib import Path
 
import torch
 
from gamma import tasks
from gamma.env import MindustryEnv
from gamma.window import LocalWindow
from gamma.net import PolicyNet
from gamma.ppo import PPOConfig
from tools.evaluate import network_policy
 
CHECKPOINT = Path(sys.argv[1] if len(sys.argv) > 1 else "checkpoints/beta.pt")
PORT = 7700
WINDOW = 48          # must match the --window used in training
CHANNELS = None      # must match the --channels used in training
TASK = "T1_copper"
 
 
def stat(raw, key):
    return int(raw.get("stats", {}).get(key, 0))
 
 
def total(d):
    return sum(int(v) for v in (d or {}).values())
 
 
def main():
    jar = str(next((Path("bridge") / "build" / "libs").glob("*.jar")))
    task = tasks.get(TASK)
    env = LocalWindow(
        MindustryEnv(task, server_dir="server-trace", bridge_port=PORT, game_port=PORT - 1000,
                     jar=jar, embodied=True, speed="max", evaluating=True, designs=(),
                     window=WINDOW),
        size=WINDOW, channels=CHANNELS,
    )
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
 
    # Reward terms, evaluated separately so a term that never fires is visible.
    torn_term = getattr(tasks, "_torn", None)
    churn_term = getattr(tasks, "_churn", None)
 
    raw = info["raw"]
    prod_hist = [total(raw.get("produced"))]
    action_counts = Counter()
    vanish_steps = []
    n_placed = n_vanished = n_decon_counter = 0
    torn_fired = churn_fired = 0
    max_churn = 0
 
    print("step  action        detail")
    for step in range(task.max_steps):
        action = policy(observation, info)
        chosen = None
        for holder in (env, getattr(env, "env", None)):
            try:
                chosen = holder.action_types[int(action[0])]
                break
            except Exception:
                continue
        if step == 0:
            print("first action array:", action,
                  "| action_types:", getattr(env, "action_types", None)
                  or getattr(getattr(env, "env", None), "action_types", None))
        prev = raw
        observation, reward, term, trunc, info = env.step(action)
        raw = info["raw"]

        act = raw.get("action") or {}
        kind = chosen if chosen is not None else act.get("type")
        action_counts[(kind, bool(act.get("applied")))] += 1
        
        d_decon = stat(raw, "buildings_deconstructed") - stat(prev, "buildings_deconstructed")
        d_placed = total(raw.get("placed")) - total(prev.get("placed"))
        built_prev, built_now = int(prev.get("built", 0)), int(raw.get("built", 0))
        # Buildings that disappeared this step, whatever the reason or the engine's counter.
        gone = max(0, built_prev + d_placed - built_now)
        d_cu = int(raw["items"].get("copper", 0)) - int(prev["items"].get("copper", 0))
        churn = raw.get("churn")
        max_churn = max(max_churn, int(churn or 0))
 
        r_torn = torn_term(-0.1)(prev, raw) if torn_term else None
        r_churn = churn_term(-2.0)(prev, raw) if churn_term else None
        if r_torn:
            torn_fired += 1
        if r_churn:
            churn_fired += 1
 
        n_placed += d_placed
        n_vanished += gone
        n_decon_counter += d_decon
        prod_hist.append(total(raw.get("produced")))
 
        if gone:
            vanish_steps.append(step)
            print(f"{step:3d}  {str(kind):<12} VANISHED {gone} (built {built_prev}+{d_placed}->{built_now}) "
                  f"decon_counter+{d_decon} churn={churn} torn_r={r_torn} churn_r={r_churn} "
                  f"copper{d_cu:+d} reward={reward:+.3f}")
        elif d_decon or kind in ("break", "demolish"):
            print(f"{step:3d}  {str(kind):<12} applied={act.get('applied')} reason={act.get('reason')} "
                  f"decon_counter+{d_decon} torn_r={r_torn} copper{d_cu:+d} reward={reward:+.3f}")
        elif kind == "connect":
            print(f"{step:3d}  connect      applied={act.get('applied')} laid={act.get('laid')} "
                  f"reason={act.get('reason')} placed+{d_placed} copper{d_cu:+d} reward={reward:+.3f}")
 
        if term or trunc:
            break
 
    useful = sum(1 for s in vanish_steps
                 if s + 11 < len(prod_hist) and prod_hist[s + 11] > prod_hist[s + 1])
 
    print("\n--- summary ---")
    print(f"steps {step + 1}, placed {n_placed}, vanished {n_vanished}, "
          f"engine deconstructed counter {n_decon_counter}")
    print(f"steps with vanished buildings: {len(vanish_steps)}, "
          f"of which produced rose within 10 steps: {useful}")
    print(f"_torn fired on {torn_fired} steps, _churn fired on {churn_fired} steps, "
          f"max obs['churn'] seen {max_churn}")
    print(f"final produced {prod_hist[-1]}, final copper {raw['items'].get('copper', 0)}")
    print("action counts (type, applied): " + ", ".join(
        f"{k}={v}" for k, v in sorted(action_counts.items(), key=lambda kv: -kv[1])))
    env.close()
 
 
if __name__ == "__main__":
    main()
 