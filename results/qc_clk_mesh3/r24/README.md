# INFRA-FIRST-QC-R24: guard51 die GRT, signal-environment clock C, env MC + related-pair STA, R17 DRC, strap lattice

Lane INFRA-FIRST-QC-R24 (2026-10-27, successor of R23, which died). Branch claude/qc-mesh-r24-1027 = main 8810c5e6a4 +
cherry-pick of ONLY codex/qwen-1027@5ce987747 (Codex R23 51.84-um guard candidate, results/qc_clk_mesh3/r23).
Inputs read-only: Codex package intel2:/srv/opentallas-scratch2/claude/codex-qwen-1027/pkg (plan sha256
37937a8691f9155b19f76998af3811b478f3961d17127c0968e7c5c5aac9b53b). Lane runs: intel2:/srv/opentallas-scratch2/claude/qc-mesh-r24.
Labels: CHECKED = independent NUMBER-CHECK sub-agent with its own parsers; UNCHECKED = one tool output.

## 1. guard51 die GRT (Codex job oth-ubuntu-366583-1793102932, collected) -- CHECKED (NUMBER-CHECK-QC-R24)
- TT and FF: overflow 0 on every layer M4-M9, EXIT 0, `global_route -congestion_iterations 50` (combo.tcl:580267).
- Usage on the derated resource: M4 3.42, M5 6.33, M6 3.84, M7 7.41, M8 0.55, M9 1.06 %, total 2.94 %; WL 608,145,969 um;
  482,856 routed nets = 449,153 ft_ + 33,702 ch_ + 1 rst_n, 0 duplicates; the 4,646 clock nets (11,566 fixed segs) are
  obstructions, not in the guide. TT and FF guides byte-identical. kit: 304 channel ports / 143,144 bits; abutted pin check
  2,689 ports / 1,137,335 bits, 0 bad, PASS.
- 20 GRT-0036 (info): t_g* M8 tap ports on the EAST edge, centre x 31216.293 (0.027 inside W); the 1.28-um pin box overhangs
  the die by 0.613 um. Cause = pin-box size at the edge, not a misplaced tap. Fix in the next plan delta (pin box inside).
- Files: grt_{TT,FF}_usage.txt. Collect paths: pkg/out/guard51/{kit.log,combo.log}, dry_exact/combo_{TT,FF}.log, GUARD51_GRT_DONE
  in build_guard4.otrun.log.

## 2. Signal-environment clock C (replaces the clock-only empty-M7 RCX and the full-plane model)
Tool `clk_env_density.py` (lane script): per fixed clock segment, die-top GRT density per layer from the guide (gcell 10.8 um,
integer-DBU gcells, 1 track per guide rect per gcell, raw tracks), plus the plan partition reserve (die_trial adjust 0.75 of M4-M7
belongs to the partitions) at utilisation u; fd2d cross-sections in the STAGE-TABLE basis geometry (16w 0.64 um, thin 0.04-um
shields at 0.08, asap7_m8m9_cal.json heights/eps) mixed by coverage -> per-net k = C_env / C_model, length-weighted M8 + M9.
NUMBER-CHECK-QC-R24b found two bugs in the first version (float gcell floor -> density x1.4; model basis 0.807 instead of the
stage-table 0.5022 -> k x0.62); both FIXED here, the numbers below are the fixed run (env3), the earlier env/fold2 runs are void.
- 97.2 % of the 1,562,338 um clock wire (875,756 M8 + 686,583 M9) lies over partitions (gcell; 96.47 % exact) -- CHECKED.
- Die-top GRT density under the clock is small: M7 under M8 clock 3.05 %, M6 2.80 %, die-mean M7 1.76 % -- CHECKED (checker's
  values; the fixed tool reproduces 3.047 / 2.802 / 1.755). So the real environment is set by the PARTITION-internal M6/M7
  routing, which the die GRT cannot see; u brackets it.
- fd2d C (fF/um), basis geometry: M8 over full M7 plane, open top 0.5026 (= stage table 0.5022, model basis); M8 M7+M9 planes 0.829;
  M8 over M5 open 0.275 (clock-alone); M9 over M8 plane 0.494 (RC3 0.4938). UNCHECKED (fixed run).
- per-net k median 0.619 / 0.799 / 0.963 at u = 0 / 0.5 / 1 (checker's independent fixed-basis estimate 0.517 / 0.746 / 0.952 with
  its own geometry choices). UNCHECKED.
- Fold `r24_envfold.py` (qc_clk_mesh3 --top-edge-corr format): stage_env = D0 + (seg - D0) * k_net on every legal stage
  (2,158 top edges, 4,644 stages, 0 unmatched); edge k median 0.796 / 0.893 / 0.980. fold_env_u*.json.gz.
  Approximation: wire-load part scales with C; stage table not re-simulated (next step).

