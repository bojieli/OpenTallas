BF planned ICG G2 candidate (ROOT approved design-target INFO trial)

Frozen previous actual plan:53852 sinks;4306 buffers+1252 ICG stages (40 originals,
1212copies);13 stages; TTwindow39.25/FF33.21. Source count/shape unchanged.
Converted on current SiteMap/per-row/macro-leaf/window-INFO source; explicit
--band info --window-policy info --ndr none. Placement displacementmax3.591um,
mean0.1774, PG clearancePASS. Source policy remains 833ps/60psTTsetup/25psFFhold;
no379pspad or clock constraint change. Trial goals PLACE/CTS/GRT only.

Review bf_icg_g2.png rendered and viewed: two ROM bodies preserved, planned clock
paths and gates occupy surrounding rows, entry at sink-centroid island. Clock
contract explicitly repaired from old inconsistent two-port north-edge clk LEF
shape to the slice's existing interior M5 entry273.228/95.58,full0.048x0.48. All
other pin coordinates are preserved. This is candidate-only plan/LEF/pin data,
not an edit to the shared S81 plan or old probe.

Kit generated: intel1 scratch2/claude/codex-bf-g2-1029/kit,hash6f85734eeba3c8ef,
842pins/2ROMmacros. Exact source branch codex/bf-g2-1029:
b0fd1009b base (4755planned window and055 runtime bandINFO already merged),
098c79173=33dac legacy INFO consistency; b9138d262=c33b30de0 planned-domain gate
compiler; d77f3be95 narrowed5f6198c15 converter+ICGmaster census only. The frozen
plan consumes that converter, so planner/model changes from5f were not imported.
Current SiteMap/macro leaf defaults and window policy are preserved.
99focused testsPASS core_infra/core_plan_to_infra/window target/legacy gate.

No new BF physical job or LEC started at handoff. Two old intel1 ce3-lecrb16 BF/ROM
containers still live9h; no final lec.json at collection. New default run_kit.sh
would run a fresh RAW-netlist LEC before floorplan; do not silently duplicate the
old proof. Planned gate copies only exist after the floorplan hook, which writes
core_infra_post.v for a separate actual post-clone proof; old pre-clone evidence
cannot qualify that netlist. ROOT/FLOW owns the exact trial execution/proof policy.

Ordinary full frontdoor (contains the above pre-floor LEC, not launched):
  bash kit/run_kit.sh kit grt 48 8
Run only through ot-run from intel2 and the exact source/dependency packet approved
by ROOT. No DRT, SIGNED or source-equivalence claim from this candidate.
