# INFRA-FIRST-QC-R25: mesh drivers re-planned on the A0 drop lattice, E-pin windows, die clock DRC re-run

Lane INFRA-FIRST-QC-R25 (2026-10-27), base claude/qc-mesh-r24-1027@bce82068b3. COORD 06:34 ruling on R24b. Section 12 unchanged:
MSCTS = H-tree -> one continuous mesh -> local trees. Inputs are read-only: the Codex guard51 package
(intel2:/srv/opentallas-scratch2/claude/codex-qwen-1027/pkg, plan sha 37937a86) and a0_clk_r3b.json (from R24 r3b).
Runs: intel2:/srv/opentallas-scratch2/claude/qc-mesh-r25. All numbers are UNCHECKED (one tool run). NUMBER-CHECK owed.

## 1. Driver re-plan (`r25_drop_drivers.py --mode replan --size-rule adjcol`, plan_replan.json.gz)
- Straps are those of the R24 re-phase: 48 kept M9 + 192 drop M9, 50 kept M8 + 128 drop M8.
- **Drop M9 segmented per A0 row.** Each drop M9 runs only from the band below its row to the band above it, giving 3,072
  row segments. No drop strap is full height any more.
- **Band drivers.** One BUFx24 sits ON each drop strap in each of the 18 A0 row bands (die edge, inter-row, centre-facing),
  so each row segment is driven at both ends: 192 x 18 = 3,456 drivers.
  - The site is the kept R23 M8 strap in the band, or the nearest 8.64 lane. A fail-closed check rejects any site on a hard
    core (+4.32) or on a partition seam. Result: 0 such sites.
- **W-edge driver column** at x 1632.96 (= 1650.24 - 2 x 8.64), M9 full span, with a driver at every M8 y. That gives 170
  drivers; 8 rows are skipped where a centre-field hard core sits under the column.
  - Why not 1641.6: at 1641.6 the 8.64 island edge would sit 4.32 um from the A0 W pin face, inside the 5.4 NK halo.
    At 1632.96 the gap is 12.96 um.
- **Plan-computed sizing (12.8 d1).** Band drivers in the 24 A0 columns with only 1 adjacent channel driver column get x2
  (two BUFx24 in parallel): 1,728 drivers. Without it, those columns are 40-45 ps late (nom_replan_nosize_TT.json).
- **Feed.** Each new driver is a leaf fed from the nearest column-tree driver. Legs: median 302 um, max 1,230 um (3 stages).
  - The model takes every leaf as arriving at the common driver arrival at TT. The FF residual of that sizing is
    -2.5..+0.8 ps and is applied.
  - CAVEAT: the leg-delay range is 41-268 ps TT. Balancing it by sizing alone is too large to be "sizing". It needs DME
    band x-trees in the plan tool (qc_clk_mesh3), which is not built yet. This run is a mesh-RC check with balanced
    drivers, not a tree build.
- **Continuity.** 36,370 geometric M9 x M8 crossings = 36,370 shared nodes (one M8-M9 via each). The fail-closed check
  exits 2 on any mismatch. The mesh stays one continuous mesh.

## 2. Mesh RC (linear RC transient, qc_clk_mesh2.solve_netlist, thev_r2, RC_R6 8w, 16,896 drop loads + 377 partition taps)
The netlist builder reproduces R24 exactly: the rephase mode gives 363.957 / p90 149.269 (nom_rephase_TT.json).

| variant (TT nominal) | C pF | crossing spread | A0-field crossing spread | drop skew | in-core drop spread med/p90/max |
|---|---|---|---|---|---|
| R23 base (R24) | 2243 | 157.3 | - | - | - |
| R24 re-phase | 3082 | 364.0 | 336.4 | 336.4 | 63.3 / 149.3 / 217.1 |
| W column only, no band drivers | 2838 | 398.9 | 365.1 | 362.0 | 63.5 / 190.9 / 247.1 |
| re-plan, no sizing | 2838 | 142.9 | 128.4 | 126.6 | 56.7 / 82.8 / 90.9 |
| **re-plan + adjcol x2 (final)** | 2838 | **122.4** | 102.6 | **101.4** | **58.2 / 82.1 / 87.1** |
| final, FF | 2838 | 114.3 | 97.2 | 95.9 | 58.9 / 79.6 / 83.3 |

- Partition-tap skew is 42.2 TT / 32.2 FF.
- A 16w drop-strap what-if gives only 7-12 % less spread for +17 % C, so it was not adopted.
- **MC (13 samples + nominal, per corner):** sigma vt 10 mV, wire 5 %, tree 2 ps/stage hierarchical, plus own-leg draws for
  the new leaves.
  - Worst crossing spread 197.4 TT / 194.7 FF; drop skew 177.2 / 177.6; partition taps 114.2 / 110.8.
  - In-core drop spread: worst max 122.2 / 121.6, worst p90 85.4 / 84.1 (mc_final_summary.json).