## 3. Effect on the clock (nominal, solve sample 0, legal geometry) -- UNCHECKED (fixed run)
| variant | tap skew TT / FF | insertion TT |
|---|---|---|
| model (full M7 plane) | 22.97 / 21.06 (CHECKED) | 6672-6695 |
| env u=0 | 34.86 / 29.24 | 5370-5405 |
| env u=0.5 | 33.86 / 28.57 | 5516-5549 |
| env u=1 | 31.04 / 26.02 | 5650-5681 |
ROOT CAUSE of the +8..12 ps: the top tree is balanced on uniform full-plane delays, but the measured die-top ft density differs
per column/branch (regional, column-level offsets: c_E3/c_W1 bn early, sl_E1/E2 + coll_f3/f4 + glue/native59/tt_ctlm late; pattern
nearly independent of u = it is the GRT part). STRUCTURAL REBALANCE (task 3) NOT DONE: needs the plan tool to balance merges on the
env fold (12.8 d1: plan-computed from plan geometry + measured die-top density, before any build).

## 4/5. MC (13 + nominal) + main die_sta_related (shared model, 997 seam pairs, AOCV 0.21 %/mm, droop shared) -- UNCHECKED except model
| run | MC worst tap skew TT/FF | TT setup | FF hold (zero-logic) | kit W40 plain / core views |
|---|---|---|---|---|
| model | 329.1 / 284.7 | +540.09 | -115.32 (CHECKED recompute) | +29.36 / +14.39 PASS |
| env u=0 | 260.9 / 223.4 | +558.51 | -96.47 | +23.31 / +9.41 PASS |
| env u=0.5 | 268.1 / 232.3 | +556.03 | -98.75 | +23.93 / +10.05 PASS |
| env u=1 | 277.4 / 240.7 | +554.02 | -100.62 | +24.52 / +11.27 PASS |
- Model run on the d51 plan gives the R18 base numbers (+540.10 / -115.32): worst pair sl_E0_hc0 -> c_E0_tn_00, both taps in the
  upper half, shifted together by the wider channel (plausible, NUMBER-CHECK; no R18 arrival file to diff).
- Worst FF hold = zero-logic seam (all 997 pairs negative): the owner-approved HB4 data hold buffers or the launch-side lockup latch
  must close it. HB4 count (pkg r11 rule) 2.63-2.66 M cells (inflated by the tport floor per NUMBER-CHECK-QC-R19; per-endpoint form owed).
  LATCH form: R22 model PASS on R18 f64; re-run on these inputs = next lane.
- INFO (checker): pair_unc.json carries 142 unordered non-plan-port pairs; one (c_W0_tf_10 -> c_E0_tf_00) would be -88.36 in the
  model run; not gated (not a plan port).
- NOT INCLUDED: the A0 in-core drop loads and the "fixed MC tool on main" (tools/die_plan/kv_r18/mesh_mc18.py, 78c678c920, the KV
  ngspice mesh MC); the run above is the qc_clk_mesh3 model MC.
- Runs: intel2:/srv/opentallas-scratch2/claude/qc-mesh-r24/run/{model,env00c,env05c,env10c}; mc_sta_summary.json, nominal_skew.json.

## 6. R17 DRC (epyc2 unit oth-ubuntu-1796220-1793090377, finished 05:03) -- UNCHECKED (one tool run)
20,857 / 20,857 boxes, 147 unique markers: 96 Min Step M8 (VIA78 end, fixed in R19 encoder, replay 198 -> 6), 24 + 24 M9 Metal
Spacing VSS at the WEST column x 2176.14 (leg + t_g* port, ckm_w_ckt_36/85 ...), 2 M7 spacing + 1 M7 short at the centre row
y 13132.7 (the lane-0 channel stacks that guard51 removes). report.out failed only because the R17 worktree was removed.
r17_drccls.{txt,json}. The 48 west-column M9 VSS spacings are a new class for the guard51 DRC to check.

## 7. Strap lattice for the 51.84 channel (QC-CORES) -- UNCHECKED
strap_lattice_d51.json (r22_strap_lattice.py with the guard51 solver args, main qc_clk_mesh3): M9 vertical 142 straps x
2177.28..31207.68 (207.36 x109 / 198.72 x28 / 216.00 x4), M8 horizontal 170 straps y 734.40..25580.16 (146.88 x118 / 138.24 x40 /
172.80 x5 / 155.52 x3 / 345.60 x1 = centre channel / 164.16 / 144.00), 8w 0.32 um, 24,140 crossings. vs R22 d43: every strap
above the centre channel moves +8.64 um (centre gap 336.96 -> 345.60), x unchanged. plan sha matches.

## Next (successor)
1. Rebalance the top tree on the env fold (plan-time, d1-style) with u = 0.5 as design point and u = 0/1 as corners; target
   nominal tap skew back to <= ~25 ps under all three.
2. Re-simulate the stage table at env C (ngspice) instead of the linear wire-part fold.
3. Port kv_r18/mesh_mc18.py to the QC mesh with the ~20k A0 drop loads; then die_sta_related per endpoint; HB4 (per-endpoint) and
   launch-side latch in parallel, first to close wins.
4. guard51 clock-alone DRC (west-column M9 VSS spacing class) and east-edge pin box.

