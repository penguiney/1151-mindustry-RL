"""How much copper each world seed puts near the core, to choose training and test seeds.

    python -m tools.scan_seeds 1-30
    python -m tools.scan_seeds 1,10000,42 --item lead

Every seed of a named map shares its terrain and its core; only the ore moves. So what
separates an easy seed from a hard one is how far the core is from the ore, and a pool
worth training on mixes the near with the far. Read once per seed from a fresh load, on
its own ports, so it can run beside a training run.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from gamma import tasks
from gamma.env import MindustryEnv

RADII = (12, 24, 40, 60)


def seeds_from(text: str) -> list[int]:
    """`1-30`, `1,10000,42`, or both: `1-5,42`."""
    seeds: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part[1:]:
            low, high = part.split("-", 1) if not part.startswith("-") else (part, part)
            seeds.extend(range(int(low), int(high) + 1))
        elif part:
            seeds.append(int(part))
    return seeds


def survey(raw: dict, channels: list[str], item: str) -> dict[int, tuple[int, int]]:
    """Per radius round the core: (tiles of the ore, 2x2 drill squares entirely on it)."""
    spatial = raw["spatial"]
    ore = spatial[channels.index(f"ore_{item}")] > 0
    free = ((spatial[channels.index("buildable")] > 0) & (spatial[channels.index("block")] == 0)
            & (spatial[channels.index("solid")] == 0))
    full = np.zeros_like(ore)
    full[:-1, :-1] = (ore[:-1, :-1] & ore[1:, :-1] & ore[:-1, 1:] & ore[1:, 1:]
                      & free[:-1, :-1] & free[1:, :-1] & free[:-1, 1:] & free[1:, 1:])
    height, width = ore.shape
    ys, xs = np.mgrid[0:height, 0:width]
    distance = np.abs(xs - int(raw["core_x"])) + np.abs(ys - int(raw["core_y"]))
    return {r: (int((ore & (distance <= r)).sum()), int((full & (distance <= r)).sum()))
            for r in RADII}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("seeds", type=seeds_from, help="e.g. 1-30 or 1,10000,42")
    parser.add_argument("--task", default="T1_copper", choices=sorted(tasks.CURRICULUM))
    parser.add_argument("--item", default="copper")
    parser.add_argument("--port", type=int, default=7950)
    parser.add_argument("--root", default="mindustry-scan")
    args = parser.parse_args()

    jar = str(next((Path("bridge") / "build" / "libs").glob("*.jar")))
    task = tasks.get(args.task)
    env = MindustryEnv(task, server_dir=args.root, bridge_port=args.port,
                       game_port=args.port - 1000, jar=jar, embodied=False)
    print(f"{args.item} round the core: tiles / full 2x2 drill squares, by Manhattan radius")
    print(f"{'seed':>10}  " + "  ".join(f"{'r' + str(r):>11}" for r in RADII))
    try:
        for seed in args.seeds:
            env.task = replace(task, world_seed=seed, world_seeds=())
            env.reset()
            rows = survey(env._last_obs, env._bridge.channels, args.item)
            print(f"{seed:>10}  " + "  ".join(f"{t:>5} / {f:<3}" for t, f in rows.values()),
                  flush=True)
    finally:
        env.close()


if __name__ == "__main__":
    main()