- **Droop.** One continuous mesh = one PDN region, so per 12.4a b1 the differential clock droop is 0.
  - Mesh C is 2838 pF, +26.5 % vs the R23 base and -8 % vs R3b. Switching power is about 1.67 W at TT
    (C V^2 f, 0.70 V, 1.2 GHz), plus 11,510 BUFx24 drivers. It goes into the shared droop model; there is no PDNSim.
- **Remaining structural floor.** The in-core drop spread (median ~58 ps) is the RC of the 1.16-mm row segment, driven only
  from the two bands. Mid-row islands (R3/R4/EF4 at V 535-665) are latest.
  - The next lever is a mesh driver in a mid-row in-core island (pushdown, 12.2a1; QC-CORES core rebuild). It is not
    plannable top-down.

## 3. E-strip islands vs A0 E-face pins (`r25_epins.py`, e_pin_windows.json)
- The plan pin tables (inputs/d51/cores/a0_{nk,nl}_pins.json, core frame, MX-invariant) list 528 E pins per type, all on M4.
  They span y 561.036-674.028: tap[0:507], tile_id[0:15], ck, rst_n, tie_hi/lo.
- Only EF5 (window 663.48 +- 4.32 + 0.5) holds pins: 24 per type. EF0-4 and EN1-2 hold 0.
- **POSSIBLE with identical 8.64 islands and the halo kept.** Shift the E pin block rigidly by -15.408 um (321 M4 pitches)
  to 545.628-658.62. That puts 0 pins in every window, for both nk and nl. The margin to the EF5 window is 0.04 um past the
  0.5-um access margin; a centred shift of -19.344 gives about 4 um on each side.
- The partner pins inside the partition move with the block (kit/pin-plan change for QC-CORES).
- Note: the legacy A0 `ck` pin is on this face (668.076). Under 12.8a the clock enters via the islands.

## 4. Die clock DRC re-run on the R24b M9 wide-VSS fix (LIVE, > 30 min)
- Chain chain.sh = the R17 chain on the fixed guard51 dry build (qc-mesh-r24/dryfix/dry): clock-alone kit -> combo
  --routed-clock -> route + RCX -> DRC on every clock box + STA -> report + drccls.
- Then `r25_samenet_gaps.py` matches the DRC markers against the 408 same-net VSS shield gaps found in mesh.json:
  24 at 0.04 um + 384 at 0.28 um, all on M9 (samenet_gaps_pre.json). This is the COORD GEOM-24 PASS-COND.
  - 0 marked = PASS. Otherwise the fallback is one shared shield between the two clock nets.
- ot-run unit oth-ubuntu-1828381-1793110415 on intel2, started 07:13, ETA about 3.5 h (R17 took 3 h 24 min).
- COLLECT: intel2:~/r25_drc.otrun.log (R25_DRC_DONE) + intel2:/srv/opentallas-scratch2/claude/qc-mesh-r25/drc/{drccls.txt,
  samenet.txt,samenet_gaps_drc.json,report.out}.

## 5. NOT DONE (needs the re-plan inside the plan tool first)
The guard51 rebuild with the new mesh, die GRT0, and main die_sta_related on the 997 seam pairs (FF hold under HB4 and
under the launch-side lockup latch) all need the drop lattice, band drivers, W column and DME band trees built in
qc_clk_mesh3 / die_clock_mesh. That is the next lane. The seam hold numbers are unchanged from R24
(-96.5..-100.6 FF, CHECKED there).

Renders (viewed): r25_wcorner.png (W edge + first two A0 rows), r25_centre_band.png (centre-facing bands).

## Die DRC re-run for the R24 M9 shield fix (2026-10-27 12:33 PDT, UNCHECKED)
Tree = R24 fixed dry build (qc-mesh-r24/dryfix/dry), full route + DRC via ot-run on intel2 (chain drc/chain.sh), run_route rc 0.
- 408 same-net VSS shield gaps (24 at 0.04 um + 384 at 0.28 um, all M9 side): **0 DRC markers on any of them** (drc/samenet_gaps_drc.json, verdict PASS). GEOM-24 PASS-COND met, so the shared-shield fallback is not needed.
- Total 24 unique markers, all "Min Step" on M8: 12 nets ckm_w_ckt_{17717..19929}_0, 2 each, at y 10749.22/10749.26, x pitch 2471.04 (one per partition column).
  - Cause: the short load branch (0.187 um, load 2204.253 -> trunk 2204.44). The R19 +0.08 end extension ends at 2204.173, 2 nm off the via enclosure edge.
  - This is a residual of the R19 Min Step fix, not the shield fix. Fix = plan geometry (snap trunk x to the load x, or extend the branch so the end clears the enclosure), no waiver.
- The clock_routed report step exited rc 2: the worktree was pruned mid-run, so the tool was missing. This is not a DRC result.
