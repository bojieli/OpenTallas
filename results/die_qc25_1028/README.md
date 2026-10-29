# DIE-QC-25 (QC die owner, successor of DIE-QC-24) -- 2026-10-28 PDT

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc25-1028 (plan/ev_qc25.json, fit24.json, legcls25.json, check25.log).
Adopted from DIE-QC-24 (not re-run): g24 gate and trial15x kit in intel2:/srv/opentallas-scratch2/claude/die-qc24-1028.
Branch claude/die-qc25-1028 (from claude/die-qc24-1028@308a1adfba). Worktree intel2 wt/die-qc25-1028.

## 1. SU bind form (COORD 22:32 ASK2 = form (a): split u_suvm) -- map of record
- physical/die_plan/qwen_compute/bind/asbuilt_map_p6.json + rule `dvs_([WE]\d)\.u_core\.u_sub\.u_suvm\..*` -> `sl_\1_su_c`
  (commit a10349f943). Same rule as TOK-QC-3's private asbuilt_map_tokqc3.json (CHECKED: parts identical, rule SET
  identical, only the order differs; rules are fullmatch and do not overlap). TOK-QC-3 bind10 with this rule and
  qfd_dv_s8_suvm_rp1 + qfd_dv_s8_vm8q_rp1 dissolved: 0 strict errors, 0 unmapped (their run, read CHECKED from
  epyc2 tok-qc-3-1028/bind10/bind_report.json).
- One catch-all rule, no per-sub-instance split: every u_suvm descendant (va/vb/vc/pg/cl/ch/bt/su8 hard cores and the
  u_rs*/u_vw*/u_rd*/u_tw*/u_cr*/u_ra*/u_oa relay glue) belongs to su_c in all three su_c types (CHECKED, ev_qc24
  partition_types contents). No-op while u_suvm is bound as one leaf.

## 2. crh lineage: plan event ev_qc25 (scripts/plan_event25.py)
- ev_qc24 e12e39da0fae -> ev_qc25 f72264b77b08. sle_su_c (sl_E0..E5_su_c) u_cl / u_ch: qfd_dv_s8x_crh (259.2 x 276.48,
  early tap 292.49 / 240.62 ps) -> qfd_dv_s8_crh_rp1 = the module the ONE-QC RTL (qfd_dv_s8_vm8q_rp1) instantiates in
  every slice; W types already carried it. Copied from slw_su_c__cl92142dac: module, outline 250.56 x 216 (signed view
  autopilot f4g 5ed4500430; fits inside the old footprint at the same origin), pins_file, note; clock taps u_cl.ck /
  u_ch.ck at the W pin offset, common latency 250 / 202.5 ps. Script asserts only these keys change; 0 s8x_crh refs left.
- tools/die_plan/check.py on ev_qc25 vs ev_qc24: finding set IDENTICAL (187 findings, 0 new, 0 gone; the 24 G0 errors
  are the ev_qc24 baseline), core views 17 -> 16 (CHECKED, plan/g0_report.json both dirs).
- Consequence: the next QC clock trial must be planned on ev_qc25 (2 crh taps per E su_c move off the early target).

## 3. trial15x: --rep-on-leg + guard 50 (DIE-QC-24 fix check) -- PASS
- Kit trial15x (trial15 form: snake cap 1200 + --rep-on-leg + --rep-off-leg-max 50, ev_qc23pg): exit 0, i.e. the guard
  did not fire (CHECKED kit15x.log). Independent check slide23.py: 24,408 leg repeaters, 0 > 50 um, max 0.6 um off-leg
  (trial15 without the fix: 28 cells at 146.8 um); slide24.py: 0 slid > 50 (CHECKED).
- trial24 (stock tree, guard only): 25,142 cells, max 7.0 um (CHECKED, same script).
- QC kit recipe from now on: `--rep-on-leg --rep-off-leg-max 50` on every QC die_trial kit (die-local recipe change,
  no shared default flip; the flags are byte-identical on clean legs per test_die_trial_rep_on_leg.py).

## 4. Region-DME leg model calibrated on routed legs (shared fitter, DIE-S81-18 fit_dme_stage_cal.py @b7a6297642)
- trial24 (== trial14) routed clock-only GRT legs, 12,626 DME legs, inv2 EVEN_LEGS: refit TT d0/k1/k2/kf
  13.93 / 0.0977 / 0.000161 / 10.46 (rms 7.11 ps, |res| p99 20.6) vs the cal the tree was built with
  (results/die_qc21_1028/inv2_stage_cal_trial13b.json: 16.77 / 0.1097 / 0.000167 / 10.95, rms 13.66 on these legs;
  median measured/built 0.865). FF 11.78 / 0.0860 / 0.000150 / 7.74 (rms 6.53 vs 12.31). CHECKED.
