# CAP-TEST-1 (COORD 11-02 22:2x): can OpenROAD/ASAP7 close a 600-800k-cell hard core? (probe only, no plan re-cut)

2026-11-02 22:40 PST START. Vehicle = KV kv3_hub_Eo (event28w_c attempt_3): 577,883 std cells, 0 macros, outline 1278.72x1676.16 (2.14 mm2), 166,913 regs, PLACE_DENSITY 0.5.
  Original failure: floorplan OT_NATIVE_CELL_CAP 577883 > 400000 (pre_floorplan_type.tcl -> native_cell_cap.tcl) [CHECKED intel1 .../kv3_hub_Eo/attempt_3/gen/kv3_hub_Eo/run_place.log].
  Separately the pre-route LEC is NOT EQUIVALENT (KEEP class: 11 of 42244 kept bits merged/renamed, u_astk_EN.m3.zq[8:9] ...) -> this probe cannot give a countable view; it measures P&R capacity only.
  Picked over the S81 serdes kits (460-540k, LEC still running) because it is the largest and densest over-cap kit.
Probe: epyc2 /home/ubuntu/scratch-root/claude/cap-test-1/kv3_hub_Eo (copy of the kit, minus lec/), driver ../probe.sh = run_kit.sh with synth + pre-floor gates + LEC removed
  (stage-resume from the kit's own 1_synth.odb, make -q synth = up to date), cap lifted kit-locally (native_cell_cap.tcl limit 2,000,000; .orig kept). Flow settings UNCHANGED from the kit (baseline first).
  ot-run --mem 96 --threads 16 --hosts epyc2 (queued for memory at 22:4x).
