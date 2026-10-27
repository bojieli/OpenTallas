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
