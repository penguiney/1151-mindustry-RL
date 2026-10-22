# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from gamma import tasks
from gamma.env import MindustryEnv
from gamma.alpha import AlphaPolicy
from gamma.policies import run_episode

env = MindustryEnv(tasks.T1_COPPER, jar="bridge/build/libs/mindustry-ai-bridge.jar")
print(run_episode(env, AlphaPolicy(env)))
env.close()