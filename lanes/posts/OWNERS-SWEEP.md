- 2026-11-18 05:14 PST SWEEP 487 unsigned rows (S81 333+19 no-row, QC 102+4, KV 50, HEAD 2 running); lanes/OWNERS-SWEEP.tsv, script bin/owners_sweep.py.
  UNOWNED 112: S81 83 (other flow error 19, kit_rtl 16, hold after CTS 15, global_place 9), QC 26 (24 cancelled superseded cbf_q*, 2 kit input missing cbx_q10), KV 3 (kv3_hub_Eo, kv3_io_cor_v1, kv3_pc).
  DEAD-OWNER 1: S81 dsdv_slice_c1x_C__t9.
  FAILED no relaunch >1h: S81 234, KV 4 (CLAND kv3_pv_v*), QC 2 (sle_hc0, sle_sc_v3).
  STALE >3h: S81 219, QC 48, KV 13; 19 S81 + 4 QC plan types have no kit-wave row (not enumerable).
- 2026-11-18 05:50 PST 05:50 sweep, 471 rows. S81: UNOWNED 37 (was 83), FAILED-no-relaunch 241 (234), STALE 220 (219), DEAD-OWNER 45 NEW (col_h10/h9 owners). QC: UNOWNED 13 (26), STALE 50 (48), FAILED-no-relaunch 5. KV: UNOWNED 3 (3), FAILED 0 (4), STALE 11 (13), DEAD-OWNER 7 NEW (kv3_hg_v1p6, kv3_hg_v3, kv3_hgi). KV-TYPES-SWEEP has no row and no agent id: not an owner. NOMCAP-1118 owns 73 rows but alive is blank (not in the id list).
