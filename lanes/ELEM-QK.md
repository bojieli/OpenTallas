# ELEM-QK (lane file) — Qwen compute (P6, main) + KV v3.8s partition types / hard cores without a signed view
Branch claude/elem-qk-1024 (localhost wt /srv/opentallas-scratch/claude/wt/elem-qk, base main 4b7b2b3e64). Run root localhost:/srv/opentallas-scratch/claude/elem-qk.
Sign-off: setup SS / hold FF, 833 ps, 60/25, related-pair CPPR skew <= 80 (spread info), new kit gates (sdc_lint, face_guard).

## 10-21 list (obsolete per owner 07:41; mapping kept for the record, no job started from it)
qfd_c_b16_dv -> dissolved into QC cbf/cbn/cbx quads (A0 hard cores + qfd_c_xstn_safe + pstn; QC-A0) | qfd_native59_dv_service -> superseded by
qfd_native59_dv_headprep_obs1 (QC type native59) | qkd_kvs_grp -> qkd_kvs_grp_r2c/_h_p in kv3_pc* (KV-G3) | qkd_pv_fin_s -> kv3_hub_C pvfin
(KV-G3) | qkd_d2d_static -> qkd_d2d_static_sfm in kv3_sys_c | qkd_host_root_admission -> obsx in kv3_hub_Wi, 22 hard cores (KV-G3/KVG3-WI).
FYI: all old closure_loop records of these leaves were TT-only with SS sensitivity -94..-331 ps (none is SS-clean).

## G0C inventory (main 4b7b2b3e64, check.py --completeness)
QC 52/56 clean (fail: sle/slw st_a/st_b ft_budget = QC-A0). KV 48/49 (kv3_hub_Wi 22 cores no pins; fixed on kv-g3 v3.8u, unmerged).

## PROPOSED ELEM-QK list (owners: object in your lane file or HANDOFF; silence by 08:45 = agreed)
QC (G3 kits from bound_r8 via bind.py kit-rtl on the P6 main plan; a P6 bind is needed where P5 buses differ):
  tt_ctlm, native59, glue, coll_s, coll_ft, coll_core, coll_ftm, coll_ftn, coll_n, coll_ucie,
  slice types without hard cores except st_a/st_b: slw/sle hc0-3, fw_v*, fe_v*, stm, sc, sle_ctl
  later: su_l0/su_l1/su_c SU hard cores + types (if QC-A0 does not run them)
  NOT mine: A0 cores + cbf/cbn/cbx quads, st_a/st_b ft_budget, coll_ftc (QC-A0); phy_serdes/_b, phy_ucie_kv = hard PHY macros.
KV (kit-rtl from kv41 bind, plan v3.8s): kv3_sys_c, kv3_sys_SD, kv3_sys_SD_v1, kv3_io_cor, kv3_io_cor_v1, kv3_io_ft, kv3_io_ft_v1, kv3_hroot
  NOT mine: hub_*, hg*, hgi*, pc*, pv*, phy* + 16 core kits (KV-G3 / KVG3-CORES / KVG3-WI).

## Status
- 08:20 PDT inventory done; kit-rtl works on main QC plan + asbuilt_tie + bound_r8 (tt_ctlm clean; native59/glue 1 unbound fault lane flt_o (P6-only); coll_s 2 narrow; slice types have P5/P6 bus diffs).
## Run dirs
## Results
## OWNER?

## ELEMQK-BIND (sub-lane: QC P6 rebind -> bound_p6)
- 08:02 PDT started: asbuilt_p6.json (= asbuilt_tie + map u_tap->sl_*_ctl, io_ucie/u_shared/g_six_five->coll_ucie, r8 = main table incl. treq, no land_r8_extra); elab running localhost pid 1116324 (yosys 0.68 native), out /srv/opentallas-scratch/claude/elem-qk/qcbind_p6

## ELEMQK-KV (fork of ELEM-QK): KV io/sys/hroot G3 kits
- 08:50 PDT kit-rtl (kv41 bind, plan v3.8s copy in src tree localhost:/srv/opentallas-scratch/claude/elem-qk/kv/src = KV-G3 e33504a6f src + main qwen_kvsys; asbuilt_elemqk.json = asbuilt_v36e with local paths):
  all 8 OK; narrow 0 / unbound 0; bound_only: io_cor ft8_i/o, sys_c ft0_i/o + io_pad_por_n + clk_clk_fwd (v3.7s dropped slots), hroot clk_clk_hbm.
  Hard macros (no placement in plan): sys_c UCIe x64 PHY + 2 d2d SRAM 64x137 + 2 SRAM 64x512; hroot SRAM 128x256 + 64x512. sys_SD/io_* none.
  G3 kits (gen.py phys, sdc_lint 0 err, patched face_guard): localhost:/srv/opentallas-scratch/claude/elem-qk/kv/g3 -> intel1/intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3
  ROUTE launched (ot-run 24G/8thr, local pids 1134185..1134224): sys_SD, sys_SD_v1, io_cor, io_cor_v1, io_ft, io_ft_v1. SYNTH-only (macro census): sys_c, hroot.

## SIGNOFF re-signoff list (2026-10-24 08:04 PDT, main 4ab1ec1399, results/signoff_1024/) — SUPERSEDED by the SIGNOFF list below (rec SS there was the TT slack)
Recipe: tools/die_plan/signoff.py (TT setup / FF hold with std boundary-hold overlay / TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna). Routed DBs of every closed block were on the wiped old fleet -> NEEDS RE-RUN; re-close from the kit and run `signoff.py run --run-dir <run> --out <dir>` before calling it closed.

