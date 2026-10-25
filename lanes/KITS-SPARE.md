# Lane KITS-SPARE (started 2026-10-25 08:13 PDT): kit NEEDS-KIT items on spare fleet capacity only
Rules: item NOT on a PATH-* cut, NOT in a pending plan delta (TYPE-REDUCE folds, KV-PLAN3 fwd_reach, QC-PLAN3, S81-PLAN2/LEAF3, head delta),
die canary not FAIL at kit stage; current generators (per-corner basis, calibrated RC, reg_fanout + lint gates); GEOM REQ via autopilot
--geom REQ; <= ~6 own items waiting for GEOM. Path items have priority at review.

## TRIAGE 2026-10-25 08:13 PDT (OWNERS.tsv tick 08:02; canary runs *_202a50a59_1025_0648)
Canary kit stages (lint..rc_file): qwen_kvsys PASS, qwen_compute PASS, s81_head PASS, s81 running (lint PASS), hbm FAIL (face_guard, rc_file) -> HBM excluded.
Excluded (with reason):
- HBM (225 NEEDS-KIT): canary FAIL at kit stage + TYPE-REDUCE master keying + strap ruling integration (HBM-KITS/PATH-HBM).
- KV: hg/hgi/pv/pc/phy/sys_SD/io/hub/hroot in KV-PLAN3 delta (fwd_reach FAIL incl. kv3_hroot; R8 pads); sys_c on PATH-KV; qkd_hr_* x15 in KV-CORES plan delta (host clocks -> die clock);
  kvs_ctl = FIX (GEOM FAIL 05:45, KVG3-CORES); ot_qwen_tp8_pv_join_t = netlist fix (face_guard shared 513), not a kit.
- QC: all sle_*/slw_*/cb*/coll_ft*/phy_serdes*/su_lane* in QC-PLAN3 / TYPE-REDUCE delta; glue/native59/phy_ucie_kv on PATH-QC; coll_n/coll_ucie missing macro views;
  tt_ctlm ROM blackbox INSTANCE param + boot deadlock; qfd_tile_nl_a0c = structural FIX (GPL-0307 corridor).
- s81_head: head delta re-post pending (spine2/ft share); hd_ctl/hd_host/hd_mesh/hd_lep0N parent RTL absent; hd_serdes PATH-S81 H1.
- S81 types: leaves/c1x_C/kv_leaf/col_h*/serdes in TYPE-REDUCE folds; stations in S81-KITS waves (t23/31/43/44/49/52 IR delta); bk_sel/gunit/iqf/phy/svc_* need
  strict bound kit RTL (PATH-S81 X1, nested-reset blocker) -> not kittable from main now.
- S81 cores on the path (via c1x_C t8/t9, col_h10_r0_p1/p4): xfin, capc5r, xrt1, bf_col, bf_front_roots, qbank_S, rom_elem_q, sstn_base566, cfifo_crs4.
  bk_g/gunit_l0/l1/l2 = structural F5 hold (Codex physical early-tap); gunit_l0r = outline growth (plan); idx_tx_n32 = parent param mismatch (plan).
SELECTED (KITS-SPARE owns from now): S81 cores ot_s81sl_xrt3 (only in dsdv_slice_c3x_C__t1), dsdv_bksel_c, dsdv_bksel_q (bk_sel__t2), dsdv_gunit_l5 (l5_n32, F5/F3/F6 structural kit);
  QC coll_core, coll_s (KIT-PLACED, GEOM cond pin regs <=62/87 um; check plan3 does not touch them).
