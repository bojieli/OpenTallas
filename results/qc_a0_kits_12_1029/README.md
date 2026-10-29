# QC-A0-KITS-12 (2026-10-29) — node flow record check, NK both-reset source proof + one placement prototype

Base: codex/qc-a0-0251@b41fd652f (Codex inputs, used as-is for GEN; no merge of private ancestry into main is requested).
Run dir: intel2:/srv/opentallas-scratch2/claude/qc-a0-kits-12-1029.

## 1. Flow releases (CHECKED, intel2 ~/coord/autopilot/signed.tsv)
- romleaf AP f6f8b3444406 -> flow-20261029-a-qc (TT +147.74 / FF +3.80); rawleaf AP 53fcde6a6c40 -> flow-20261029-b-qc (TT +90.23 / FF +5.40).
- Node (COORD 02:43 HOLD: the tag must contain a615f444b). Measured: the tools/orfs_hold_mm.tcl staged in the node kit
  (epyc2 codex-qc-a0-2340/node_finalff, sha256 d8c3df3a) is byte-identical to the d9716851c copy, not a615f444b (5cf5ab04).
  a615 changes only ot_rc_cal_restore, and 0/38 kit logs contain any OT_RC_CAL line, so that path never ran.
  The view flow = d9716851c = flow-20261029-c-qc (0 watched-file diffs, also with orfs_hold_mm.tcl added to the watch set).

## 2. NL fresh-gate LEC (Codex, verified)
main results/codex_qc_nl_lec_0251: EQUIVALENT, compare 31742/31742, joint 12570, kept 9881 / 0 missing / 0 constant,
wrong-representative control 28 differs CAUGHT (CHECKED from summary.json + native_proof.log).

## 3. NK both-reset candidate (recipe results/codex_qc_a0_0251/nk_both_reset_recipe.json, suffix a0nk12rstboth)
- GEN PASS (19 hard children, 2584 pins, kit_hash 71b5196e94317414). The relay feeds BOTH t_out[513:512] and n_y[513:512] (RTL grep CHECKED).
- SYNTH, SELRANGE PASS (0 unwaived), SDC_LINT PASS, FACE 2582/2582 (CHECKED).
- Native LEC (synth_lec.sh; profile = the proved rstwave native profile, every relation re-proved): joint 12508/12508,
  compare 34816/34816 EQUIVALENT, kept 10912/10912, 0 missing / 0 constant, 0 profile rows skipped (CHECKED, nk_rstboth_lec_summary.json).
  The +1 boot-edge behaviour is covered by the Codex miter (nk_both_reset_miter.log PASS: 1044 active, 939+1044 wrong controls caught).
- Relay home (relay_probe.tcl on NK 2_floorplan.odb): street x 135.648..137.808 has edge TAPs (w 0.108) at 135.648 and 137.700
  in every row, so the free span is 135.756..137.700 = 1.944 um. The 1.08-um relay at x 136.188..137.268 clears both by 0.432 um (CHECKED).
  The root site 311..315 x 668..672 overlaps no instance.
- Anchor projection (nk_anchor_project.py): the reviewed NL reset6 FF anchors whose names exist in the NK synth, plus the 8 contract
  reset-capture anchors. 803 NL names are absent in NK. v1 kept anchors in the 1.944-um street between the rawfault column (+halo)
  and the NODE halo (x 388.10..390.04): DPL-0033, 2 FFs on TAPs (place_fail1_dpl_street.log). v2 leaves the 2866 NL anchors
  at x >= 383.664 over the NODE y range to GPL (placed by connectivity) and anchors 10595.
- ONE placement (v2, placement only, no CTS/GRT), AUTO-GEOM without GRT (geom_rules --all-kits, CHECKED; PNG VIEWED):
  r2r max 634.61 (first Codex NK placement 836.41), 124 captures > 405 (was 706), relay_collapse 20 (unchanged),
  channel_h 1.174 / channel_v 1.845 / col_v 1.696 (above the 1.0 hard limit), aspect 2.528, partial_face 2, pin_reg p90 8.45, cells_on_macros 0.
  Worst reach: n_b_q[513] -> g_icg.dr[2] (the ICG enable path). Worst relay: e_first -> u_tx q[388], 13 hops, max hop 559.
  Picture: the NODE takes the 65-um east column where NL keeps about 3000 ME FFs. In NK those FFs crowd the narrow horizontal streets
  between the rawfault rows and the street west of the NODE. VERDICT: GEOM FAIL. The NK upper half has too little std-cell space;
  anchors cannot fix that. NO CTS/GRT.
- AUTO-GEOM GRT probe (50 iterations) still running: nk_geom/grt.log, cong.rpt, then auto_geom.json/png (geom_check.sh).

## 4. NL ICG0 typed placement (Codex unit oth-ubuntu-582810-1793274530, adopted, not killed)
GPL did not converge. After the routability revert (iteration 4710), overflow fell to 0.20 at 4830. Then HPWL grew from 1.8e6 to 2.7e7 um
while overflow stayed at about 0.5, and the penalty reached 9e30 by iteration 20630 (06:3x). Divergence detection never fired. In reset6 it
fired and reverted to the overflow-0.19 snapshot. No 3_3 odb yet.
