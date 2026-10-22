# 讓腳本在任何資料夾都能執行：切到專案根目錄，並讓 gamma/tools 可被 import
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import gzip, json
from collections import defaultdict

path = "replays/live/match0/ep000012-pos004655.jsonl.gz"
with gzip.open(path, "rt", encoding="utf-8") as f:
    frames = [json.loads(l) for l in f][1:]

tl = defaultdict(list)
for i, fr in enumerate(frames):
    sc = fr.get("scene") or {}
    pl = sc.get("placed") or []
    for k in range(0, len(pl) - 5, 6):
        tl[pl[k]].append((i, "placed"))
    be = sc.get("belts") or []
    for k in range(0, len(be) - 3, 4):
        tl[be[k]].append((i, "belt"))
    for r in sc.get("removed") or []:
        tl[r].append((i, "REMOVED"))

counts = sorted(((sum(1 for _, t in v if t == "REMOVED"), k) for k, v in tl.items()), reverse=True)
for n, k in counts[:5]:
    seq = [f"{s}:{t}" for s, t in tl[k]][:24]
    print(k, "removed", n, "times |", " ".join(seq))