### qwen_compute: 21 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 21
- last record already FAILS the standard (re-close, not just re-STA): qfd_dv_lane_h_safe2 (recorded TT pin-flop spread 82.4 ps > 80); qfd_dv_s8_station_tail1 (recorded TT pin-flop spread 84.0 ps > 80, recorded FF pin-flop spread 80.2 ps > 80)
- NO kit in repo (8): ot_qfd_xs_leaf, qfd_dv_s5_lrly, qfd_dv_s8x_btab, qfd_dv_s8x_prog, qfd_dv_s8x_vmr, qfd_dv_slice_tload, qfd_tile_nk_romleaf_rpf, qfd_tile_nl_romleaf_rpf
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): ot_hdc_sfu_exp_t x96 (47.82/21.69, 5.1/4.5); ot_hdc_sfu_rcp_t x96 (74.83/18.55, 10.8/10.1); ot_hdc_sfu_rsq_t x96 (55.5/22.16, 1.8/2.1); ot_qfd_xs_leaf x192 (62.32/23.38, 15.4/15.1); qfd_dv_lane_h_safe2 x96 (10.97/6.5, 82.4/77.0); qfd_dv_redstn2_region x48 (74.64/18.08, 60.4/58.7); qfd_dv_s5_ctl_repair4_leaf x12 (16.56/1.18, 70.8/62.3); qfd_dv_s5_lrly x96 (298.94/20.52, 34.5/33.4); qfd_dv_s5_su8_rst3 x12 (121.91/7.42, 33.4/31.8); qfd_dv_s5_xhead3 x24 (29.92/18.15, 63.7/61.5); qfd_dv_s8_crh_rp1 x12 (166.12/19.36, 30.3/29.7); qfd_dv_s8_station_tail1 x48 (62.87/16.31, 84.0/80.2); qfd_dv_s8x_btab x12 (263.37/1.41, 42.7/42.8); qfd_dv_s8x_crh x12 (132.79/3.53, 54.4/51.7); qfd_dv_s8x_prog x12 (219.75/8.19, 35.0/33.4); qfd_dv_s8x_vmr x36 (202.15/13.1, 69.0/65.3); qfd_dv_slice_tload x12 (19.14/14.46, 38.5/38.4); qfd_dv_stream_tile x12 (18.64/16.99, 57.1/55.5); qfd_tile_nk_romleaf_rpf x720 (None/None, None/None); qfd_tile_nl_romleaf_rpf x48 (None/None, None/None); qfd_ucie_six_five x1 (27.85/20.9, 31.6/31.5)

### qwen_kvsys: 20 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 20
- last record already FAILS the standard (re-close, not just re-STA): qkd_kvs_ctl (recorded TT pin-flop spread 121.8 ps > 80, recorded FF pin-flop spread 109.3 ps > 80); qkd_kvs_emb (recorded TT pin-flop spread 149.9 ps > 80)
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): ot_qkh_head_score4_native x128 (316.98/25.72, 2.8/2.2); ot_qkh_head_stin_native x2048 (342.95/20.38, 10.0/10.4); ot_qkh_head_stk_native x2048 (340.98/28.23, 1.9/1.8); ot_qkh_ktree_lk x128 (198.95/23.07, 17.5/17.4); ot_qwen_tp8_pv_join_t x64 (80.23/23.23, 50.2/49.8); ot_qwen_tp8_pv_slice_t x512 (46.74/16.06, 31.9/31.5); qkd_astk_fault_join x9 (431.16/27.12, 0.0/0.0); qkd_ctrl_kc x4 (92.08/25.46, 3.2/3.3); qkd_embgw x1 (29.09/6.37, 42.3/40.0); qkd_hp_or2 x87 (379.81/66.33, 0.0/0.0); qkd_kvs_ctl x1 (24.38/8.88, 121.8/109.3); qkd_kvs_emb x1 (27.3/13.35, 149.9/66.7); qkd_kvs_hroot x4 (40.47/16.77, 42.5/42.0); qkd_pv_rs_hd_f x2 (326.13/21.55, 35.5/34.2); qkd_rlyi_258s x128 (334.8/27.45, 5.6/5.7); qkd_seq_core_static_s x1 (189.52/21.81, 16.9/17.6); qkd_seq_fan_s x4 (326.77/18.06, 14.4/14.2); qkd_seq_xs_s x4 (155.4/19.39, 16.1/15.9); qkh_head_gather_stage x64 (354.91/11.02, 42.9/42.4); qkh_head_sstage x64 (317.75/11.84, 0.6/0.6)
- surviving routed runs signed: kv3_io_ft_v1 NOT SIGNED (SS -346.22, FF std -3.08 (raw +8.56), TT -55.95, slew viol 1547 TT), kv3_io_cor_v1 NOT SIGNED (SS -417.24, FF std -10.52, TT -132.68, slew viol 4030 TT)

## [SUPERSEDED: SS-based, owner 10-24 rule is TT setup / FF hold] SIGNOFF re-signoff list v2 (2026-10-24 08:06 PDT, main 0f5176689d, results/signoff_1024/README.md + per_die.md)
Recipe tools/die_plan/signoff.py: SS setup, FF hold (std overlay: out min 0 / in min -40), TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna. Every closed block's routed DB was on the wiped old fleet -> NEEDS RE-RUN. NOTE: closure_loop verdicts were accepted at TT setup; 'rec SS' below is the SS-library slack (metrics.ss_sensitivity_ps). Paper FAIL = re-close needed (not just re-STA). After re-close: `signoff.py run --run-dir <ORFS run> --out <dir>` must say SIGNED.

### qwen_compute: 21 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 21 (paper FAIL 16, paper PASS 3)
- ot_hdc_sfu_exp_t x96: NEEDS RE-RUN | rec SS -309.97 (TT 47.82) FF 21.69 spread TT/FF 5.1/4.5 | kit repo | paper FAIL
- ot_hdc_sfu_rcp_t x96: NEEDS RE-RUN | rec SS -277.47 (TT 74.83) FF 18.55 spread TT/FF 10.8/10.1 | kit repo | paper FAIL
- ot_hdc_sfu_rsq_t x96: NEEDS RE-RUN | rec SS -309.07 (TT 55.5) FF 22.16 spread TT/FF 1.8/2.1 | kit repo | paper FAIL
- ot_qfd_xs_leaf x192: NEEDS RE-RUN | rec SS -288.6 (TT 62.32) FF 23.38 spread TT/FF 15.4/15.1 | kit NOT IN REPO | paper FAIL
- qfd_dv_lane_h_safe2 x96: NEEDS RE-RUN | rec SS -362.04 (TT 10.97) FF 6.5 spread TT/FF 82.4/77 | kit repo | paper FAIL
- qfd_dv_redstn2_region x48: NEEDS RE-RUN | rec SS -221.45 (TT 74.64) FF 18.08 spread TT/FF 60.4/58.7 | kit repo | paper FAIL
- qfd_dv_s5_ctl_repair4_leaf x12: NEEDS RE-RUN | rec SS -265.74 (TT 16.56) FF 1.18 spread TT/FF 70.8/62.3 | kit repo | paper FAIL
- qfd_dv_s5_lrly x96: NEEDS RE-RUN | rec SS 178.48 (TT 298.94) FF 20.52 spread TT/FF 34.5/33.4 | kit NOT IN REPO | paper PASS
- qfd_dv_s5_su8_rst3 x12: NEEDS RE-RUN | rec SS -205.86 (TT 121.91) FF 7.42 spread TT/FF 33.4/31.8 | kit repo | paper FAIL
- qfd_dv_s5_xhead3 x24: NEEDS RE-RUN | rec SS -278.04 (TT 29.92) FF 18.15 spread TT/FF 63.7/61.5 | kit repo | paper FAIL
- qfd_dv_s8_crh_rp1 x12: NEEDS RE-RUN | rec SS -17.91 (TT 166.12) FF 19.36 spread TT/FF 30.3/29.7 | kit repo | paper FAIL
- qfd_dv_s8_station_tail1 x48: NEEDS RE-RUN | rec SS -263.4 (TT 62.87) FF 16.31 spread TT/FF 84/80.2 | kit repo | paper FAIL
- qfd_dv_s8x_btab x12: NEEDS RE-RUN | rec SS -6.34 (TT 263.37) FF 1.41 spread TT/FF 42.7/42.8 | kit NOT IN REPO | paper FAIL
- qfd_dv_s8x_crh x12: NEEDS RE-RUN | rec SS -64.37 (TT 132.79) FF 3.53 spread TT/FF 54.4/51.7 | kit repo | paper FAIL
- qfd_dv_s8x_prog x12: NEEDS RE-RUN | rec SS 50.3 (TT 219.75) FF 8.19 spread TT/FF 35/33.4 | kit NOT IN REPO | paper PASS
- qfd_dv_s8x_vmr x36: NEEDS RE-RUN | rec SS 43.88 (TT 202.15) FF 13.1 spread TT/FF 69/65.3 | kit NOT IN REPO | paper PASS
- qfd_dv_slice_tload x12: NEEDS RE-RUN | rec SS -230.95 (TT 19.14) FF 14.46 spread TT/FF 38.5/38.4 | kit NOT IN REPO | paper FAIL
- qfd_dv_stream_tile x12: NEEDS RE-RUN | rec SS -276.71 (TT 18.64) FF 16.99 spread TT/FF 57.1/55.5 | kit repo | paper FAIL
- qfd_tile_nk_romleaf_rpf x720: NEEDS RE-RUN | rec SS - (TT -) FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD
- qfd_tile_nl_romleaf_rpf x48: NEEDS RE-RUN | rec SS - (TT -) FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD
- qfd_ucie_six_five x1: NEEDS RE-RUN | rec SS -176.98 (TT 27.85) FF 20.9 spread TT/FF 31.6/31.5 | kit repo | paper FAIL

