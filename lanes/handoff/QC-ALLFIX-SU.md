# QC-ALLFIX-SU handoff (family helper for QC-ALLFIX; su rows)
Updated 2026-11-23 18:1x PST. Dir: epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX-SU (OT_LANE=QC-ALLFIX-SU), rt 70b6f0430ea9.
Base: compose A f418c1b290f3 (QC-ALLFIX/cA/rows/plan_b25_tapoff.json). Tree QC-ALLFIX-SU/tree (C4 fork 88451f71a4fc).
GOTCHA: rt_launch_tree launch dirs SYMLINK physical/ into the tree -> installing a plan in any launch changes the tree plan for all launches. One gate at a time per tree. The tree asbuilt carries RED2.
Rows:
- RED2: rows/red2/row_red2.py 4f7bc6a20d45 + red_fault_r8_extra.json 3daaf93866cb. ROW-REBASED posted 18:1x: PRE no new finding; scoped strict sle_su_c: 6 red_fault sinks land 2.
- SU2R (rc105 + su_c re-floor): rows/su2r/ pipeline: su2r.py 93092cbc56e2 (lift +151.2, north band fixed, cws1/cws2 +1 station, waist rows x_su_l1_o/x_su_l0_i off y340) -> suc_n.py de5bbb9f30ea (SUC-N: x_ctl_o +108 um and x_sc_o +116.64 um on su_c N with stm/sc partner pins/bands/edge clocks) -> fable-fix-qc-v4/addtap.py --fix + rt retap.py (OLD = cA) + tap_offset_cover fill (su_tapfix2.sh) -> su_lat.py (24 cws lanes stations/cycles +1) = plan_su2r_g.json db537389cc92. Gate g_gate (PRE + G0), g_gate.ot; earlier SU2R-only PRE: TAPNAME x3 (fixed by addtap/retap), ROWS-NO-PROOF inherited.
- rc103 / hg-HOLD-SKEW / hg-RESET-ASYNC su_l1: IN BASE (tap_reset_split + tap_pair_affinity), REASONED-probe.
- Open: x_su_l0_o q[150]/[103]/[105] stage-0 legs (kit placement, no plan per-bit table): judged on the su_c probe after SU2R.
