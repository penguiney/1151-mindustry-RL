"""Score a checkpoint on worlds it has never trained on.

    python tools/evaluate.py checkpoints/beta-best.pt
    python tools/evaluate.py checkpoints/exp05/beta.pt checkpoints/exp07/beta.pt --items copper,lead

This is the only measurement in the project that can tell learning from memorising. A
reward curve rising on the maps an agent trained on is exactly what memorisation looks
like, so it answers nothing on its own. The sector pool holds a fifth of the planet back
for this, and nothing in a training run ever touches it.

With --random, every checkpoint given is also scored side by side with a masked random
policy, the floor. It is off by default: the random policy has no way to find ore, so on
these maps it barely mines and its score is no useful reference. With two checkpoints, the
verdict compares the two of them; with one and --random, the checkpoint against the floor.

Per ore named in --items, each policy also reports where the ore in the core came from
(machines against the unit's own hand) and how its drills did: how many were connected
(mined more than their own buffer holds, so something carried ore away) and how many were
still running at the end.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import queue
import statistics
import threading
import time
import webbrowser
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import torch

from gamma import server, tasks
from gamma.env import MindustryEnv
from gamma.library import load as load_designs
from gamma.net import PolicyNet
from gamma.ppo import PPOConfig, load_weights
from gamma.window import DEFAULT_SIZE, LocalWindow


@dataclass
class Outcome:
    """What one episode came to."""

    sector: int
    reward: float
    steps: int
    wave: int
    built: int
    solved: bool
    #: Ore a machine delivered to the core. Hand mining is not counted, by the engine.
    produced: int
    #: Milestones the episode reached, by name.
    reached: frozenset[str]
    #: Whether the core was still standing when the episode ended.
    survived: bool
    #: Per tracked ore: machine, hand, drills, connected, running.
    per_item: dict[str, dict[str, int]]
    #: The seed the world was pinned to, None when it was not.
    world_seed: int | None = None


#: A mechanical drill holds this many items. One that mined more had them carried away.
DRILL_BUFFER = 10


class DrillLedger:
    """Every drill an episode had, from `drill_mined` read each step.

    The observation only lists drills still standing, so one that was torn down mid
    episode would vanish from a final snapshot. The ledger keeps them."""

    def __init__(self) -> None:
        # building id -> [item, first step seen, highest count, last step it rose]
        self.drills: dict[str, list] = {}

    def update(self, raw: dict, step: int) -> None:
        for item, counts in (raw.get("drill_mined") or {}).items():
            for building, count in counts.items():
                count = int(count)
                entry = self.drills.setdefault(building, [item, step, 0, step])
                if count > entry[2]:
                    entry[2] = count
                    entry[3] = step

    def tally(self, item: str, end: int, settle: int, window: int) -> dict[str, int]:
        """Drills of one ore that had time to prove themselves, and how they did.

        A drill is only counted once it has stood `settle` steps or is already past its
        buffer: one laid near the end has not had the chance to fill it and would read as
        unconnected. Running means its count still rose in the last `window` steps."""
        drills = connected = running = 0
        for kind, first, best, rose in self.drills.values():
            if kind != item or (end - first < settle and best <= DRILL_BUFFER):
                continue
            drills += 1
            connected += best > DRILL_BUFFER
            running += end - rose < window
        return {"drills": drills, "connected": connected, "running": running}


def _share(part: float, whole: float) -> float:
    return round(part / whole, 3) if whole else 0.0


def summarise_items(outcomes: list[Outcome]) -> dict:
    """Per ore, pooled over episodes: a rate is total over total rather than a mean of
    per-episode rates, so an episode with one drill does not weigh as much as one with
    thirty."""
    items: dict[str, dict] = {}
    for item in (outcomes[0].per_item if outcomes else {}):
        total = {key: sum(o.per_item[item][key] for o in outcomes)
                 for key in ("machine", "hand", "drills", "connected", "running")}
        n = len(outcomes)
        items[item] = {
            "mean_machine": round(total["machine"] / n, 1),
            "mean_hand": round(total["hand"] / n, 1),
            "hand_share": _share(total["hand"], total["hand"] + total["machine"]),
            "mean_drills": round(total["drills"] / n, 1),
            "connected_rate": _share(total["connected"], total["drills"]),
            "running_rate": _share(total["running"], total["drills"]),
        }
    return items


def summarise(name: str, outcomes: list[Outcome]) -> dict:
    rewards = [o.reward for o in outcomes]
    return {
        "policy": name,
        "episodes": len(outcomes),
        "sectors": len({o.sector for o in outcomes}),
        "mean_reward": round(statistics.fmean(rewards), 3) if rewards else 0.0,
        # The uncertainty on that mean, which is what a comparison has to be read against.
        # The spread alone invites the mistake this file made twice: two runs of the same
        # measurement named opposite winners, at 1.3 and 0.7 standard deviations, and both
        # were reported as results.
        "standard_error": round(
            statistics.pstdev(rewards) / math.sqrt(len(rewards)), 3
        ) if len(rewards) > 1 else 0.0,
        # The spread matters as much as the mean here: a policy that scores well on a
        # third of the worlds and collapses on the rest has not generalised, and its mean
        # can look identical to one that copes everywhere.
        "reward_spread": round(statistics.pstdev(rewards), 3) if len(rewards) > 1 else 0.0,
        "worst_reward": round(min(rewards), 3) if rewards else 0.0,
        "mean_wave": round(statistics.fmean(o.wave for o in outcomes), 2) if outcomes else 0,
        "mean_built": round(statistics.fmean(o.built for o in outcomes), 1) if outcomes else 0,
        "mean_produced": round(statistics.fmean(o.produced for o in outcomes), 1) if outcomes else 0,
        "solved": sum(o.solved for o in outcomes),
        "survived": round(
            statistics.fmean(o.survived for o in outcomes), 3) if outcomes else 0.0,
        # How often each rung of the ladder was reached, which says far more than a mean
        # reward does. A policy that never once reaches `automation` has not started
        # playing the game, whatever its score.
        "milestones": {
            stone.name: round(
                sum(stone.name in o.reached for o in outcomes) / len(outcomes), 2
            )
            for stone in tasks.MILESTONES
        } if outcomes else {},
        "per_item": summarise_items(outcomes),
        # Pooled over seeds, a mean hides the one the policy was trained on carrying the
        # rest. Split, the gap between a trained seed and an unseen one is the measure.
        "per_seed": {
            seed: {
                "episodes": len(group),
                "mean_reward": round(statistics.fmean(o.reward for o in group), 3),
                "solved": sum(o.solved for o in group),
                "per_item": summarise_items(group),
            }
            for seed in dict.fromkeys(o.world_seed for o in outcomes)
            if seed is not None
            for group in [[o for o in outcomes if o.world_seed == seed]]
        },
    }


def seed_list(text: str) -> tuple[int, ...]:
    """`--seed`: one seed, or several separated by commas."""
    try:
        seeds = tuple(int(part) for part in text.split(",") if part.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a seed or a list of seeds: {text!r}")
    if not seeds:
        raise argparse.ArgumentTypeError("no seed given")
    return seeds


def play(env, policy, task, steps: int, items: tuple[str, ...] = ("copper",),
         settle: int = 60, window: int = 50, seed: int | None = None) -> Outcome:
    """One episode, greedy where the policy is a network.

    A seed pins this episode's world. Set here rather than drawn by the environment, so
    every policy compared plays the same seeds in the same order."""
    if seed is not None:
        env.env.task = replace(task, world_seed=seed, world_seeds=())
    observation, info = env.reset()
    total = 0.0
    raw = info["raw"]
    ledger = DrillLedger()

    for step in range(steps):
        action = policy(observation, info)
        observation, reward, terminated, truncated, info = env.step(action)
        raw = info["raw"]
        total += reward
        ledger.update(raw, step)
        if terminated or truncated:
            break

    per_item = {
        item: {
            # The engine counts only what a transport block delivers; the bridge counts
            # what the unit hands over itself. Together they are everything that arrived.
            "machine": int(raw.get("produced", {}).get(item, 0)),
            "hand": int(raw.get("hand_delivered", {}).get(item, 0)),
            **ledger.tally(item, step, settle, window),
        }
        for item in items
    }

    return Outcome(
        sector=env.sector_index if env.sector_index is not None else -1,
        reward=total,
        steps=step + 1,
        wave=int(raw.get("wave", 0)),
        built=int(raw.get("built", 0)),
        solved=bool(task.succeeded(raw)),
        produced=sum(int(a) for a in raw.get("produced", {}).values()),
        # Asked of the task, not of the observation: the automation and variety rungs
        # read the reward's ledger, which no observation carries.
        reached=tasks.reached(task, raw),
        #: Whether the base was still standing. Half of what a run is judged on, and it
        #: was not being measured at all.
        survived=bool(raw.get("has_core", False)),
        per_item=per_item,
        world_seed=seed,
    )


def network_policy(net: PolicyNet, device: str):
    """Sample from the policy, masked. Greedy would collapse a stochastic policy onto one
    action type and measure something the agent never does."""

    def act(observation, info):
        with torch.no_grad():
            spatial = torch.as_tensor(observation["spatial"][None], device=device)
            globals_ = torch.as_tensor(observation["global"][None], device=device)
            mask = info.get("action_mask", {})
            masks = {
                "type": torch.as_tensor(mask["type"][None], device=device),
                "block": torch.as_tensor(mask["block"][None], device=device),
                "position": torch.as_tensor(
                    mask["position"].reshape(1, -1), device=device
                ),
                # Without this the network falls back to the single position mask, which
                # cannot be right for more than one action type at a time. A policy
                # evaluated that way is not the policy that was trained.
                "position_sets": torch.as_tensor(
                    mask["position_sets"].reshape(1, mask["position_sets"].shape[0], -1),
                    device=device,
                ),
            }
            action, _, _, _ = net.act(spatial, globals_, masks)
            return net.to_env_action(action)[0]

    return act


def random_policy(env, seed: int = 20260825):
    """The floor. Masked, because an unmasked random policy is refused almost always and
    would set a floor no policy could fail to clear.

    Seeded, which it was not, and that mattered more than it sounds. Drawing from the
    global generator made the floor different on every run, so the same policy on the same
    held-out sectors was compared against a different opponent each time. Measured: the
    unseeded floor delivered 18.7 ore in one run and 0 in the next, on the same worlds, and
    the two runs disagreed about which policy won.
    """
    rng = np.random.default_rng(seed)

    def act(observation, info):
        mask = info.get("action_mask", {})
        types = np.flatnonzero(mask["type"])
        blocks = np.flatnonzero(mask["block"])
        positions = np.flatnonzero(mask["position"].reshape(-1))
        window = env.size
        flat = int(rng.choice(positions)) if positions.size else 0
        return np.array([
            int(rng.choice(types)) if types.size else 0,
            int(rng.choice(blocks)) if blocks.size else 0,
            flat % window,
            flat // window,
            rng.integers(4),
        ])

    return act


def seed_table_lines(per_seed: dict, items, seeds=()) -> list[str]:
    """One row per seed, one column pair per ore: machine-delivered ore and drills.

    A seed in `seeds` with no episode played yet gets a row of 0/0 and dashes."""
    pad = " " * 14
    lines = ["",
             pad + f"{'seed':<8}{'reward':>9}{'solved':>8}"
             + "".join(f"  {item:^15}" for item in items),
             pad + " " * 25 + "".join(f"  {'machine':>8}{'drills':>7}" for _ in items)]
    for seed in dict.fromkeys([*seeds, *per_seed]):
        row = per_seed.get(seed)
        if row is None:
            lines.append(pad + f"{seed:<8}{'-':>9}{'0/0':>8}"
                         + "".join(f"  {'-':>8}{'-':>7}" for _ in items))
            continue
        cells = "".join(f"  {row['per_item'][item]['mean_machine']:8.1f}"
                        f"{row['per_item'][item]['mean_drills']:7.1f}" for item in items)
        solved = f"{row['solved']}/{row['episodes']}"
        lines.append(pad + f"{seed:<8}{row['mean_reward']:+9.1f}{solved:>8}" + cells)
    return lines


def evaluation_task(args):
    """Return the task on the first seed in the args, which is used to size the PolicyNet."""
    task = tasks.get(args.task)
    if args.seed:
        task = replace(task, world_seed=args.seed[0], world_seeds=())
    return task


def evaluation_env(task, args, jar: str, port: int, root: str):
    """Build the environment that the policies need."""
    designs = ()
    if args.designs and Path(args.designs).is_file():
        designs = tuple(load_designs(Path(args.designs)))
    return LocalWindow(
        MindustryEnv(
            task, server_dir=root, bridge_port=port, game_port=port - 1000,
            jar=jar, embodied=True, speed="max", evaluating=True, designs=designs,
            window=args.window,
        ),
        size=args.window, channels=args.channels,
    )


def network_policies(env, checkpoints, args, device: str) -> list:
    """load weights(.pt) into PolicyNet, to form policies that play the game."""
    policies = []
    for checkpoint in checkpoints:
        observation, info = env.reset()
        net = PolicyNet(
            channels=observation["spatial"].shape[0],
            window=args.window,
            globals_size=observation["global"].shape[0],
            n_types=len(info["action_mask"]["type"]),
            n_blocks=len(info["action_mask"]["block"]),
            # The action layout, asked of the environment being evaluated on. A network
            # built without it treats every action type as aiming at the same tiles, which
            # is what the trained weights were not trained to do.
            position_set_of_type=env.position_set_of_type,
            block_of_type=env.block_of_type,
            rotation_of_type=env.rotation_of_type,
        )
        load_weights(net, checkpoint, device)
        net.to(device).eval()
        policies.append(network_policy(net, device))
    return policies


def _worker(index: int, args, jar: str, items, jobs, results) -> None:
    """Runs in a child process: play the episodes taken from `jobs` until it gives None."""
    torch.set_num_threads(1)
    # A child process starts with the default, not with what main set.
    server.POLITE = not args.greedy
    task = evaluation_task(args)
    # Ports count down from --port, because training uses 7920 and up.
    env = evaluation_env(task, args, jar, args.port - index, f"{args.root}/worker{index}")
    try:
        policies = network_policies(env, args.checkpoint, args, "cpu")
        while (job := jobs.get()) is not None:
            which, episode, seed = job
            outcome = play(env, policies[which], task, args.max_steps, items, args.settle,
                           args.running_window, seed)
            results.put((which, episode, outcome))
    except BaseException as error:
        results.put(("failed", index, f"{type(error).__name__}: {error}"))
        raise
    finally:
        env.close()


def play_in_parallel(args, jar: str, items, total: int, on_outcome=None) -> list[list[Outcome]]:
    """Play every episode on `args.envs` child processes, one environment each.

    Returns the outcomes per checkpoint, in episode order, as a serial run would.
    `on_outcome(which, outcome)` is called as each episode finishes, in finishing order."""
    seeds = args.seed or ()
    context = multiprocessing.get_context("spawn")
    jobs, results = context.Queue(), context.Queue()
    for which in range(len(args.checkpoint)):
        for episode in range(total):
            jobs.put((which, episode, seeds[episode % len(seeds)] if seeds else None))
    for _ in range(args.envs):
        jobs.put(None)

    workers = [context.Process(target=_worker, args=(index, args, jar, items, jobs, results))
               for index in range(args.envs)]
    for worker in workers:
        worker.start()

    needed = len(args.checkpoint) * total
    outcomes: dict[tuple[int, int], Outcome] = {}
    try:
        while len(outcomes) < needed:
            try:
                message = results.get(timeout=5)
            except queue.Empty:
                if not any(worker.is_alive() for worker in workers):
                    raise SystemExit("every worker has exited, with episodes left to play")
                continue
            if message[0] == "failed":
                raise SystemExit(f"worker {message[1]} failed: {message[2]}")
            which, episode, outcome = message
            outcomes[(which, episode)] = outcome
            if on_outcome is not None:
                on_outcome(which, outcome)
    finally:
        for worker in workers:
            worker.join(timeout=60 if len(outcomes) == needed else 0)
        # Each server is in a job object, so terminating its worker ends it too.
        for worker in workers:
            if worker.is_alive():
                worker.terminate()

    return [[outcomes[(which, episode)] for episode in range(total)]
            for which in range(len(args.checkpoint))]


def summary_lines(summary: dict, seeds, items) -> list[str]:
    """One policy's results as printed: totals, milestones, ores and, with several seeds,
    the seed table."""
    lines = [
        f"{summary['policy']:>12}  reward {summary['mean_reward']:+8.3f} "
        f"+-{summary['reward_spread']:6.3f}  worst {summary['worst_reward']:+8.3f}  "
        f"wave {summary['mean_wave']:5.2f}  built {summary['mean_built']:6.1f}  "
        f"produced {summary['mean_produced']:8.1f}  "
        f"solved {summary['solved']}/{summary['episodes']}  "
        f"core tenu {summary['survived']:.0%}",
    ]
    reached = [f"{n} {r:.0%}" for n, r in summary["milestones"].items() if r > 0]
    lines.append(f"{'':>12}  {' | '.join(reached) if reached else 'no milestone reached'}")
    for item, row in summary["per_item"].items():
        lines.append(f"{'':>12}  {item:<8} machine {row['mean_machine']:7.1f}  "
                     f"hand {row['mean_hand']:7.1f} ({row['hand_share']:4.0%} by hand) | "
                     f"drills {row['mean_drills']:5.1f}  connected {row['connected_rate']:4.0%}  "
                     f"running {row['running_rate']:4.0%}")
    if len(seeds) > 1:
        lines += seed_table_lines(summary["per_seed"], items, seeds)
    return lines


def print_summary(summary: dict, seeds, items) -> None:
    print("\n".join(summary_lines(summary, seeds, items)), flush=True)


_LIVE_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>evaluate</title>
<style>
:root { color-scheme: light dark; }
body { margin: 16px; font: 13px/1.4 Consolas, "Cascadia Mono", monospace; }
#status { margin-bottom: 8px; opacity: 0.7; }
pre { margin: 0; white-space: pre; }
</style></head>
<body><div id="status">connecting...</div><pre id="table"></pre>
<script>
const status = document.getElementById("status"), table = document.getElementById("table");
async function update() {
  try {
    const answer = await fetch("/table", {cache: "no-store"});
    table.textContent = await answer.text();
    status.textContent = "live, updated " + new Date().toLocaleTimeString();
  } catch (error) {
    return;  // evaluate has ended; the last table stays as it was
  }
  setTimeout(update, 1000);
}
update();
</script></body></html>
"""