- Stable across trees: the same fitter on trial13b's own legs gives TT 14.05 / 0.0963 / 0.000173 / 9.58 (rms 7.47; the
  13b cal file scores 14.15 on its own legs). So the 13b cal (DIE-QC-21 validate.py regressors) over-prices every leg by
  ~13 % vs how die_trial places inv2 legs (even stage counts) -- a model-form mismatch, not tree-to-tree noise. CHECKED.
- Per-class (legcls25.py; straight 10,623 / snake 1,787 / routed 216 legs), per-TAP accumulated model error (sum of leg
  residuals root -> tap) and its per-region spread (= skew the model cannot see), TT:
  | model | leg rms | tap |err| p50/p90/p99 | region spread p50/p90/max |
  | built (13b cal) | 13.66 | 99.7 / 136.4 / 157.4 | 89.4 / 104.8 / 120.7 |
  | global refit | 7.11 | 14.5 / 42.4 / 62.8 | 49.4 / 67.1 / 115.6 |
  | per-class refit | 6.67 | 12.8 / 42.4 / 64.5 | 51.5 / 73.6 / 122.5 |
  | per-class, 2-fold by region | 6.72 | 12.9 / 42.5 / 65.5 | 51.6 / 73.0 / 120.4 |
  Caveat: DME legs only (tap legs, early targets and planned per-tap offsets not in the sum), so the spread is a model-
  error diagnostic, not the routed skew (routed trial24 spread TT p90 76.7). The ranking of models is the result.
  FF the same pattern (built 79.6 -> global 47.0 -> per-class 47.6 region spread p50). Per-class coefficients differ
  (snake kf 15.7 vs straight 8.5) but do NOT improve the tap-level error: use the GLOBAL refit.
- Output: results/die_qc25_1028/inv2_stage_cal_trial24.json (load_stage_cal format; tap copied from the 13b cal).
  The next QC tree trial uses --region-dme-stage-cal inv2_stage_cal_trial24.json. Residual per-region model-blind
  spread ~50 ps p50 remains (deep ~8-leg region trees): that is the mesh case (section 6), not a model problem.

## 5. Gate g24 (DIE-QC-24 trial24 = trial14 stock tree, ev_qc23pg, --clock-cal spice_edge) -- CHECKED (read of g24)
- Intra kit-contract hold W180: plain +46.68 ps (0 neg); WITH clock OCV +8.30 ps (0 neg; worst c_W2_bn_01 t21 -> t8,
  need 171.7 of 180) -> mesh trigger (a) does NOT fire on g24. Seam W180: +117.43 plain / +89.16 OCV PASS.
- Related pairs: TT setup intra +110.24 / seam +240.84 (0 neg). CA 2537 crossings TT worst lo 105.6 / FF 105.1, 0 fail,
  PASS. Real-view intra pairs (3360): TT setup +215.2, FF hold -79.58 (685 neg; raw, --hold-buffers none).
- Freeze-gate verdict: FAIL closed, same categories as g15: 780 early A0 core taps without a signed view (view mode;
  declared mode intra FF raw hold -170.9), and the plan-defined landed class (TT setup -806.86). No new failure class.
- Attribution (CHECKED, g24nocal = the same proof/arrivals/bind_clock, die_sta_related WITHOUT --clock-cal spice_edge):
  intra W180+OCV -60.14 (260 neg, same worst pair c_W2_bn_01 t21 -> t8), plain -21.26 (19 neg). So the trigger-(a)
  clearance (-60 -> +8.3) comes entirely from the COORD-ruled freeze-gate clock number (spice_edge, NUMBER-CHECK-INV-1
  PASS), not from a tree change; the margin is thin (8.3 ps of 180).
- Not computed here: skew as arrival minus planned target (the shared die_sta_related change from DIE-S81-18 is not in
  this lane's tools snapshot); gate25 (trial25) runs the same snapshot -> successor reruns die_sta_related from main.

## 6. trial25 (running) = stock form on ev_qc25 + refit cal + --rep-on-leg + guard 50
intel2 die-qc25-1028/chain25.sh (kit -> bays -> overlay -> clock-only GRT TT/FF docker 48g -> snake/val -> gate25 ->
g25). Started 23:17; kit ~45 min, gate ~1 h after GRT -> DONE ~01:15 PDT. Collect: chain25.status, g25/chain.log DONE,
read_gate25.py g25; routed spread vs trial24 (TT p90 76.7, >92 ps 10 regions); fit_dme_stage_cal on trial25 legs
(should now show median measured/built ~1.0).

## 7. Waiting on others
- A0-quad mesh (task 5): QC-MESH-PILOT-2 DRT verdict not posted yet (pilot collect after 23:45). No plan work started
  (trigger (a) does not fire on g24; mesh adoption stays CONDITIONAL on pilot pair U <= 61 ps).
- a0k6s view (task 6): not re-signed yet (QC-A0-KITS-9 on parent ICG work). TOK-QK-PEER pair image at the next bind
  (TOK-QC-4 on ev_qc25).
