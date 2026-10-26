"""Watch policies play, side by side on the training dashboard, without training any.

    python tools/watch.py --policy checkpoints/exp14/beta.pt
    python tools/watch.py --policy checkpoints/exp14/beta.pt,checkpoints/exp13/beta.pt,alpha
    python tools/watch.py --policy checkpoints/exp14/beta.pt,random --matches 2 --seed 1,42

--policy is required: a comma list of checkpoints (any path ending in .pt) and built-in
policies (alpha, masked-random, random). Each one plays --matches matches of its own, so
the leaderboard compares policies rather than the luck of one policy's matches.

Every match is a showcase match from tools/train_beta.py: it plays on its own, at --speed
(uncapped unless told otherwise), and its experience goes nowhere. Nothing is trained and no checkpoint, journal or
history is written; replays are, unless --no-record.

Ports, server directories and the dashboard port are all apart from training's, so this
can run beside a training run. It still takes CPU from one.

To watch a recording in the real Mindustry client instead, see tools/watch_client.py.
"""

from __future__ import annotations

import argparse
import random
import threading
import time
import webbrowser
from pathlib import Path

from gamma import tasks
from gamma.alpha import AlphaPolicy
from gamma.alpha_embodied import EmbodiedAlphaPolicy
from gamma.cleanup import kill_servers
from gamma.monitor import TrainingMonitor
from gamma.net import PolicyNet
from gamma.policies import MaskedRandomPolicy, RandomPolicy
from gamma.ppo import PPOConfig, load_weights
from gamma.window import DEFAULT_SIZE
from tools.evaluate import seed_list
from tools.extract_sprites import ensure_assets
from tools.train_beta import EnvWorker, ensure_jar, showcase_policy

#: Clear of training's 7920/6920 and evaluate's 7910, for up to thirty matches.
BRIDGE_PORT_BASE = 7960
WATCH_GAME_PORT_BASE = 6960

#: Policies that need no checkpoint.
BUILT_IN = ("alpha", "masked-random", "random")


def policy_list(text: str) -> list[str]:
    """`a.pt,alpha` into its entries, each a checkpoint that exists or a built-in name."""
    entries = [part.strip() for part in text.split(",") if part.strip()]
    if not entries:
        raise argparse.ArgumentTypeError("no policy given")
    for entry in entries:
        if entry.endswith(".pt"):
            if not Path(entry).is_file():
                raise argparse.ArgumentTypeError(f"no checkpoint at {entry}")
        elif entry not in BUILT_IN:
            raise argparse.ArgumentTypeError(
                f"{entry!r} is neither a .pt checkpoint nor one of {', '.join(BUILT_IN)}")
    return entries


def label_of(entry: str) -> str:
    """A checkpoint by its folder and file (exp14/beta.pt), a built-in by its name."""
    if not entry.endswith(".pt"):
        return entry
    path = Path(entry)
    return f"{path.parent.name}/{path.name}" if path.parent.name else path.name


def checkpoint_policy(entry: str, worker: EnvWorker, observation, info, args, device):
    """The network for one checkpoint, shaped from a live observation, and its generation."""
    layout = worker.env
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
    saved = load_weights(net, entry, device)
    net.to(device).eval()
    generation = saved.get("updates") if isinstance(saved, dict) else None
    return showcase_policy(net, args.window, device), generation


def built_in_policy(name: str, worker: EnvWorker, seed: int):
    """A scripted or random baseline, reading the bare environment it plays in."""
    env = worker.env
    if name == "alpha":
        policy = EmbodiedAlphaPolicy(env) if env.embodied else AlphaPolicy(env)
    elif name == "masked-random":
        policy = MaskedRandomPolicy(env.action_space, seed=seed, env=env)
    else:
        policy = RandomPolicy(env.action_space, seed=seed)
    if hasattr(policy, "reset"):
        worker.on_reset = policy.reset
    return policy.act


class SeedSchedule:
    """The world of every episode, the same for every match.

    With seeds, episode i plays seeds[i mod n]. Without, each episode draws a fresh seed
    once and every match gets that one, so a side-by-side comparison is never between two
    different maps.
    """

    def __init__(self, seeds) -> None:
        self.seeds = tuple(seeds or ())
        self.drawn: dict[int, int] = {}
        self.lock = threading.Lock()
        self.rng = random.Random()

    def __call__(self, episode: int) -> int:
        if self.seeds:
            return self.seeds[episode % len(self.seeds)]
        with self.lock:
            if episode not in self.drawn:
                self.drawn[episode] = self.rng.randrange(1, 1_000_000)
            return self.drawn[episode]


