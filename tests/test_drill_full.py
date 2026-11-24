"""Fullness grace periods run on simulation ticks; reward consumes cumulative events."""

from pathlib import Path
import subprocess

import pytest

from gamma import tasks


def test_fullness_reward_counts_each_interval_once():
    reward = tasks.get("T2_copper_lead_income").reward
    before = {"build_copper_spent": 0, "drill_full_penalty_intervals": 2}
    after = {**before, "drill_full_penalty_intervals": 5}
    assert reward(before, after) == pytest.approx(-0.03)
    assert reward(after, after) == 0
    assert reward(after, before) == 0  # episode reset cannot award points


def test_old_bridge_requires_rebuild():
    with pytest.raises(RuntimeError, match="drill_full_penalty_intervals missing"):
        tasks.get("T2_copper_lead_income").reward(
            {"build_copper_spent": 0}, {"build_copper_spent": 0})


def test_java_tracker_timing_and_resets(tmp_path):
    source = Path(__file__).resolve().parents[1] / "bridge/src/mindustryai/net/DrillFullTracker.java"
    harness = tmp_path / "FullTrackerCheck.java"
    harness.write_text('''
package mindustryai.net;
import java.util.Set;
public class FullTrackerCheck {
    static void count(DrillFullTracker t, long expected) {
        if (t.penaltyIntervals() != expected)
            throw new AssertionError(t.penaltyIntervals() + " != " + expected);
    }
    public static void main(String[] args) {
        DrillFullTracker t = new DrillFullTracker();
        for (int i = 0; i < 300; i++) t.update(1, true, 1);
        count(t, 0); // exact five-second grace
        t.update(1, true, 29); count(t, 0);
        t.update(1, true, 1); count(t, 1);
        t.update(1, true, 60); count(t, 3);
        t.update(2, true, 330); count(t, 4); // independent drill
        t.update(1, false, 1); // any output below capacity resets the grace
        t.update(1, true, 300); count(t, 4);
        t.update(1, true, 30); count(t, 5);
        t.retain(Set.of(2)); // demolition forgets this building
        t.update(1, true, 300); count(t, 5);
        t.reset(); count(t, 0);
        for (int i = 0; i < 660; i++) t.update(1, true, 0.5);
        count(t, 1); // fractional simulation delta
    }
}
''', encoding="utf-8")
    subprocess.run(["javac", "-d", str(tmp_path), str(source), str(harness)], check=True,
                   capture_output=True, text=True)
    subprocess.run(["java", "-cp", str(tmp_path), "mindustryai.net.FullTrackerCheck"],
                   check=True, capture_output=True, text=True)
