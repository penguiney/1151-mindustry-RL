"""The drill ledger behind evaluate's connected and running rates. No server needed."""

from __future__ import annotations

from tools.evaluate import DrillLedger


def run(history: list[dict[str, int]]) -> DrillLedger:
    """Feed one `drill_mined` snapshot per step, all copper."""
    ledger = DrillLedger()
    for step, counts in enumerate(history):
        ledger.update({"drill_mined": {"copper": counts}}, step)
    return ledger


def test_a_drill_that_fills_its_buffer_and_stops_is_not_connected() -> None:
    history = [{"1": min(10, step // 5 + 1)} for step in range(200)]
    tally = run(history).tally("copper", 199, settle=60, window=50)
    assert tally == {"drills": 1, "connected": 0, "running": 0}


def test_a_connected_drill_that_jams_is_connected_but_not_running() -> None:
    history = [{"1": min(30, step // 5 + 1)} for step in range(300)]
    tally = run(history).tally("copper", 299, settle=60, window=50)
    assert tally == {"drills": 1, "connected": 1, "running": 0}


def test_a_drill_still_mining_at_the_end_is_running() -> None:
    history = [{"1": step // 5 + 1} for step in range(300)]
    tally = run(history).tally("copper", 299, settle=60, window=50)
    assert tally == {"drills": 1, "connected": 1, "running": 1}


def test_a_drill_torn_down_is_still_counted() -> None:
    # Mined 20, then disappears from the observation for the rest of the episode.
    history = [{"1": step // 5 + 1} if step < 100 else {} for step in range(300)]
    tally = run(history).tally("copper", 299, settle=60, window=50)
    assert tally == {"drills": 1, "connected": 1, "running": 0}


def test_a_drill_laid_near_the_end_is_left_out() -> None:
    history = [{} if step < 270 else {"1": (step - 270) // 5 + 1} for step in range(300)]
    tally = run(history).tally("copper", 299, settle=60, window=50)
    assert tally["drills"] == 0


def test_other_ores_are_kept_apart() -> None:
    ledger = DrillLedger()
    for step in range(200):
        ledger.update({"drill_mined": {"copper": {"1": step // 5 + 1}, "sand": {"2": 5}}}, step)
    assert ledger.tally("copper", 199, 60, 50)["drills"] == 1
    assert ledger.tally("sand", 199, 60, 50) == {"drills": 1, "connected": 0, "running": 0}
