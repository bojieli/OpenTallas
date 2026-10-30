# HBM clock closure continuation, 2026-10-29 23:52 PDT

Own branch codex/hbm-clock-2251. No RTL/arithmetic or added-cycle changes. Model probes are not SIGNED views.

## Concrete BD plan event for parent integration

`bdring_entry_event.py PLAN_COPY` corrects all4 BD clock entries from the stale43.2,151.2 centre of the retired86.4x302.4 shape to60.48,108 in the current120.96x216 outline. The8.64x8.64 island is56.16,103.68..64.8,112.32. It updates clock_entries.json, entries.json, the module's one-island clock.mesh record, oriented per-type taps and all4 clock_taps_die exports. All other modules/pins/data/cycles remain unchanged. Parent approved the narrow candidate and owns adoption/G0/G0C.

Actual copied-plan candidate: intel1:/srv/opentallas-scratch2/claude/codex-hbm-clock-2251/d29d_bdentry. Fresh current SOURCE1abb generator produced bd_kits/ot_hgi_sm_xload_cl2_bdring_0c99d1c898e0-_bdentry2327, `KIT_PREFLIGHT --contract PASS0`, native io.tcl clkM5(60.504,108),0.048x0.48,±1.08 FT pins, one pushdown island. Plan review image personally viewed. Fresh LEC EQUIVALENT16616/16616,0diff/undecided. Place+AUTO-GEOM unitoth-ubuntu-3411553-1793341815 LIVE intel1, run_bd_place.sh; check kit/run_place.log then rev/auto_geom.json. No old wrong-entry SIGNED adoption.

Important nuance: old BD view metadata hash0c99 matches the current source pin table, but its slice consumed stale clock_entries coordinates and moved physical clk after ordinary boundary projection. The old plan_pins.json alone projected clk toE120.864,108, and MS overrode the final physical port to43.2,151.2. Current source table is60.504,108. External CE/slice contract must match actual kit IO; hash-only comparisons miss this existing-contract inconsistency.

Old w60_p2 two-BUFx4 clock prefix was electrically weak: actualTT prefix19.35+32.88ps and43ps transition into clkbuf_0. Actual PDK NLDM sizing at measuredloads predicts a singleBUF8 mean255.29TT/205.62FF orBUF12f243.51/197.52, preserving0 data cycles. These remain DIAGNOSTIC estimates; fresh entry changes must be measured first. `bdring_root_nldm.json` retains the model. Own old-entry GRT-mode diagnostic unit1273079 was stopped after discovering the stale entry (only own exact container9e3a8983c7bd; logs/partial data preserved). No inherited data-ECO jobs were stopped. FLOW owns the measured old-data place12022 BUF10→BUF16f setup+4.196ps what-if; map any eventual new critical path by actual net identity, not old placer numbering.

## Qcore actual failure and clock-only alternatives

Inherited qcore_qa actual terminalFAIL: GRT pinmeanTT274.00(dev24.00) /FF222.72(dev20.22), TTsetup−29.53, FFhold−19.79. Its old helper lacked GRT-CLK-LOCK.

Clock-only same-size LVT substitutions obey the existing≤2% allowance, preserve protected plan islands, all pin functions/polarity, data nets and cycle count. Full510/152223 clock cells(.335%) gave actual placementTT217.87/FF184.41, too early: REJECTED. Uniform top3levels(7cells,.0046%) give247.99/202.86; top4levels(12cells,.0079%) give243.29/200.13, both model gatesPASS. `clock_lvt.tcl` records counts and refuses footprint/pin mismatch. Actual top4 finish unitoth-ubuntu-1508378-1793340476 LIVE epyc2:/srv/opentallas-scratch2/claude/codex-hbm-clock-2251/qcore_lvt_top4, with exact1abb current orfs_hold_mm GRT clock lock. Its own repeated LEC completed EQUIVALENT39179/39179,0diff/undecided; GRT now active. Check run_finish.log, postcts_gate_{tt,ff}.json and final signoff. No SIGNED claim.

## EP actual failure and existing structural fix

Inherited k25b native completed23:38 NOTSIGNED: TTsetup+164.06, FFhold−32.41/217eps, slew561TT/464FF, DRC/antenna0. Related-pair skew162.3TT/164.0FF on p_tx_f→u_tx.prv, pinmeans287.53/231.77. Current d29d pin/CE and kit entry all agree220.344/220.32,25.92; summary entries.json alone is stale but not consumed by this kit. Old GRT means262.23/208.81 and hold+0.59 were insufficient for routed closure.

Cause: planned sink ownership preceded GPL; actual image nearest clock25.92um versus assigned driver161.68um. Existing `core_tree.post_place_rebind="exact_count"` was disabled. Own intel1:/srv/opentallas-scratch2/claude/codex-hbm-clock-2251/ep_rebind enables that existing opt-in on the retained actual3_place. Parent-approved checker verifies complete RTL/top/params/defines plus original formal gold/gate proof; no duplicate formal or waiver. All111 register leaves keep exact counts/depth/source, macro leaves separate. Actual CTS unit3733806 TERMINAL0:9977sinks,3622 reassignments/1670exchange cycles; maximum assigned distance161.68→55.67um,gt100um46→0. FF reg2reg gate−66.03/523→−11.65/256 PASS. Next: TT/FF model, then GRT with current clock lock; real related-pair and signoff gates remain. No DRT/SIGNED claim for rebind yet.

All own physical reviews are under results/geom_review/hbm_clock_2251. OWNER?: none.
