# QC-RC97-BT2 handoff (Opus 5.5, sub-lane of QC-ALLFIX, started 11-24 17:37 PST). Report to COORD, cc QC-ALLFIX, QC-CB-C1L.
Job: rc97 row for C1n = st_a_v2 region hard cores at BT_LAT=2 + registered btab read (OT_BTAB_S4R) + latency priced;
private core kits to sign-off + LEC; then st_a_v2 (+ paired st_b_v2) type launches under the anti-churn rule.
Lane dirs: epyc7 + epyc2 /srv/opentallas-scratch2/claude/QC-RC97-BT2 (wt = lane clone of main on epyc7; bin/, base/, cores/, in/, rows/).

## Findings (11-24 18:0x)
- C1l 4da59e55acc0 has 3 region masters on 5 st_a_v2 types (6 slices): h17_n7_s8 (E1 pvd2ec7769, E3 pv4242de79),
  h18_n7_s8 (E5 pv88773f93), h15_n9_s11 (W1+W3 cl9f076a5c, W5 clf4365a62).
- bt_q of a slice feeds all 8 regions: st_a u_r0-3 (bt_ql) AND st_b u_r4-7 (bt_qh via lane x_st_a_st_b), and the st_b
  r_d joins ctl on u_r0's r_v (qc_fabric_transport doc). So BT_LAT=2 must be on all 8 regions of a slice: st_a via the
  new masters, st_b (soft regions) via the bind hook (qc_fabric_transport bt_lat, one value per slice, fail closed).
- HARD_CORE_PARAM_WRAP: the emitted region params must equal the plan param_wrap -> BT_LAT must come from the bind (hook),
  not from the plan alone.
- Btab +1 form is path-preserving: qfd_dv_s5_btab_s4 `ifdef OT_BTAB_S4R -> u_core = qfd_dv_s5_btab_safe_r (same
  u_core.g_btb[k].u_m SRAM names, rd_q stage at macro Q, select 2 stages). The main btab_s4r.sv (HCST-R3) renames the
  hierarchy (u_bt.g_btb) and was not used.
- st_a_v1 slices (E0 E2 E4 W0 W2 W4, masters qfd_dv_s8_station_tail1_*) are NOT in this row.

## Core kits (epyc2, goal finish, recipe = signed 11-17 tl-qcstav2 rk/sta_region_nb0, util 0.4, only BT_LAT 1->2)
- generator bin/mk_bt2.py 7c2abec4c50a (params from C1l hard-core row; pins = plan cores/st_a/sta_region_nb0_pins.json 810d2a9e)
- sta_region_nb0_h17_n7_s8_bt2 unit oth-ubuntu-2004608-1795571986 (kit cores/<m>/kits/<m>_synth0)
- sta_region_nb0_h18_n7_s8_bt2 unit oth-ubuntu-2007105-1795571991
- sta_region_nb0_h15_n9_s11_bt2 unit oth-ubuntu-2010185-1795571996
- waiter: ot-wait on epyc2 (from localhost bg). Logs epyc2 lane dir run_<m>.otrun.log.

## Row RC97-BT2 (C1l base; carry into C1n)
- generator wt/tools/die_plan/qc_rc97_bt2_row.py d89536ec63ca; epyc7 rows/plan_c1l_rc97bt2.json 4de40be104e5,
  rows/rc97bt2_delta.json 73802380c585.
- RTL/tool (lane clone, not pushed yet): rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv (+safe_r), qfd_dv_s5_btab_s4.sv (ifdef),
  bench rtl/test/qwen_dv/s5/run_btab_safe_r.sh + tb_btab_safe_r.sv, hook physical/die_plan/qwen_compute/bind/qc_fabric_transport.py
  (+test_qc_fabric_bt_lat.py, 10 pass), tools/qwen_layerbench/stn_transport_params.py (result/busy +bt_lat-1).
- Latency: 0 lane/station changes (LATCHECK tables unchanged); +1 edge in-slice on the bt round trip: stn result +1, busy +1
  on E1 E3 E5 W1 W3 W5 (compiler DV_STN_TRANSPORT).

## Next
1. btab bench PASS -> push main (ot-push-main) -> post ROW.
2. core results -> export views to qcviews_rc97bt2/<m>/ (lef, tt/ff lib) -> CORE post.
3. scoped strict bind of the st_a_v2 + st_b_v2 types on a C1l fork (forkbindK/bindI pattern) -> types launch (anti-churn).
