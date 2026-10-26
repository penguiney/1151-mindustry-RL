"""Watch a checkpoint play, on the same dashboard as training, without training it.

    python tools/watch_beta.py                                  # checkpoints/beta.pt
    python tools/watch_beta.py checkpoints/exp15/beta.pt --matches 2 --seed 1,42

Every match here is a showcase match from tools/train_beta.py: it plays the policy at a
speed a person can follow and its experience goes nowhere. There is no learner, so no checkpoint and journal update.
The weights are loaded once and never change.

Ports, server directories and the dashboard port are all apart from training's, so this
can run beside a training run. It still takes CPU from one.
"""

from __future__ import annotations

import argparse
import time
import webbrowser
from pathlib import Path

from gamma import tasks
from gamma.cleanup import kill_servers
from gamma.monitor import TrainingMonitor
from gamma.net import PolicyNet
from gamma.ppo import PPOConfig, load_weights
from gamma.window import DEFAULT_SIZE
from tools.evaluate import seed_list
from tools.extract_sprites import ensure_assets
from tools.train_beta import EnvWorker, ensure_jar, showcase_policy

#: Clear of training's 7920/6920 and evaluate's 7910, for up to thirty matches.
BRIDGE_PORT_BASE = 7960
WATCH_GAME_PORT_BASE = 6960


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint", type=Path, nargs="?", default=Path("checkpoints/beta.pt"))
    parser.add_argument("--matches", type=int, default=1)
    parser.add_argument("--speed", default="2",
                        help="simulation speed, 1 is realtime, 'max' is uncapped")
    parser.add_argument("--task", default="T1_copper", choices=sorted(tasks.CURRICULUM))
    parser.add_argument("--embodied", action="store_true", default=True)
    parser.add_argument("--direct", dest="embodied", action="store_false",
                        help="edit the world directly instead of flying a unit")
    parser.add_argument("--window", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--channels", type=int, default=14)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--worlds", type=int, default=0)
    parser.add_argument("--seed", type=seed_list, default=None,
                        help="pin the world, as in train_beta: one seed or a comma list")
    # Empty by default, as the runs here are trained with `--designs=`: a library adds a
    # `stamp` type the checkpoint never had, and its zeroed head row is not a no-op.
    parser.add_argument("--designs", default="",
                        help="design library, only for a checkpoint trained with one")
    parser.add_argument("--port", type=int, default=8810)
    parser.add_argument("--root", default="mindustry-watch")
    parser.add_argument("--record", action="store_true", default=True,
                        help="archive the best episodes under --replays")
    parser.add_argument("--no-record", dest="record", action="store_false")
    parser.add_argument("--replays", default="replays/watch")
    parser.add_argument("--scene-fps", type=int, default=10)
    parser.add_argument("--no-open", dest="open", action="store_false", default=True)
    args = parser.parse_args()
    # What EnvWorker reads for a showcase match's speed.
    args.watch_speed = args.speed

    if not args.checkpoint.is_file():
        raise SystemExit(f"no checkpoint at {args.checkpoint}")

    monitor = TrainingMonitor(title=f"watch {args.checkpoint} / {args.task}")
    url = monitor.serve(args.port, strict=True)
    kill_servers()
    ensure_jar()
    ensure_assets()
    print(f"dashboard: {url}", flush=True)
    if args.open:
        webbrowser.open(url)

    ports = (BRIDGE_PORT_BASE, WATCH_GAME_PORT_BASE)
    workers = [EnvWorker(i, args, monitor, None, showcase=True, ports=ports)
               for i in range(args.matches)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.ready.wait()
    alive = [w for w in workers if w.failed is None]
    if not alive:
        raise SystemExit("no environment started")

    observation, info = alive[0].results.get()
    layout = alive[0].env
    device = PPOConfig().device
    net = PolicyNet(
        channels=observation["spatial"].shape[0],
        window=args.window,
        globals_size=observation["global"].shape[0],
        n_types=len(info["action_mask"]["type"]),
        position_set_of_type=layout.position_set_of_type,
        block_of_type=layout.block_of_type,
        rotation_of_type=layout.rotation_of_type,
        n_blocks=len(info["action_mask"]["block"]),
    )
    saved = load_weights(net, args.checkpoint, device)
    net.to(device).eval()
    generation = saved.get("updates") if isinstance(saved, dict) else None
    print(f"playing {args.checkpoint}"
          + (f" (generation {generation})" if generation is not None else ""), flush=True)

    act = showcase_policy(net, args.window, device)
    for worker in alive:
        worker.act = act

    print(f"{len(alive)} matches at speed {args.speed}; in the game: Mindustry -> Play -> "
          f"Join Game -> 127.0.0.1:{WATCH_GAME_PORT_BASE}+match. Ctrl+C to stop", flush=True)
    try:
        while any(w.thread.is_alive() for w in alive) and not monitor.stopping.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopping...", flush=True)
    finally:
        for worker in workers:
            worker.stop.set()
        for worker in workers:
            worker.thread.join(timeout=30)
        monitor.stop()


if __name__ == "__main__":
    main()
