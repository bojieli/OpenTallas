# d44v_gqi_cp1109: the counter's HBM plan d44v_gqi + event corepins_1109

COUNT-ARCHIVE-2, 2026-11-09, per COORD 08:55 ruling (4) and the overlay rule in `../d44v_corepins_1109/README.md` ("For a counter on d44v_gqi, overlay the two cores/ tables and the 24 pins_file fields").

`die_plan.json.gz` is d44v_gqi (main) with 24 `hard_cores[].pins_file` fields changed: ot_wbq_root_g1 x16 -> `cores/ot_wbq_root_g1__216x129.6__vC5.json`, ot_svgr_own x8 -> `cores/ot_svgr_own__129.6x432__RF4T.json`. The top-level `note` is extended. No other leaf differs. Every changed field equals the same field in d44v_corepins_1109.

`cores/` holds the two new tables (byte copies of d44v_corepins_1109/cores) plus d44v_gqi's own gqi8 table. Other tables resolve through hbm/cores, as they do for d44v_gqi.

Why not d44v_corepins_1109 itself: that plan is the full HBM final (d44v_final4_1109 base). A counter on it drops 9 designs that are counted on d44v_gqi (hnx_rp3h_gn/gs/lc/tl are not in that plan; su_pg_lane_exp_x_core, su_static_qcore_r13, coll_inj_idx_join_rg, sfu_opsa_rest and svgr_bk have new outlines or pins). Counted stays counted until replaced, so the full final waits until those designs are re-signed on it.
