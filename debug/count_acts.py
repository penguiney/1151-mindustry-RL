# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import glob
import gzip
import json
from collections import Counter

for path in sorted(glob.glob("replays/live/*/*.jsonl.gz")):
    counts = Counter()
    first = None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    frame = json.loads(line)
                except Exception:
                    continue
                if first is None:
                    first = sorted(frame.keys())
                act = frame.get("act")
                if isinstance(act, dict):
                    counts[act.get("t")] += 1
    except EOFError:
        pass  # .pending 檔還在寫，結尾不完整
    print(path.split("live\\")[-1], dict(counts))
    if first and "pending" not in path and path.endswith("pos001344.jsonl.gz"):
        print("  frame keys:", first)