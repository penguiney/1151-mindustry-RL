# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from gamma import tasks
from gamma.env import MindustryEnv

env = MindustryEnv(tasks.T1_COPPER, jar="bridge/build/libs/mindustry-ai-bridge.jar")
out = env.reset()
obs = out[0] if isinstance(out, tuple) else out   # Gymnasium 的 reset 通常回傳 (obs, info)
print(type(obs))
print(obs.keys() if hasattr(obs, "keys") else obs)
print(obs.get("unit"))


print(obs["global"])
print(getattr(env, "global_names", None) or getattr(env, "channels", None))

env.close()