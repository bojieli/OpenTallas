# DIE-S81-17 (2026-10-28): go15 intra-region skew root cause, structural fix estimate, CA bind fix

Data: intel2:/srv/opentallas-scratch2/claude/die-s81-17 (go15 = intel2 die-s81-16/go15, plan_s11 778e9af860b0).
Tools: main 410e940f4f (die_sta_related reproduces go15 exactly: TT intra hold -566.78 / FF -559.59, skew 925.38/838.48; CHECKED).

## 1. Root cause of the ~900 ps "intra skew" (scripts/skew_root.py, skew15_summary.json, regions_top.txt)

Per pair: hold damage D = (lc + latB) - (ea + latA) - cr = tree_ee (ec-ea) + unc_spread (lc-ec-cr) + lat (declared insertion difference).

(a) LABEL. The tool's `skew` (skew_diag) is raw tap arrivals WITHOUT the declared core insertion, so a planned-early core tap
counts its designed earliness as skew. Max real D is 523.8 TT / 513.5 FF (not 925/838). Worst pair bk_sel c3->t1:
tree_ee 778.9, declared lat difference -401.6 -> the c3 tap is ~377 ps OVER-early, plus unc_spread 146.5 + OCV 53.7. CHECKED.

(b) BULK (397/397 regions, 170k pairs): zero-logic declared pairs have a data floor of +35.7 TT (clkq_min - hold); mean negative pair:
tree_ee 3.8, unc_spread 50.2, OCV 34.6, unc 25 -> h -78. Dominant term unc_spread in 124k/170k pairs. Without unc_spread 137k
stay negative; without unc_spread and OCV 63k. unc_spread is the CLK-INV-CAL-2 double count (liberty inverter pin-cap range
on top of the spice-MC table). Not a tree defect. CHECKED arithmetic.

(c) TREE IMBALANCE (the tail, 284 of 397 regions' worst pair dominated by tree_ee): the region DME delay model is the BUFx24 1x
fit (STAGE_1X_TT d0 20.8 ps, k1 0.014 ps/um) applied to an inv2 tree. Fitted on 16604 go15 routed legs (scripts/cal_est.py, CHECKED):
inv2 = d0 12.5 ps, k1 0.162 ps/um, k2 0.00023, fanout +12.3 ps (TT); rms per leg 7.95 (cal) vs 30.8 (go15 model); routed/model
median 1.46 plain, 1.56 snake, 1.67 at fanout-2 nodes. The DME therefore balanced long legs against stacked near-zero-wire
inverters: svc_12 t1 path below LCA = 16 stages (6 at 1-4 um, ~11 ps each) vs t19 = 12 stages of 188-334 um legs (50-118 ps each)
-> t19 188 ps later with 4 fewer stages. Same form in svc_0/4/8/9/13/15, lk_EN2. The model error summed per path explains the
measured skew (svc_12 model-error 202 vs measured 188-200).

(d) EARLY-TAP DOUBLE COMPENSATION: go15 used --region-dme-early 1.78/1.53 (empirical hang-mode ratio from go13) on top of the
merge-mode sink delay. With the uncalibrated wire price the realised earliness is ~1.9x declared (bk_sel c3 779 vs 402).

ROM vs non-ROM (go15 rom taps at the old 285 TT = DIAGNOSTIC):
| class | pairs | neg | worst hold TT/FF | max D TT |
| rom (either end rom_elem_q core tap) | 33888 | 31956 | -237.5 / -235.8 | 209.1 |
| other core-tap pairs | 28882 | 26646 | -566.8 / -559.6 (bk_sel) | 523.8 |
| reg-reg | 116124 | 111300 | -522.9 / -466.9 (bk_sel), -311.5 outside bk_sel (svc_12) | 469.5 |
ROM pairs are not the driver; they fail by the same bulk mechanism (b).

Top 10 regions (TT): bk_sel -566.8 (over-early core tap + 3.2 mm snaked path, (c)+(d)); svc_12 -311.5, svc_13 -304.7, svc_8 -280.4,
svc_9 -275.8, svc_0 -272.5, svc_4 -262.9, svc_15 -247.6 (reg-reg, (c): 2.4-2.8 mm regions, tree_ee 125-188); s_7S_C -259.4
(core xfin->capc5r: declared lat 167.6, i.e. declared insertion spread between core types inside one region); s_5N_L2 -246.0
(ve_m core tap tree_ee 236 vs declared 58: over-early, (d)).

## 2. Structural fix ESTIMATE (UNCHECKED projections from go15 legs; nothing built)
Calibrated DME (die_trial --region-dme-stage-cal, DIE-QC-21 form, on main) with inv2_stage_cal_s81_go15.json and early ratio 1.0:
region max-pair nominal skew (sum of per-leg residuals below the LCA) p50 103.5 -> 46.1, p90 146.5 -> 74.3, max 506.5 -> 286.1 (bk_sel)
TT; FF p50 94.5 -> 40.4, p90 134.2 -> 66.4. A uniform rescale alone does not fix it (p50 93.6). Same-region cores enter at matched
insertion by the merge-mode sink delay with the calibrated model (no fudge ratio). Hold on zero-logic declared pairs stays
negative until the unc_spread double count is removed (CLK-INV-CAL-2 spice_edge, pending NUMBER-CHECK) and the kit-contract
window carries the residual. bk_sel (2.4 mm, 51 taps, 680 um snakes) still ~286 after calibration -> needs its partition tree
re-cut (two region roots) - estimate before any change.

## 3. CA bind width rc 1 (FIXED, shared tool)
count_align_bind --parts ocv indexed r["src_part"]; S81 landed_phase_ocv rows are partition-level (src/dst ARE partitions, no
src_part/dst_part), so every S81 bind since go12 raised KeyError. Fix ocv_parts(): fall back to src/dst = the
count_align_plan.row_ports identity (named rows unchanged). Test added; test_count_align_bind PASS. go15 rerun (main + fix):
bind width rc 0; CA STA 2306 crossings TT worst lo 104.4 / FF 105.0, fail 0, start-skew fail 0/1139, PASS (cabind_go15_status.txt, CHECKED).