## 8. COORD 06:2x (GEOM-22) items -- R24b
### (2) R17 DRC: 48 M9 Metal Spacing to VSS at the west-column centre rows -- ROOT CAUSE + STRUCTURAL FIX (generator)
- Root cause: NOT the PG grid (the combo has no PG M9) and not the centre channel. Two different clock nets on M9 sit 2.80 um apart
  (e.g. ckm_w_ckt_85_0 row-end leg x 2175.72 and the column trunk ckm_w_ckt_98_0 x 2178.52). Their drawn VSS shields (0.64 at +-1.14)
  overlap and merge into one 1.16-um VSS shape. ASAP7 M9 SPACINGTABLE WIDTH 0.99975 at PRL >= 1.8 then needs 1.0 um, but both clock
  metals are 0.50 um away. TrackRouter's R8 wide-merge check (`merged_width`) only counted PG stripes, not the drawn shields of other
  clock nets.
- Fix: `tools/die_plan/die_clock_128.py` TrackRouter.place now runs merged_width over self.ix, which holds PG plus every reserved
  shape. Regression test `test_clock128_r8.py::test_wide_merge_counts_other_clock_nets_drawn_shields` fails without the fix and passes
  with it; r8 5/5 and shield 11/11 tests pass.
- guard51 dry build re-run with the fix ($S/dryfix/dry, 8.2 s, the same plan sha 37937a86): proxy check `wide_vss_check.py` gives
  baseline 24 wide M9 VSS pairs / 48 metal violations (= the R17 count; columns x 2176, 4647, ...), fixed 0 / 0.
  48 nets move by one 0.08-um track; tree wire 1562.338 -> 1562.348 mm; 120 M9:wide_merge_skip. UNCHECKED (NUMBER-CHECK-QC-R24c
  running). A die DRC re-run on the fixed build is owed (combo + DRT DRC, >30 min).
### (1) A0-CLK-R3b strap re-phase adopted in the R24 lattice + mesh RC with the 16,896 drop loads -- FAIL as specified
- `r24_rephase.py` keeps the R23 straps outside the A0 field (channels, inter-row and centre bands) and every driver column. It
  replaces every M9 over an A0 column and every M8 over an A0 row by the R3b drop straps. The W-column extension is included:
  M9 from 1762.56 and M8 from 250.56..26066.88.
- Result: 240 M9 (48 kept + 192 drop), 178 M8 (50 kept + 128 drop); 16,896/16,896 drops on M9xM8 crossings. Loads are 1 island
  driver input each at the crossing, with stub 0.
- Whole-die linear RC mesh (qc_clk_mesh2 netlist/solve, thev_r2, 6,156 drivers unchanged), TT nominal:
| lattice | C_total pF | crossing spread ps | drop skew ps | in-core drop spread med/p90/max ps |
|---|---|---|---|---|
| R23 base (no drops attach: 0 crossings at islands) | 2243.2 | 157.29 | - | - |
| re-phase (R3b) | 3081.8 | 363.96 | 336.41 | 63.3 / 149.3 / 217.1 |
| keep R23 + add drop straps (R3b alt) | 4660.5 | 418.84 | 365.10 | 51.1 / 138.0 / 209.2 |
- CAUSE (structural): (a) the 192 drop M9 straps lie inside the cores and run the full die height. They are fed only through M8
  crossings from the channel driver columns. (b) The W column (x0 1650.24) has no driver column W of it (first one 2177.28), so its
  4 drop straps are driven from 400 um away; the worst cores are c_W5_*_01/11. MC samples were not run because the nominal already
  fails; droop is not re-run (mesh C +37 % -> switching current +37 % into the shared droop model).
- NEXT (plan tool, 12.8 d1): re-plan the mesh drivers on the A0-commensurate lattice. Put drivers ON the drop straps: one driver
  per drop M9 per A0 row band, fed from the tree like the R23 row drivers, plus a W-edge driver column at x 1650.24-8.64. Segment the
  drop M9 straps per A0 row (no full-height interior straps). Then rerun this check with MC + droop.
  Shared pieces: 0.5022 basis, thev, 377/960 partition taps attach (pre-existing in base too, needs the d51 tap snap).
### (3) E-strip islands vs the A0 E pin face -- NOT CONFIRMED (geometry conflict)
- R3b E strip EF0-5/EN1-2 centre x 452.0, footprint 447.68..456.32. The A0 E face is at 457.92, leaving a 1.60-um gap (not ~4 um).
  A 4.32-um pin-access keep-off (the BTAB ruling value) needs centre <= 449.28, i.e. footprint 444.96..453.60. But NK hard children
  reach x 441.936 + 5.4 halo = 447.34, so 8.64-um islands cannot meet both (6.26 um free). NL has room (435.456 + 5.4 = 440.86).
- The A0 E-face pin y/layer list ("original y/layer values retained", Codex b7da9afaa) is not in a file I could find, so the pin-y
  overlap with the 8 island y-bands is NOT CHECKED. Options for QC-CORES: E-strip islands 4.32 wide on NK; E halo 5.4 -> 2.16 for the
  strip; or the pin plan keeps M4/M5 pins out of the 8 island y-windows (+-4.32 + spacing).