class LiveTable:
    """The results so far, served as a page that refreshes itself every second.

    Updated once per finished episode. Shown in a browser rather than redrawn in the
    terminal: two checkpoints with fifteen seeds are taller than most terminal windows."""

    def __init__(self, names, total: int, seeds, items, port: int) -> None:
        self.names, self.total, self.seeds, self.items = names, total, seeds, items
        self.outcomes: list[list[Outcome]] = [[] for _ in names]
        self.started = time.time()
        # Set by finish(): the run's own seconds, as in the report, and the verdict.
        self.seconds: float | None = None
        self.verdict: list[str] = []
        self.lock = threading.Lock()
        # Bumped on every update, and noted when the page fetches it, so close() can wait
        # for the page to have the final table.
        self.version = self.sent = 0
        self.server = self._serve(port)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"

    def add(self, which: int, outcome: Outcome) -> None:
        with self.lock:
            self.outcomes[which].append(outcome)
            self.version += 1

    def finish(self, seconds: float, verdict: list[str]) -> None:
        with self.lock:
            self.seconds, self.verdict = seconds, verdict
            self.version += 1

    def close(self) -> None:
        """Stop serving, once a page that was watching has fetched the final table."""
        deadline = time.time() + 3
        while self.sent and self.sent < self.version and time.time() < deadline:
            time.sleep(0.1)
        self.server.shutdown()
        self.server.server_close()

    def _render(self) -> str:
        """The table as it stands. Built on each request, so the elapsed time keeps moving
        between episodes; once finished, it is the run's own seconds."""
        done = sum(len(o) for o in self.outcomes)
        needed = len(self.names) * self.total
        finished = self.seconds is not None
        elapsed = int(self.seconds if finished else time.time() - self.started)
        lines = [f"  evaluate  {done}/{needed} episodes  {done / needed:.0%}   "
                 f"{elapsed // 60}:{elapsed % 60:02d} elapsed"
                 + ("   finished" if finished else ""), ""]
        for name, outcomes in zip(self.names, self.outcomes):
            if not outcomes:
                lines.append(f"{name:>12}  0/{self.total} episodes")
                if len(self.seeds) > 1:
                    lines += seed_table_lines({}, self.items, self.seeds)
                continue
            # Grouped by seed in --seed order rather than in the order episodes finished.
            ordered = sorted(outcomes, key=lambda o: self.seeds.index(o.world_seed)
                             if o.world_seed in self.seeds else 0)
            lines += summary_lines(summarise(name, ordered), self.seeds, self.items)
        return "\n".join(lines + self.verdict) + "\n"

    def _serve(self, port: int) -> ThreadingHTTPServer:
        live = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/table":
                    with live.lock:
                        body, live.sent = live._render().encode("utf-8"), live.version
                    kind = "text/plain; charset=utf-8"
                elif self.path == "/":
                    body, kind = _LIVE_PAGE.encode("utf-8"), "text/html; charset=utf-8"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:
                # One line per request every second would bury the terminal.
                pass

        # The next free port when this one is taken, by another evaluate for instance.
        for candidate in range(port, port + 10):
            try:
                live_server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
                break
            except OSError:
                continue
        else:
            raise SystemExit(f"no free port for the live table in {port}..{port + 9}")
        threading.Thread(target=live_server.serve_forever, daemon=True).start()
        return live_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint", type=Path, nargs="*",
                        help="zero, one or two checkpoints. With two, the verdict compares "
                             "them with each other rather than with the random floor")
    parser.add_argument("--task", default="frontier", choices=sorted(tasks.CURRICULUM))
    parser.add_argument("--episodes", type=int, default=10,
                        help="with --seed, run N episodes per seed, without --seed, run N episodes in total.")
    parser.add_argument("--max-steps", type=int, default=1500)
    parser.add_argument("--window", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--channels", type=int, default=14)
    parser.add_argument("--seed", type=seed_list, default=None, 
                        help="world seeds to test on, e.g. 1,10000,42."
                             "Leave it out to get a random world seed every episode")
    parser.add_argument("--port", type=int, default=7910)
    parser.add_argument("--root", default="mindustry-eval")
    parser.add_argument("--designs", default="",
                        help="the structures the policy was trained with "
                             "(docs/designs.json), off by default. Must match training: "
                             "the library adds a `stamp` action, and a mismatched head "
                             "is loaded without complaint and plays a different policy")
    parser.add_argument("--random", action=argparse.BooleanOptionalAction, default=False,
                        help="also test a policy that picks random legal actions")
    parser.add_argument("--items", default="copper",
                        help="ores to report on, comma separated (default: copper), e.g. "
                             "copper,lead,sand. For each: ore delivered by machines and by "
                             "hand, the hand share, drills, connected rate and running rate")
    parser.add_argument("--settle", type=int, default=60,
                        help="steps a drill must have stood before it counts towards the "
                             "connected and running rates, unless it already mined more "
                             "than its buffer of %d (default: 60). Keeps drills laid near "
                             "the end from reading as unconnected" % DRILL_BUFFER)
    parser.add_argument("--running-window", type=int, default=50,
                        help="a drill is running if its count still rose in this many "
                             "final steps of the episode (default: 50)")
    parser.add_argument("--out", type=Path, default=Path("checkpoints/scratch/evaluate.json"))
    parser.add_argument("--envs", type=int, default=1,
                        help="environments to play on at once (default: 1). Each runs in "
                             "its own process, on ports downwards from --port and in a "
                             "folder under --root, with its networks on the CPU")
    parser.add_argument("--greedy", action="store_true",
                        help="take the whole machine: faster evaluation, unusable desktop")
    parser.add_argument("--live-port", type=int, default=8820,
                        help="serve the results so far at http://127.0.0.1:PORT/ while the "
                             "evaluation runs (default: 8820, the next free one if taken). "
                             "0 turns it off")
    parser.add_argument("--no-open", dest="open", action="store_false", default=True,
                        help="do not open the live table in a browser")
    args = parser.parse_args()
    server.POLITE = not args.greedy

    if len(args.checkpoint) > 2:
        parser.error("at most two checkpoints")
    if args.envs < 1:
        parser.error("--envs must be at least 1")
    if args.envs > 1 and args.random:
        parser.error("--random only runs with --envs 1")
    if not args.checkpoint and not args.random:
        raise SystemExit("nothing to evaluate: pass a checkpoint, or --random for the floor")

    # Deliberately no server cleanup: this runs on its own ports and its own directory,
    # and is meant to be usable while a training run is going. Killing every Mindustry
    # process would take the run down with it.
    jar = str(next((Path("bridge") / "build" / "libs").glob("*.jar")))
    task = evaluation_task(args)
    seeds = args.seed or ()
    items = tuple(item.strip() for item in args.items.split(",") if item.strip())

    # Two checkpoints are often both called beta.pt; the folder tells them apart.
    stems = [path.stem for path in args.checkpoint]
    names = [f"{path.parent.name}/{path.stem}" if stems.count(path.stem) > 1 else path.stem
             for path in args.checkpoint]
    if args.random:
        names.append("random")
    # Per seed when seeds are given, so every seed carries the same weight in the means
    # whatever their number. A total split by `i mod n` left the first seeds with one
    # episode more whenever the total was not a multiple of the list.
    total = args.episodes * len(seeds) if seeds else args.episodes
    report = {"task": task.name, "held_out": True, "episodes_each": args.episodes,
              "designs": len(load_designs(Path(args.designs)))
              if args.designs and Path(args.designs).is_file() else 0,
              "items": list(items), "settle": args.settle,
              "running_window": args.running_window, "envs": args.envs,
              "greedy": args.greedy, "results": []}

    # Served from a daemon thread, so an exception anywhere below ends it with the process.
    live = LiveTable(names, total, seeds, items, args.live_port) if args.live_port else None
    on_outcome = live.add if live else None
    if live:
        print(f"live table: {live.url}", flush=True)
        if args.open:
            webbrowser.open(live.url)

    if args.envs > 1:
        # Includes the time the workers take to start their servers.
        started = time.time()
        for name, outcomes in zip(names, play_in_parallel(args, jar, items, total, on_outcome)):
            summary = summarise(name, outcomes)
            report["results"].append(summary)
            print_summary(summary, seeds, items)
    else:
        env = evaluation_env(task, args, jar, args.port, args.root)
        try:
            policies = network_policies(env, args.checkpoint, args, PPOConfig().device)
            if args.random:
                policies.append(random_policy(env))
            started = time.time()
            for which, (name, policy) in enumerate(zip(names, policies)):
                outcomes = []
                for i in range(total):
                    outcomes.append(play(env, policy, task, args.max_steps, items, args.settle,
                                         args.running_window,
                                         seeds[i % len(seeds)] if seeds else None))
                    if on_outcome is not None:
                        on_outcome(which, outcomes[-1])
                summary = summarise(name, outcomes)
                report["results"].append(summary)
                print_summary(summary, seeds, items)
        finally:
            # An exception mid-run used to skip this, and the server was left holding the
            # port for the next evaluation.
            env.close()
    report["seconds"] = round(time.time() - started, 1)

    # The only line that answers the question this tool exists for, and it says "not
    # enough evidence" far more often than a mean reward suggests.
    # Two checkpoints are compared with each other; one is compared with the floor.
    verdict = []
    if len(report["results"]) >= 2:
        first, second = report["results"][:2]
        gap = first["mean_reward"] - second["mean_reward"]
        uncertainty = math.hypot(first["standard_error"], second["standard_error"])
        sigmas = abs(gap) / uncertainty if uncertainty else 0.0
        report["verdict"] = {
            "gap": round(gap, 3), "uncertainty": round(uncertainty, 3),
            "sigmas": round(sigmas, 2),
            "conclusive": sigmas >= 2.0,
        }
        verdict = ["", f"{first['policy']} minus {second['policy']}: {gap:+.2f} "
                       f"+-{uncertainty:.2f}, {sigmas:.1f} standard deviations"]
        if sigmas < 2.0:
            verdict.append("Not enough evidence to separate them. More episodes, or a bigger "
                           "difference, or both.")
        else:
            verdict.append(f"{first['policy'] if gap > 0 else second['policy']} is ahead.")
        print("\n".join(verdict))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten to {args.out}")
    if live:
        live.finish(report["seconds"], verdict)
        live.close()


if __name__ == "__main__":
    main()
