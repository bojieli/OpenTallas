# QC-ALLFIX-SU handoff (family helper for QC-ALLFIX; su rows)
Updated 2026-11-23 17:5x PST. Dir: epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX-SU (OT_LANE=QC-ALLFIX-SU), rt 70b6f0430ea9.
Base: compose A f418c1b290f3 = /srv/opentallas-scratch2/claude/QC-ALLFIX/cA/rows/plan_b25_tapoff.json. Tree: QC-ALLFIX-SU/tree (C4 snapshot fork 88451f71a4fc; plan replaced by compose A; asbuilt has RED2 applied).
Rows:
- RED2 (RED +2): rows/red2/row_red2.py (4f7bc6a20d45) + red_fault_r8_extra.json (3daaf93866cb). Tree-file row: copies the table to runtime/zz_extra_red_plus2_c4.json and appends it to asbuilt land_r8_extra (fix for plus2_c4_1123 'native clock table outside base'). Gate: red2_gate (PRE + strict bind --types sle_su_c), red2_gate.ot.
- SU2R (rc105 SU-2 rebased + waist split): rows/su2r/su2r.py (93092cbc56e2) -> plan_su2r.json (697a949e63c5). Middle row +151.2, north band unchanged, cws1/cws2 +1 street station (fixes the 24 G0 hop errors), x_su_l1_o / x_su_l0_i rows off y340. Gate: su2r_gate (PRE + G0).
- rc103 su_l1 tap affinity, hg-HOLD-SKEW, hg-RESET-ASYNC (su_l1): IN BASE (tap_reset_split + tap_pair_affinity chains/ring_depth 3/macro_follow on all su_l1 types). REASONED-probe. cbf_q00__cl1b5a6458 lacks tap_reset_split (cb family; told integrator).
- su_c north (x109 x_ctl_o / x999 x_sc_o face flops + ft terminations): not in SU2R; needs N window spread with stm/ctl neighbours.
- q[150]/[103]/[105] x_su_l0_o stage-0 reseat: no per-bit table in plan (kit placement); open.
