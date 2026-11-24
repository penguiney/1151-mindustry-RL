package mindustryai.net;

import java.util.HashMap;
import java.util.Set;

/** Per-building continuous fullness, measured in simulation ticks, never wall time. */
final class DrillFullTracker {
    private final HashMap<Integer, Double> fullTicks = new HashMap<>();
    private long penaltyIntervals;

    void update(int id, boolean full, double delta) {
        if (!full) {
            fullTicks.remove(id);
            return;
        }
        double before = fullTicks.getOrDefault(id, 0.0);
        double after = before + Math.max(0, delta);
        // First 300 ticks are free; charge once per complete 30 ticks thereafter.
        penaltyIntervals += intervals(after) - intervals(before);
        fullTicks.put(id, after);
    }

    private static long intervals(double ticks) {
        return (long) Math.floor(Math.max(0, ticks - 300) / 30);
    }

    void retain(Set<Integer> alive) {
        fullTicks.keySet().retainAll(alive);
    }

    long penaltyIntervals() {
        return penaltyIntervals;
    }

    void reset() {
        fullTicks.clear();
        penaltyIntervals = 0;
    }
}
