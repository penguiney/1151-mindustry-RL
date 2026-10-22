# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from gamma import tasks
from gamma.env import MindustryEnv
from gamma.alpha import AlphaPolicy

env = MindustryEnv(tasks.T1_COPPER, jar="bridge/build/libs/mindustry-ai-bridge.jar")
policy = AlphaPolicy(env)


def total(d):
    return sum(int(v) for v in (d or {}).values())


def run_once(label):
    print(f"--- {label} ---")
    observation, info = env.reset()
    raw = env._last_obs
    print("drilled at reset:", raw.get("drilled"))

    last = None
    prev_total = 0
    monotonic = True
    max_gap = None  # produced - drilled, 應該 <= 0 的意思是 drilled >= produced

    for i in range(env.task.max_steps):
        action = policy.act(observation, info)
        observation, reward, terminated, truncated, info = env.step(action)
        raw = info.get("raw", env._last_obs)

        drilled = raw.get("drilled", {})
        produced = raw.get("produced", {})

        if total(drilled) < prev_total:
            monotonic = False
            print(f"  !! step {i}: drilled 變小了 {prev_total} -> {total(drilled)}")
        prev_total = total(drilled)

        for item, amount in produced.items():
            gap = int(amount) - int(drilled.get(item, 0))
            max_gap = gap if max_gap is None else max(max_gap, gap)

        snap = (dict(drilled), dict(produced), dict(raw.get("placed", {})))
        if snap != last:
            print(f"  step {i:3d}  drilled={snap[0]}  produced={snap[1]}  placed={snap[2]}")
            last = snap

        if terminated or truncated:
            break

    print("  final drilled:", raw.get("drilled"))
    print("  單調遞增:", monotonic)
    print("  max(produced - drilled):", max_gap, "(<= 0 才對, None 代表沒有 produced)")


run_once("episode 1")
run_once("episode 2 (重置後應從 {} 開始)")
env.close()