package mindustryai.net;

import mindustry.Vars;
import mindustry.content.Items;
import mindustry.gen.Building;
import mindustry.gen.Unit;
import mindustry.world.blocks.ConstructBlock;

/** Observe actual construction payments, including partially completed buildings. */
public final class BuildCostTracker {
    private static int copperSpent;
    private static boolean installed;

    private BuildCostTracker() {}

    public static void install() {
        if (installed) return;
        installed = true;
        for (var block : Vars.content.blocks()) {
            if (block instanceof ConstructBlock construction) {
                construction.buildType = () -> construction.new ConstructBuild() {
                    @Override
                    public void construct(Unit builder, Building core, float amount, Object config) {
                        boolean tracked = core != null && core.items != null
                            && core.team == Vars.state.rules.defaultTeam;
                        int before = tracked ? core.items.get(Items.copper) : 0;
                        try {
                            super.construct(builder, core, amount, config);
                        } finally {
                            // Measure within the construction call, so deliveries, refunds,
                            // crafting and ammunition cannot be mistaken for build costs.
                            if (tracked) record(before - core.items.get(Items.copper));
                        }
                    }
                };
            }
        }
    }

    public static void record(int amount) {
        copperSpent += Math.max(0, amount);
    }

    public static int copperSpent() {
        return copperSpent;
    }

    public static void reset() {
        copperSpent = 0;
    }
}