class EpisodeGate:
    """Holds a match that finished its episode until every other live match has too.

    A match that dies or is stopped stops counting, so the rest are never held for it.
    """

    def __init__(self, workers) -> None:
        self.workers = workers
        self.reached: dict[int, int] = {}
        self.changed = threading.Condition()

    def wait(self, worker, episode: int) -> None:
        with self.changed:
            self.reached[worker.index] = episode
            self.changed.notify_all()
            while not worker.stop.is_set():
                live = [w for w in self.workers
                        if w.failed is None and w.thread.is_alive() and not w.stop.is_set()]
                if all(self.reached.get(w.index, -1) >= episode for w in live):
                    return
                self.changed.wait(0.5)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--policy", type=policy_list, required=True,
                        help="comma list of checkpoints (.pt) and built-in policies "
                             f"({', '.join(BUILT_IN)})")
    parser.add_argument("--matches", type=int, default=1, help="matches per policy")
    parser.add_argument("--speed", default="max",
                        help="simulation speed: 'max' is uncapped (default), 1 is realtime, "
                             "2 is easy to follow")
    parser.add_argument("--task", default="T1_copper", choices=sorted(tasks.CURRICULUM))
    parser.add_argument("--embodied", action="store_true", default=True)
    parser.add_argument("--direct", dest="embodied", action="store_false",
                        help="edit the world directly instead of flying a unit")
    parser.add_argument("--window", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--channels", type=int, default=14)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--worlds", type=int, default=0)
    parser.add_argument("--seed", type=seed_list, default=None,
                        help="world seeds, e.g. 1,10000,42, taken in turn: episode i plays "
                             "seed i mod n in every match. Without it every episode draws a "
                             "random world, the same one in every match")
    parser.add_argument("--no-sync", dest="sync", action="store_false", default=True,
                        help="let a match start its next episode without waiting for the "
                             "others to finish theirs")
    # Empty by default, as the runs here are trained with `--designs=`: a library adds a
    # `stamp` type the checkpoint never had, and its zeroed head row is not a no-op.
    parser.add_argument("--designs", default="",
                        help="design library, only for a checkpoint trained with one")
    parser.add_argument("--port", type=int, default=8810)
    parser.add_argument("--root", default="mindustry-watch")
    parser.add_argument("--no-record", dest="record", action="store_false", default=True,
                        help="do not archive the best episodes under --replays")
    parser.add_argument("--replays", default="replays/watch")
    parser.add_argument("--scene-fps", type=int, default=10)
    parser.add_argument("--join", action="store_true",
                        help="show each match's address to join in the Mindustry client")
    parser.add_argument("--no-open", dest="open", action="store_false", default=True)
    args = parser.parse_args()
    # What EnvWorker reads for a showcase match's speed.
    args.watch_speed = args.speed
    if args.matches < 1:
        parser.error("--matches must be at least 1")

    monitor = TrainingMonitor(title=f"watch / {args.task}")
    monitor.trains = False
    url = monitor.serve(args.port, strict=True)
    kill_servers()
    ensure_jar()
    ensure_assets()
    print(f"dashboard: {url}", flush=True)
    if args.open:
        webbrowser.open(url)

    # Policy p's matches take indices p * matches onwards, so one policy's matches sit
    # together on the dashboard.
    ports = (BRIDGE_PORT_BASE, WATCH_GAME_PORT_BASE)
    plan = [(entry, p * args.matches + k)
            for p, entry in enumerate(args.policy) for k in range(args.matches)]
    workers = [EnvWorker(index, args, monitor, None, showcase=True, ports=ports,
                         label=label_of(entry), windowed=entry.endswith(".pt"))
               for entry, index in plan]
    # Same worlds in the same order in every match, and with sync, the same episode at
    # the same time, so the leaderboard compares policies on equal terms.
    schedule = SeedSchedule(args.seed)
    gate = EpisodeGate(workers)
    for worker in workers:
        worker.seed_of = schedule
        if args.sync:
            worker.before_reset = lambda episode, w=worker: gate.wait(w, episode)
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.ready.wait()

    device = PPOConfig().device
    # One network per checkpoint, shared by its matches.
    networks: dict[str, tuple] = {}
    alive = []
    for (entry, index), worker in zip(plan, workers):
        if worker.failed is not None:
            continue
        observation, info = worker.results.get()
        if entry.endswith(".pt"):
            if entry not in networks:
                networks[entry] = checkpoint_policy(entry, worker, observation, info, args, device)
                act, generation = networks[entry]
                print(f"playing {entry}"
                      + (f" (generation {generation})" if generation is not None else ""),
                      flush=True)
            worker.act = networks[entry][0]
        else:
            worker.act = built_in_policy(entry, worker, seed=index * 977)
        alive.append(worker)
    if not alive:
        raise SystemExit("no environment started")

    # The header shows one generation, which means something only for one checkpoint.
    generations = {g for _, g in networks.values()}
    if len(networks) == 1 and len(generations) == 1:
        monitor.generation = generations.pop()

    print(f"{len(alive)} matches at speed {args.speed}"
          + (f"; in the game: Mindustry -> Play -> Join Game -> "
             f"127.0.0.1:{WATCH_GAME_PORT_BASE}+match" if args.join else "")
          + ". Ctrl+C to stop", flush=True)
    try:
        while any(w.thread.is_alive() for w in alive) and not monitor.stopping.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopping...", flush=True)
    finally:
        for worker in workers:
            worker.stop.set()
        with gate.changed:
            gate.changed.notify_all()
        for worker in workers:
            worker.thread.join(timeout=30)
        monitor.stop()


if __name__ == "__main__":
    main()