### qwen_kvsys: 20 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 20 (paper FAIL 9, paper PASS 11)
- ot_qkh_head_score4_native x128: NEEDS RE-RUN | rec SS 211.89 (TT 316.98) FF 25.72 spread TT/FF 2.8/2.2 | kit repo | paper PASS
- ot_qkh_head_stin_native x2048: NEEDS RE-RUN | rec SS 253.02 (TT 342.95) FF 20.38 spread TT/FF 10/10.4 | kit repo | paper PASS
- ot_qkh_head_stk_native x2048: NEEDS RE-RUN | rec SS 250.52 (TT 340.98) FF 28.23 spread TT/FF 1.9/1.8 | kit repo | paper PASS
- ot_qkh_ktree_lk x128: NEEDS RE-RUN | rec SS -88.42 (TT 198.95) FF 23.07 spread TT/FF 17.5/17.4 | kit repo | paper FAIL
- ot_qwen_tp8_pv_join_t x64: NEEDS RE-RUN | rec SS -271.12 (TT 80.23) FF 23.23 spread TT/FF 50.2/49.8 | kit repo | paper FAIL
- ot_qwen_tp8_pv_slice_t x512: NEEDS RE-RUN | rec SS -273.24 (TT 46.74) FF 16.06 spread TT/FF 31.9/31.5 | kit repo | paper FAIL
- qkd_astk_fault_join x9: NEEDS RE-RUN | rec SS 392.5 (TT 431.16) FF 27.12 spread TT/FF 0/0 | kit repo | paper PASS
- qkd_ctrl_kc x4: NEEDS RE-RUN | rec SS 19.05 (TT 92.08) FF 25.46 spread TT/FF 3.2/3.3 | kit repo | paper PASS
- qkd_embgw x1: NEEDS RE-RUN | rec SS -353.25 (TT 29.09) FF 6.37 spread TT/FF 42.3/40 | kit repo | paper FAIL
- qkd_hp_or2 x87: NEEDS RE-RUN | rec SS 307.59 (TT 379.81) FF 66.33 spread TT/FF 0/0 | kit repo | paper PASS
- qkd_kvs_ctl x1: NEEDS RE-RUN | rec SS -295.24 (TT 24.38) FF 8.88 spread TT/FF 121.8/109.3 | kit repo | paper FAIL
- qkd_kvs_emb x1: NEEDS RE-RUN | rec SS -369.4 (TT 27.3) FF 13.35 spread TT/FF 149.9/66.7 | kit repo | paper FAIL
- qkd_kvs_hroot x4: NEEDS RE-RUN | rec SS -219.78 (TT 40.47) FF 16.77 spread TT/FF 42.5/42 | kit repo | paper FAIL
- qkd_pv_rs_hd_f x2: NEEDS RE-RUN | rec SS 228.38 (TT 326.13) FF 21.55 spread TT/FF 35.5/34.2 | kit repo | paper PASS
- qkd_rlyi_258s x128: NEEDS RE-RUN | rec SS 108.93 (TT 334.8) FF 27.45 spread TT/FF 5.6/5.7 | kit repo | paper PASS
- qkd_seq_core_static_s x1: NEEDS RE-RUN | rec SS -99.68 (TT 189.52) FF 21.81 spread TT/FF 16.9/17.6 | kit repo | paper FAIL
- qkd_seq_fan_s x4: NEEDS RE-RUN | rec SS 235.62 (TT 326.77) FF 18.06 spread TT/FF 14.4/14.2 | kit repo | paper PASS
- qkd_seq_xs_s x4: NEEDS RE-RUN | rec SS -103.57 (TT 155.4) FF 19.39 spread TT/FF 16.1/15.9 | kit repo | paper FAIL
- qkh_head_gather_stage x64: NEEDS RE-RUN | rec SS 269.98 (TT 354.91) FF 11.02 spread TT/FF 42.9/42.4 | kit repo | paper PASS
- qkh_head_sstage x64: NEEDS RE-RUN | rec SS 211.84 (TT 317.75) FF 11.84 spread TT/FF 0.6/0.6 | kit repo | paper PASS
- surviving routed runs signed (pathfinding): kv3_io_ft_v1 NOT SIGNED (SS -346.22, FF std -3.08 (raw +8.56), TT -55.95, 1547 slew viol TT), kv3_io_cor_v1 NOT SIGNED (SS -417.24, FF std -10.52, TT -132.68, 4030 slew viol TT)
- 09:20 PDT TOOL FIXES @409bafcab1 (claude/elem-qk-1024): bind.py keep cells (kit-local bind_cells.sv when the bind predates CP1-R10 keep: kv41 + QC bound_r8 kits otherwise fail face_guard on merged epoch/replica flops), kit-rtl `include headers (+ gen_phys VERILOG_INCLUDE_DIRS), face_guard checks planned pins only (bound-only clk_*/io_* ports listed as unplanned_ports).
  face_guard now: io_cor/io_cor_v1/io_ft/io_ft_v1 PASS, hroot PASS 4313/4313, sys_c PASS 4967/4967.
  sys_c macros (synth): UCIe x64 PHY + 4x d2d_sram 64x137 p288 -> overlay physical/die_plan/qwen_kvsys/elemqk/macro_overlay.json (plan COPY die_plan_elemqk.json, PROPOSED to KV-G3). hroot: 0 macros in synth (kit-rtl hard_macros over-reports unelaborated files).
  BLOCKED: kv3_sys_SD / kv3_sys_SD_v1: bound RTL = ot_qfd_serdes_112g_x6_phy (x12 SerDes half) model with no LEF/lib view -> NOT RUN until an x6-half PHY abstract exists (OWNER?/KV-G3).
  Old g3 kits (no keep cells, no review) routing on intel1 = PATHFINDING ONLY: io_cor_v1, io_ft, io_ft_v1 (intel1:/srv/opentallas-scratch2/claude/elem-qk/kvg3).
  Review runs (owner order 08:05): place goal on intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3b (io x4) and kvg3c (sys_c, hroot; plan copy with macro overlay).
- 08:10 PDT bind on P6 copy (r8 table regenerated from this bind: 248,396 pad flops, max pad 5; main table was STALE vs P6 bind: cb tile hops bound 8 vs 4, treq uncovered): proof unbound 4 / tied 0 / undriven 0, 2 errors = UNPLANNED plan gaps (coll_ucie->coll_core 3 b: io_ucie.tx_up, u_shared.rx_valid -> g_face[0]; coll_s->glue 1 b: g_face[4].fault_cause -> sys_face.obs_fault). verify running.

## 2026-10-24 08:20 PDT NEEDS RE-RUN wave (COORD: fleet idle, go wide)
- 33 QC+KV modules of results/signoff_1024 NEEDS RE-RUN that have a ref_tile kit (none claimed in other lane files):
  re-run at the SAME source commit as their CLOSED record (job.json route stage, no daemon) via
  tools/elem_qk/rerun_reftile.py (branch claude/elem-qk-1024 0df18c069d), then main's signoff.py --corners tt,ff.
  Hosts localhost/epyc2/epyc3 (ot-run, scratch only). List + hosts: /srv/opentallas-scratch/claude/elem-qk/rerun_hosts.txt.
- Author floorplan reviews (render of floorplan.json at the closed commit): 33x PASS-CONDITIONAL, records
  results/geom_review/<module>__<kit>__<hash>.json (reviewer ELEM-QK), contact sheets results/elem_qk_1024/review/batch_0*.png.
  GEOM-REVIEW: please second-review. Notes: qkd_kvs_ctl 475x475 0 macros (large); qkh_head_gather_stage aspect 15.
- No kit (not re-runnable here): ot_qfd_xs_leaf, qfd_dv_s5_lrly, s8x_btab/prog/vmr, slice_tload. romleaf_rpf = QC-A0.
- QC G3 tt_ctlm: as-built ROM instantiations carry #(.INSTANCE(..)) -> yosys/OpenSTA reject vs _bb macro; kit copy strips
  macro parameter overrides (tools/elem_qk/kit_strip_macro_params.py, logged per kit). Place re-running on intel2.

## SIGNOFF re-signoff list v3 — TT RULE (2026-10-24 08:22 PDT, main f942bf2f72; supersedes v1/v2 above)
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).

### qwen_compute: 21 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 21 (paper FAIL 2, PASS 17, no/incomplete record 2)
- ot_hdc_sfu_exp_t x96: NEEDS RE-RUN | rec TT 47.82 FF 21.69 spread TT/FF 5.1/4.5 | kit repo | paper PASS
- ot_hdc_sfu_rcp_t x96: NEEDS RE-RUN | rec TT 74.83 FF 18.55 spread TT/FF 10.8/10.1 | kit repo | paper PASS
- ot_hdc_sfu_rsq_t x96: NEEDS RE-RUN | rec TT 55.5 FF 22.16 spread TT/FF 1.8/2.1 | kit repo | paper PASS
- ot_qfd_xs_leaf x192: NEEDS RE-RUN | rec TT 62.32 FF 23.38 spread TT/FF 15.4/15.1 | kit NOT IN REPO | paper PASS
- qfd_dv_lane_h_safe2 x96: NEEDS RE-RUN | rec TT 10.97 FF 6.5 spread TT/FF 82.4/77 | kit repo | paper FAIL (recorded TT pin-flop spread 82.4 ps > 80)
- qfd_dv_redstn2_region x48: NEEDS RE-RUN | rec TT 74.64 FF 18.08 spread TT/FF 60.4/58.7 | kit repo | paper PASS
- qfd_dv_s5_ctl_repair4_leaf x12: NEEDS RE-RUN | rec TT 16.56 FF 1.18 spread TT/FF 70.8/62.3 | kit repo | paper PASS
- qfd_dv_s5_lrly x96: NEEDS RE-RUN | rec TT 298.94 FF 20.52 spread TT/FF 34.5/33.4 | kit NOT IN REPO | paper PASS
- qfd_dv_s5_su8_rst3 x12: NEEDS RE-RUN | rec TT 121.91 FF 7.42 spread TT/FF 33.4/31.8 | kit repo | paper PASS
- qfd_dv_s5_xhead3 x24: NEEDS RE-RUN | rec TT 29.92 FF 18.15 spread TT/FF 63.7/61.5 | kit repo | paper PASS
- qfd_dv_s8_crh_rp1 x12: NEEDS RE-RUN | rec TT 166.12 FF 19.36 spread TT/FF 30.3/29.7 | kit repo | paper PASS
- qfd_dv_s8_station_tail1 x48: NEEDS RE-RUN | rec TT 62.87 FF 16.31 spread TT/FF 84/80.2 | kit repo | paper FAIL (recorded TT pin-flop spread 84.0 ps > 80; recorded FF pin-flop spread 80.2 ps > 80)
- qfd_dv_s8x_btab x12: NEEDS RE-RUN | rec TT 263.37 FF 1.41 spread TT/FF 42.7/42.8 | kit NOT IN REPO | paper PASS
- qfd_dv_s8x_crh x12: NEEDS RE-RUN | rec TT 132.79 FF 3.53 spread TT/FF 54.4/51.7 | kit repo | paper PASS
- qfd_dv_s8x_prog x12: NEEDS RE-RUN | rec TT 219.75 FF 8.19 spread TT/FF 35/33.4 | kit NOT IN REPO | paper PASS
- qfd_dv_s8x_vmr x36: NEEDS RE-RUN | rec TT 202.15 FF 13.1 spread TT/FF 69/65.3 | kit NOT IN REPO | paper PASS
- qfd_dv_slice_tload x12: NEEDS RE-RUN | rec TT 19.14 FF 14.46 spread TT/FF 38.5/38.4 | kit NOT IN REPO | paper PASS
- qfd_dv_stream_tile x12: NEEDS RE-RUN | rec TT 18.64 FF 16.99 spread TT/FF 57.1/55.5 | kit repo | paper PASS
- qfd_tile_nk_romleaf_rpf x720: NEEDS RE-RUN | rec TT - FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD (no closed record in the repo)
- qfd_tile_nl_romleaf_rpf x48: NEEDS RE-RUN | rec TT - FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD (no closed record in the repo)
- qfd_ucie_six_five x1: NEEDS RE-RUN | rec TT 27.85 FF 20.9 spread TT/FF 31.6/31.5 | kit repo | paper PASS

### qwen_kvsys: 20 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 20 (paper FAIL 2, PASS 18, no/incomplete record 0)
- ot_qkh_head_score4_native x128: NEEDS RE-RUN | rec TT 316.98 FF 25.72 spread TT/FF 2.8/2.2 | kit repo | paper PASS
- ot_qkh_head_stin_native x2048: NEEDS RE-RUN | rec TT 342.95 FF 20.38 spread TT/FF 10/10.4 | kit repo | paper PASS
- ot_qkh_head_stk_native x2048: NEEDS RE-RUN | rec TT 340.98 FF 28.23 spread TT/FF 1.9/1.8 | kit repo | paper PASS
- ot_qkh_ktree_lk x128: NEEDS RE-RUN | rec TT 198.95 FF 23.07 spread TT/FF 17.5/17.4 | kit repo | paper PASS
- ot_qwen_tp8_pv_join_t x64: NEEDS RE-RUN | rec TT 80.23 FF 23.23 spread TT/FF 50.2/49.8 | kit repo | paper PASS
- ot_qwen_tp8_pv_slice_t x512: NEEDS RE-RUN | rec TT 46.74 FF 16.06 spread TT/FF 31.9/31.5 | kit repo | paper PASS
- qkd_astk_fault_join x9: NEEDS RE-RUN | rec TT 431.16 FF 27.12 spread TT/FF 0/0 | kit repo | paper PASS
- qkd_ctrl_kc x4: NEEDS RE-RUN | rec TT 92.08 FF 25.46 spread TT/FF 3.2/3.3 | kit repo | paper PASS
- qkd_embgw x1: NEEDS RE-RUN | rec TT 29.09 FF 6.37 spread TT/FF 42.3/40 | kit repo | paper PASS
- qkd_hp_or2 x87: NEEDS RE-RUN | rec TT 379.81 FF 66.33 spread TT/FF 0/0 | kit repo | paper PASS
- qkd_kvs_ctl x1: NEEDS RE-RUN | rec TT 24.38 FF 8.88 spread TT/FF 121.8/109.3 | kit repo | paper FAIL (recorded TT pin-flop spread 121.8 ps > 80; recorded FF pin-flop spread 109.3 ps > 80)
- qkd_kvs_emb x1: NEEDS RE-RUN | rec TT 27.3 FF 13.35 spread TT/FF 149.9/66.7 | kit repo | paper FAIL (recorded TT pin-flop spread 149.9 ps > 80)
- qkd_kvs_hroot x4: NEEDS RE-RUN | rec TT 40.47 FF 16.77 spread TT/FF 42.5/42 | kit repo | paper PASS
- qkd_pv_rs_hd_f x2: NEEDS RE-RUN | rec TT 326.13 FF 21.55 spread TT/FF 35.5/34.2 | kit repo | paper PASS
- qkd_rlyi_258s x128: NEEDS RE-RUN | rec TT 334.8 FF 27.45 spread TT/FF 5.6/5.7 | kit repo | paper PASS
- qkd_seq_core_static_s x1: NEEDS RE-RUN | rec TT 189.52 FF 21.81 spread TT/FF 16.9/17.6 | kit repo | paper PASS
- qkd_seq_fan_s x4: NEEDS RE-RUN | rec TT 326.77 FF 18.06 spread TT/FF 14.4/14.2 | kit repo | paper PASS
- qkd_seq_xs_s x4: NEEDS RE-RUN | rec TT 155.4 FF 19.39 spread TT/FF 16.1/15.9 | kit repo | paper PASS
- qkh_head_gather_stage x64: NEEDS RE-RUN | rec TT 354.91 FF 11.02 spread TT/FF 42.9/42.4 | kit repo | paper PASS
- qkh_head_sstage x64: NEEDS RE-RUN | rec TT 317.75 FF 11.84 spread TT/FF 0.6/0.6 | kit repo | paper PASS
- surviving routed runs (TT rule): kv3_io_ft_v1 NOT SIGNED (TT -55.95/36 ep, FF std -3.08 (raw +8.56), 1547 slew viol TT), kv3_io_cor_v1 NOT SIGNED (TT -132.68, FF std -10.52, 4030 slew viol TT)
- 2026-10-24 08:23 PDT first re-run qkd_hp_or2: NOT SIGNED (sdc_lint ref_tile SDC form; face_guard unregistered 2); TT +441.7 / FF +25.6 /
  DRC 0. OWNER?/SIGNOFF asked (lanes/SIGNOFF.md) whether ref_tile re-runs can sign or need die-plan re-kit.
- tt_ctlm G3 place: face_guard FAIL (dropped 80, shared 91, feedthrough 61) = P5 bound_r8 vs P6 plan; waits for bound_p6.
- 08:35 PDT reviews PASS (results/geom_review/kv_g3_kv3_io_ft*__elemqk__*.json): io_ft, io_ft_v1 -> FINISH launched intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3b (ot-run 24G/8). sys_c PHY moved to y 250.56 (core margin), place relaunched kvg3d.
- 08:55 PDT main merge (CP1-R10 face_keep hooks + odb face_guard) -> ALL KV kits regenerated: intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3e (face_guard planned-pins fix re-applied @499a830ac1). Stale-tool runs stopped (my containers only): g3b io_ft/io_ft_v1 finish, intel1 kvg3 pathfinding routes. FINISH running kvg3e io_ft, io_ft_v1 (geometry = reviewed kvg3b, io.tcl identical). PLACE for review: sys_c (kvg3e), io_cor/io_cor_v1 (kvg3b), hroot (kvg3c).
- 2026-10-24 08:28 PDT native59 G3 synth: face_guard FAIL (dropped 34, shared 133, ft 1) - same cause as tt_ctlm (bound_r8 P5 vs P6 plan);
  both QC G3 kits wait for bound_p6 (ELEMQK-BIND), will be regenerated on main >= 0ce45ab03c (face_keep) before any P&R.
- Re-runs: rerun_reftile fixed (pathspec, kit dir) and regenerated with main d3e08231d2 signoff tools; first attempts of
  9 kits failed on harness bugs / missing ~/.local PDK (now present) -> relaunched. Re-runs at closed commit lack the
  face_keep fix: verdict relies on signoff.py face_guard (COORD 0ce45ab03c note).

## CODEX notes
- Existing 33 ref_tile re-runs plus KV kit wave must be collected; first hp_or2 timing +441.7/+25.6 ps DRC0 but NOT SIGNED because sdc_lint/face_guard contract fails. QC tt_ctlm/native59 face_guard fails from P5-bound vs P6-plan mismatch; blocked on bound_p6. Next collect rebind and new face_keep kit results; no false closure.

- CODEX collected 9 completed ref_tile signoffs, all NOT SIGNED. TT setup / FF hold ps: qfd_dv_s5_crh +379.52/+4.17; qfd_dv_s8_crh_rp1 +406.54/+4.52; qkd_ctrl_kc -1.13/NOT RUN (FF rc137); qkh_native_stin_1014 +311.75/-6.83; qkd_astk_fault_join +435.67/+18.55; qkd_pv_rs_hd_f +329.34/-7.65; qkh_head_sstage +308.35/-15.45; qkh_r4_score4_1014 +314.57/-4.01; qkd_hp_or2 FF/TT unconstrained sentinel 1e42 (combinational/no clock, not a timing PASS). Shared signoff clock insertion has unit bug (spreads ~1e14 ps); root coordinator notified and owns fix. Real hold failures require hold ECO/re-kit, source old closed views not enough. Ref_tile generic SDC cannot pass die-plan sdc_lint (dynamic Tcl and 833.333 period vs833); face_guard detects dropped/comb/shared ports. No signoff credit claimed.
- bound_p6 bind FAIL: 2 unplanned crossing groups (coll_s->glue 1 bit, coll_ucie->coll_core 3 bits), verify 2,723,870 matched / 0 mismatched, glue_unmatched14, asbuilt_errors2. This is the concrete next blocker for tt_ctlm/native59; plan missing fault/status routes must be added, no tie-offs.

- CODEX took over missing P6 crossings on codex/elem-qk-1024. Fault/status capacity adds4bits,0cycles: S fault-vector35->36,forwarded69->70,UCIe fault/status1->4. Generated G0PASS0errors88warn,G0C52/56; rebind live localhost scratch/claude/codex-qwen/qcp6_status_bind via ot-run (existing asbuilt JSON reused,no new elaboration).

## RESUMED 2026-10-24 12:11 PDT (after 08:50-12:04 usage limit; RESUME-1208.md)
- Adopted: Codex qcp6_status_bind_v5 (localhost /srv/opentallas-scratch/claude/codex-qwen/qcp6_status_bind_v5: bind 0 errors,
  split verify PASS 2,723,870/2,723,884 matched, 14 declared glue) on main plan 90907cf3b1 = the P6 bound for QC G3 kits.
  codex/elem-qk-1024 @a8a31539a8 (ASTK replica candidate, P6 edits mostly on main): not whole-merged; isolate as needed.
  Live Codex job in this family: intel1 astk_WN_r4 (KV core, KVG3-CORES/Codex) - not mine to relaunch; will collect.
- 33 ref_tile re-runs all finished; re-signing all with main 24b2da3433 signoff.py (unit fix 824d91d37e, ft1 pairs) -> collect.
- Next: QC tt_ctlm/native59 (+glue/coll) G3 kits regenerated on main from bound v5 (face_keep), review, route.
- 2026-10-24 12:24 PDT QC G3 on bound v5 (main plan + elemqk macro overlay, kits regenerated on main incl. face_keep): tt_ctlm SDC_LINT
  PASS, FACE_GUARD PASS 3117/3117; place failed MPL-0020 (OpenDB escapes generate brackets) -> gen_phys fix
  (macro names escaped), re-running place epyc3. native59 FACE_GUARD FAIL shared 2 = plan duplicate fault lane
  (fltn vs native59__fault_native_fault), plan fix asked in lanes/QC-A0.md (OWNER?). native59 held from route.

## ELEMQK-KV
- 13:1x PDT RESUMED (ELEMQK-KV fork). Adopted: none (no Codex job in my KV types). Merged origin/main into claude/elem-qk-1024 (88f5349870; main face_guard taken, my planned-pins-only check gone).
  Regenerated kits g3g from plan copy die_plan_elemqk.json (macro overlay) with fresh kit-rtl; bound-only pins resolved in kit wrapper (kit-local edit, recorded in RTL header):
  hroot clk_clk_hbm<-clk; sys_c io_pad_por_n<-arst_n, clk_clk_fwd<-clk, ft0 (dropped v3.7s slot) tied 0/open; io_cor ft8 tied 0/open.
  Root cause of old sys_c face_guard_odb dropped 23: kit had pre-30fe617bcb face_keep.tcl regexp (^u_bin_..) that missed nested u_bound.u_bin_* (dont_touch 0 cells). g3g has main's face_keep.
  Place launched intel1/intel2 kvg3g (all 6). sys_SD / sys_SD_v1: NOT RUN (no LEF/lib for ot_qfd_serdes_112g_x6_phy).
- 2026-10-24 12:30 PDT ASTK/ECTLK variants launched (ot-run): ASTK x4 cores x {hm55: canonical + impl hold margin 55 (FF hold ~35 ps faster
  than TT-repaired hold), r4h: Codex read-control replica RTL d3c7327ff3 + hm55 (TT fails = zq read-mux fanout, WN
  zq[2]->oa[108] -80.6), r4hs: r4h + setup margin 20, density 0.72, timing-driven GPL}. ECTLK (ck pin at E corner of
  881x216; CTS diag 694-747 ps insertion incl. 255 ps pre-CTS wire buffers + macro-latency balancing chains) from the
  ectlk_m7 placement: e1 -no_insertion_delay (no delay-buffer derate), e2 e1+buffer distance 120/branch 60/clusters 20x50,
  e3 e1+BUFx24 root/tree+balance_levels. All finish with main signoff.py tt,ff (kits' SDC unchanged).
- 2026-10-24 13:21 PDT HOLD (fork ELEMQK-HOLD): 21 warm FF-hold ECO runs (head e1..e7 x a/b/c, old 285.12 routes) launched localhost/epyc3. First: e5/a (FF-only m0, 381 hold bufs): TT +14.33 / FF hold -1.15 (22 ep, was -7.89) NOT SIGNED; also drv slew FAIL, clock insertion 357 vs 250+-40 FAIL, face_guard FAIL (old kit). => hold is fixable by ECO, but the old 285.12 views cannot sign (insertion/face) - recipe calibration for the 216x216 re-kits.
- 2026-10-24 13:26 PDT tt_ctlm v5 placed (review PASS-COND, results/geom_review/tt_ctlm__g3qc3_v5__place.json: 37 ff-ff hops > 675 um risk); ROUTE launched epyc3 (run_kit route -> finish/abstract/signoff). Forks: ELEMQK-HOLD (7 heads x 3 hold variants), ELEMQK-ASTK (ASTK + ECTLK variants), ELEMQK-KV resumed.
- 14:2x ELEMQK-KV g3g place reviews recorded (results/geom_review/kv_g3_*__elemqk__*): io_ft/io_ft_v1/io_cor PASS, io_cor_v1 PASS-COND (663 hops 675..690 um), hroot PASS-COND (u_rly relay not midway: 286 hops >750, max 831), sys_c FAIL (d2d SRAMs far from d2d_kv cluster, max 905 um) -> overlay SRAMs moved to x 950..1210, g3h re-place intel2.
  Routes running intel1/intel2 kvg3g: io_ft, io_cor, io_cor_v1, hroot.
  io_ft_v1 g3g ROUTED: NOT SIGNED: TT setup -85.44 (1054 ep, 635 um hops with ~250 um unbuffered segments, RCX slew to 688 ps), FF hold +10.27, spread 34.7/30.3, DRC 0, GRT ovf 0, pin_audit PASS 2100/2100, face_guard PASS. run_kit 6_report OOMs at 24 GB (peak 25.1) -> skips signoff: use >= 32 GB for ft kits.
  Trying kit-local PRE_RESIZE repair_design -max_wire_length 120 (kvg3g_wl/kv3_io_ft_v1). If it closes, propose to gen_phys owners as a kit default for long ft hops.
- 2026-10-24 18:49 PDT RESUMED after 2nd limit. Forks HOLD + KV resumed. OWNER 18:4x: QC capacity plan accepted -> QC G3 kits (tt_ctlm/native59/glue/coll*) must be rebound on it once QC-A0 lands it (current v5 bind = P6 main plan; tt_ctlm v5 route in GRT iterations 19/30 epyc3 = congestion signal, pathfinding). codex/qc-capacity-1024 still has the duplicate fltn lane (native59 face_guard FAIL) - asked QC-A0 12:24, no answer yet. 20 re-runs re-signing with main 24b2da3433.
- 2026-10-24 18:50 PDT HOLD results (21/21 done, all NOT SIGNED; results/elem_qk_1024/hold): TT setup / FF hold ps per head, variant b
  (FF-only margin 3, best): e1 +14.30/-1.42 | e2 +27.10/+0.09 PASS | e3 +4.59/-0.16 | e4 +13.55/-0.95 | e5 +13.98/-1.61 |
  e6 +15.59/-1.40 | e7 +17.13/-0.56 (a margin0 -0.81..-3.85; c MCMM -1.19..-3.85). Every run also FAILS drv (TT slew),
  clock (insertion 320-363 vs 250+-40), face_guard (old kit) -> no head can sign from the 285.12 views; hold is ECO-fixable
  (recipe b, margin >= 3) and should be carried into the 216x216 re-kits.

## PARKED 2026-10-24 18:56 PDT  (branch tip after sub-agent parks: 2ece7f9a79)
- Branch claude/elem-qk-1024 @de0409474f (pushed; main merged in). NOT merged to main: tools/die_plan pytest shows
  failures in test_g2/test_relay_mid (+ test_bind needs OT_BIND_YOSYS=local yosys); not yet compared against main -> next
  agent: run the same suite on a main checkout, merge only if no new failures. Own changes: bind.py kit-rtl (keep cells,
  `include headers), gen_phys.py (include dirs, escaped macro names), tools/elem_qk/*, results/elem_qk_1024/*, geom_review.
- Live jobs (let finish, then collect):
  * epyc3:/srv/opentallas-scratch/claude/elem-qk/g3qc3/tt_ctlm  run_kit route (unit oth-ubuntu-440481-1792873606; was in
    GRT extra iterations 19/30 = congestion), log localhost .../elem-qk/logs/qc3_tt_ctlm_route.log, KIT/run_route.log;
    signoff runs inside run_kit (KIT/signoff/signoff.json). Pathfinding: bound v5 = P6 main plan, NOT the accepted
    capacity plan.
  * localhost:/srv/opentallas-scratch/claude/elem-qk/rerun/qkd_kvs_ctl  re-run route (log logs/rr_qkd_kvs_ctl.log), then
    resign: cd there; ot-run ... bash ../../resign.sh 24b2da3433; collect: tools/elem_qk/collect_rerun.py.
  * forks ELEMQK-ASTK (ASTK/ECTLK variants) and ELEMQK-KV (KV io/sys/hroot G3) told to park; their blocks follow below.
- Results: 32/33 signoff_1024 re-runs routed at closed commit + main signoff: ALL NOT SIGNED (results/elem_qk_1024/
  README.md, rerun_summary.json): sdc_lint 32 (ref_tile Tcl SDC form), face_guard 26, FF hold 13. -> need die-plan G3
  re-kit to sign. KV heads e1..e7 hold variants (21): none SIGNED; recipe b (FF-only margin 3) fixes hold to <=5 endpoints
  (e2 +0.09 / TT +27.10) but DRV slew, clock insertion 320-363 vs 250+-40, old-kit face_guard remain (re-kit by KVG3-CORES).
  QC tt_ctlm v5: SDC_LINT PASS, FACE_GUARD PASS 3117/3117, placed (review PASS-COND), route pending.
- Failures/blocks: native59 face_guard FAIL = duplicate plan fault lane fltn (asked QC-A0 12:24, still in capacity plan).
  21 re-runs killed 08:33 by fleet-wide docker stop (relaunched OK).
- Next: rebind QC G3 types on the accepted capacity plan once QC-A0 lands it (tt_ctlm, native59 after fltn fix, glue,
  coll_*; coll/glue have bound_only clocks clk_coll/clk_serdes/clk_d2d -> need SDC/plan clock decision).
- OWNER?: (1) ref_tile re-runs can never sign (SDC form + face registers): confirm re-kit as the only path (SIGNOFF lane).
  (2) native59 fltn duplicate lane: drop it (QC plan owner). (3) multi-clock coll/glue types: plan clock per bound_only clock.
- Cleaned epyc2 scratch2 codex-qwen obj trees (~106 GB freed, binaries kept).
- 2026-10-24 18:56 PDT PARK (fork ELEMQK-HOLD): branch claude/elem-qk-1024 @de0409474f (hold work in ed2fcee37e, a0875f8a5f), clean, pushed.
  Live jobs: none (all 21 hold-ECO runs finished; no elemqk-hold containers on localhost/epyc3).
  Results: results/elem_qk_1024/hold/ (README, hold_summary.json, 21 signoff.json): all NOT SIGNED; recipe b (FF-only,
  margin 3) brings FF hold to -1.6..+0.09 ps (e2 passes hold, TT +27.10) but drv slew / clock insertion 320-363 vs
  250+-40 / face_guard fail on the old 285.12 kits. Run dirs localhost+epyc3:/srv/opentallas-scratch/claude/elem-qk/hold.
  Next: apply recipe b (tools/elem_qk/hold_eco) as the post-route hold step of the KVG3-CORES 216x216 head re-kits once
  they route clean on clock insertion/slew/face_guard.
## ASTK/ECTLK parked 2026-10-24 18:56 PDT (fork ELEMQK-ASTK)
- Branch claude/elem-qk-1024 @22cfe74028 (tools/elem_qk/astk_variants.sh, run_variant.sh, results/elem_qk_1024/astk/VERDICTS.md).
- Live jobs of mine: none (all 14 variants finished; ES r4hs NOT RUN: ot-run "no host qualifies" glitch). Watching only Codex
  intel1:/srv/opentallas-scratch2/claude/codex-qwen/astk_WN_r4 (not mine; collect with signoff.py tt,ff into a new dir).
- Results (all NOT CLOSED, no route): ASTK EN/ES/WN/WS hm55 / r4h / r4hs (EN/WN/WS) -> CTS RSZ-0060 max hold-buffer count
  (flat 55 ps TC hold margin too aggressive). ECTLK e1/e2/e3 (-no_insertion_delay, buffer spacing/clusters, BUFx24 tree)
  -> CTS RSZ-0060, ~11.36k hold buffers: late clock is ck pin geometry (E corner of 881 um), not macro balancing.
  Run dirs: epyc3:/srv/opentallas-scratch/claude/elem-qk/astk/<core>/<v>, intel2:/srv/opentallas-scratch2/claude/elem-qk/ectlk/e{1,2,3}.
- Next: ASTK = margin-15 route (+replica RTL r4 for TT) then FF-only post-route hold ECO (root r4b/r4d recipe), signoff tt,ff;
  ECTLK = measure e1 CTS insertion, then OWNER?: centre clock entry / plan pin move (250 ps budget never waived).
- KV kits parked 18:56 PDT (ELEMQK-KV). Branch claude/elem-qk-1024@2ece7f9a79. Verdicts results/elem_qk_1024/kv/*.json (none SIGNED):
  io_ft TT -98.3/FF +9.5; io_ft_v1 TT -85.4 -> -39.8 with repair_design -max_wire_length 120 (slew 0; residual = input->face flop: SPEF tap insertion 204..239 vs plan 250); io_cor TT -244.3/FF -11.0; io_cor_v1 TT -128.7/FF -27.8/spread 89.4;
  hroot TT -139.7/FF -11.1; all DRC 0, GRT 0, pin_audit + face_guard PASS. sys_c g3h GRT FAIL ovf 109 at UCIe PHY bottom corners (W pins y 250..500 under PHY). sys_SD/_v1 NOT RUN (no x6 PHY view).
  Systemic kit-flow findings: (1) run_kit 6_report RCX OOMs at any cap (peak = cap) -> signoff skipped; run signoff.py separately. (2) 635+ um hops need max_wire_length repeaters (flow left 250 um segments, RCX slew 688 ps). (3) tap_balance lands SPEF insertion ~30 ps below plan 250 -> input budget paths fail.
  RESET RULE conflicts: every kit has a per-partition 2-flop sync on raw arst_n (bind u_rst_sync) fanning out by buffer tree (no relay flops) over up to 1900 um; ot_dp_st face flops async-reset; hroot leaf re-syncs (cascaded ot_rst_relay root->bank/main, unequal depth).
  LIVE (mine, keep running, collect then signoff): intel1 /srv/opentallas-scratch2/claude/elem-qk/kvr2/{kv3_hroot,kv3_io_cor,kv3_io_ft}; intel2 .../kvr2/{kv3_io_cor_v1,kv3_io_ft_v1} (r2 = wirelen + OT_TAP_TARGET_PS 280 + HOLD margin 45, signoff chained; logs localhost:/srv/opentallas-scratch/claude/elem-qk/logs/r2_*.log); intel2 .../kvg3h/kv3_sys_c (-allow_congestion pathfinding, log logs/kvh_kv3_sys_c_route.log; run signoff.py by hand after).
  Next: collect r2 signoffs; sys_c PHY move/halo + plan W pins / host-leg stations (propose KV-G3); hroot relay guide; propose wirelen + tap target fix to gen_phys owners; macro overlay physical/die_plan/qwen_kvsys/elemqk/macro_overlay.json -> KV-G3.

## CODEX notes 2026-10-25 02:39 PDT — KV wave collected
All inherited ELEM-QK KV r2/g3h jobs are finished; none SIGNED. intel1:/srv/opentallas-scratch2/claude/elem-qk/kvr2: hroot TT -137.23 / FF -19.69 ps, DRV 61/60, spread 105.8/85.5; io_cor -235.20/-36.88, DRV81/29, spread102.5/84.1; io_ft -6.78/-7.70 (only setup+hold fail). intel2 kvr2 io_ft_v1 -18.40/-8.95 (only setup+hold fail). io_cor_v1 FAIL GRT-0183 net75231 boxed by congestion after wirelen120 inserted14,103 buffers/14,101 nets (tool warns threshold<184um increases delay). intel2 kvg3h sys_c FAIL GRT-0183 u_bound.u_bin_i_kvs_emb_rowtx__emb_tx_payload/net152160, locally boxed in by PHY/blockage congestion. These are pre-dec17 timing/geometry records, not current-plan release results. Next repair is native reach405/wavefront re-kit on merged v3.9 (not another r2 overlay); keep max-wire repeaters >= measured delay-optimum184um, stations handle reach. sys_c requires PHY/channel clearance in new review; cor/hroot require full clock rebalance, not higher hold margin. ASTK hm55/r4h/r4hs and ECTLK e1/e2/e3 already terminal RSZ-0060 are superseded (oversized hold margins/late corner clock entry); no duplicate routes. Current core repairs/collection tracked KVG3-CORES + KV-G3.

## CODEX notes 2026-10-25 02:53 PDT
Collected old kvr2 successor job signoffs (none SIGNED): intel1 elem-qk/kvr2/io_ft TT-6.78/FF-7.70ps,473/584EP,DRVpassDRC0; hroot TT-137.23/FF-19.69,351/202EP,slew61/60; io_cor TT-235.20/FF-36.88,627/2203EP,slew81/29,DRC0 (finished02:02). Prior spread-gate failures are historical diagnostic; real setup/hold failures remain. Cause unchanged long FT/data legs + late/uneven local clock before405/reset batch. KV steward notified and owns current-plan re-kit; do not reroute these obsolete kits. QC tt_ctlm old v5 remains recorded structural congestion FAIL and stopped. Current QC A0 progress lives in QC-A0; future soft kits await batch and PROTO CLEAN.
2026-10-25 03:16 PDT INFRA -> ELEM-QK: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: /srv/opentallas-scratch/claude/elem-qk (125 GB, cwd). When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.
