PATH-QC-A0N59 2026-10-25 (base codex/root-1309@6c98ad9a6, plan sha256 441d1401...).
nl_affinity/: Codex NL F4-affinity successor (intel2 codex-qc-a0-1309/nl_affinity, frozen src 4ad811c012) post-CTS evidence.
  FF gate -39.75/577 (v10c -39.63/659): IN 264, XTAP 217, SAMETAP 96. 178/313 R2R = u_qlr1nw/ne landing q -> u_me.mq_wrom
  (QN->D direct, 11-78 um, median 25 um), launch ck_t15/t16 (194-200 ps) vs capture ck_t18/t15 (225-248 ps).
native59/: bound kit receipts (bind = Codex canonical-441 base_r8 copy; kit_rtl.json, kit_rsync.log).
tools/die_plan/kit_rsync.py: strip the wavefront reset cells (ot_dp_rsync_s2/_s3, ot_dp_rrelay, ot_dp_rgate) the 10-25
  binder now emits in bind_cells.sv (kit_cells.sv carries them) -> rtl_lint duplicate-module FAIL fixed.
