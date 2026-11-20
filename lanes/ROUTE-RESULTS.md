# ROUTE-RESULTS (hourly, newest last)

## 2026-11-19 23:5x PST ROUTE-RESULTS (HOURLY-WRITEUP-23xx, first run, window 00:00-23:32 today)

ROUTE-RESULTS 11-19 00:00 to 11-19 23:32 (from kit run logs + signoff.json; gate = DRC 0, TT setup >= -42 ps, FF hold >= 0)  hosts local,epyc2,epyc7,epyc8,epyc9,epyc10,intel1
| die | CTS | GRT | route | sign-off | pass | fail setup | fail hold | fail congestion | fail DRC | fail crash | routed, no sign-off |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s81 | 280 | 165 | 39 | 25 | 4 | 8 | 7 | 1 | 8 | 47 | 12 |
| head | 32 | 28 | 17 | 8 | 2 | 3 | 0 | 0 | 3 | 3 | 9 |
| qc | 170 | 114 | 43 | 40 | 6 | 3 | 27 | 0 | 4 | 26 | 3 |
| kv | 15 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 3 | 0 |
| other | 6 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| all | 503 | 310 | 99 | 74 | 12 | 14 | 35 | 3 | 15 | 79 | 24 |
ended past CTS: 182  passed 12  failed 146  (fail rate 92% of 158 decided)
  of the 79 tool crashes, 74 have no crash signature: no process, log idle >= 120 min (crashed or cancelled by the wave)
  s81 congestion/overflow: 1 (ot_s81sl_leaf__t27)
  s81 tool crash: 47 (col_h10_r1__t1__cl95b37463__pv6a7ae122, col_h10_r1__t1__cl95b37463__pv86f5e3b9, col_h10_r1__t1__cl95b37463__pv86f5e3b9, col_h10_r1__t1__cl95b37463__pve28d14fa, ...)
  s81 DRC: 8 (col_h9_r2__t1__clce45cab5__pv06a1adf6, col_h9_r2__t1__clce45cab5__pv22267ca0, col_h9_r2__t1__clce45cab5__pv31e47bd5, col_h9_r2__t1__clce45cab5__pv37074264, ...)
  s81 hold: 7 (slice_station__t24__cl64811a5d, slice_station__t24__cl66b71008, slice_station__t24__cleece78ec, slice_station__t30__cl1653104c, ...)
  s81 setup timing: 8 (col_h9_r2__t1__cl774acf45__pvea45273b, col_h9_r2__t1__clc9ad8f7e__pv45d0c698, col_h9_r2__t1__clce45cab5__pv6827937d, col_h9_r2__t1__clce45cab5__pvcd1d9f5f, ...)
  head tool crash: 3 (hd_spn, hd_tile, hd_tile)
  head DRC: 3 (hd_host_n, hd_host_n, hd_host_n)
  head setup timing: 3 (hd_ctl, hd_ctl, hd_host_w)
  qc tool crash: 26 (cbf_q00__cl870de686, cbx_q10__cl89936551, cbx_q10__cl89936551_h, cbx_q10__cl94a12200, ...)
  qc DRC: 4 (sle_st_a_v1__cl67389ecd, sle_st_a_v2__pv30dda31f__pv88773f93, sle_st_a_v2__pv30dda31f__pvd2ec7769, sle_st_a_v2__pv4242de79)
  qc hold: 27 (coll_s, sle_hc0__cl05696ed1, sle_hc0__cl05696ed1, sle_hc0__cl929603c0__cl38badc56, ...)
  qc setup timing: 3 (sle_su_l1__cl5ea486db, slw_fw_v2__cl8537f156, slw_sc_v1__cl63e5a7a2)
  kv congestion/overflow: 2 (kv3_hgi_v1__cl42bc8b12, kv3_pc_v3)
  kv tool crash: 3 (kv3_hgi_v3, kv3_pc__cl254f2e73, kv3_pv_v5)
  other hold: 1 (sle_hc0__cl929603c0__cl38badc56)

How to read: counts come from each kit's own ORFS logs (run/logs/asap7/<design>/base/4_1_cts, 5_1_grt, 5_2_route .json/.log) and signoff/signoff.json, not the wave log; a build is counted in a stage row when that stage file was written in the window, and once in the outcome columns by its last event. Pass = DRC 0, TT setup >= -42 ps, FF hold >= 0 (the profile's own gates when present). 'fail crash' = a crash signature, or no process and a stage log idle >= 120 min (possibly cancelled by the wave). Builds fail one class each (first of DRC, setup, hold). Tool: tools/route_results.py + tests/test_route_results.py on main (cb8aa2980b8), copy in ~/coord/tools. Runtime: the all-host sweep took ~25 min (epyc8 load 220); for the hourly block use --hours 1 with --roots limited to the wave runs and active private dirs.


## 2026-11-20 00:1x PST ROUTE-RESULTS (HOURLY-WRITEUP-00xx, fast mode, window 23:03-00:03)

ROUTE-RESULTS 11-19 23:03 to 11-20 00:03 (from kit run logs + signoff.json; gate = DRC 0, TT setup >= -42 ps, FF hold >= 0)  hosts local,epyc2,epyc7,epyc8,epyc9,epyc10,intel1
| die | CTS | GRT | route | sign-off | pass | fail setup | fail hold | fail congestion | fail DRC | fail real crash | cancelled/superseded | dead, unexplained | routed, no sign-off |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s81 | 111 | 81 | 4 | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 2 |
| head | 4 | 3 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qc | 19 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| kv | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| all | 137 | 92 | 6 | 3 | 0 | 1 | 0 | 0 | 2 | 1 | 0 | 0 | 3 |
decided past CTS: 4  passed 0  failed 4  (fail rate 100%);  not failures: 0 cancelled/superseded, 0 dead unexplained, 3 routed awaiting sign-off
  s81 DRC: 2 (col_h9_r2__t1__clce45cab5__pv06a1adf6, col_h9_r2__t1__clce45cab5__pv22267ca0)
  head setup timing: 1 (hd_ctl)
  qc real tool crash (signature): 1 (slw_fe_v1__clfe325744__cl08d14f0d)

QC has been blocked since 22:55 by the src_manifest breaker (58 rows), and rt sync has been stuck since 00:02, so QC kit launches in this hour are zero by block, not by choice.

### Corrected 11-19 day table (crashes split: real signature vs cancelled/superseded vs dead unexplained; tools/route_results.py c844e23cb28 on main)

ROUTE-RESULTS 11-19 00:00 to 11-20 00:00 (from kit run logs + signoff.json; gate = DRC 0, TT setup >= -42 ps, FF hold >= 0)  hosts local,epyc2,epyc7,epyc8,epyc9,epyc10,intel1
| die | CTS | GRT | route | sign-off | pass | fail setup | fail hold | fail congestion | fail DRC | fail real crash | cancelled/superseded | dead, unexplained | routed, no sign-off |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s81 | 315 | 190 | 40 | 25 | 4 | 8 | 7 | 1 | 6 | 1 | 7 | 39 | 13 |
| head | 35 | 28 | 17 | 9 | 2 | 4 | 0 | 0 | 3 | 0 | 0 | 3 | 8 |
| qc | 180 | 115 | 43 | 40 | 6 | 3 | 27 | 0 | 4 | 4 | 5 | 17 | 3 |
| kv | 15 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 3 | 0 |
| other | 7 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| all | 552 | 336 | 100 | 75 | 12 | 15 | 35 | 3 | 13 | 5 | 12 | 62 | 24 |
decided past CTS: 83  passed 12  failed 71  (fail rate 86%);  not failures: 12 cancelled/superseded, 62 dead unexplained, 24 routed awaiting sign-off
  dead unexplained = no process, no crash signature, log idle >= 120 min, no ot-run cancel or wave CANCELLED row
  s81 cancelled/superseded: 7 (col_h10_r1__t1__cl95b37463__pv86f5e3b9, dsdv_slice_lepw_mu_LP__t2, dsdv_slice_lepw_mus_LP__t2, ot_s81sl_leaf__t16, ...)
  s81 congestion/overflow: 1 (ot_s81sl_leaf__t27)
  s81 real tool crash (signature): 1 (serdes__t15__cla3d02796)
  s81 dead, unexplained: 39 (col_h10_r1__t1__cl95b37463__pv6a7ae122, col_h10_r1__t1__cl95b37463__pv86f5e3b9, col_h10_r1__t1__cl95b37463__pve28d14fa, col_h10_r1__t1__cl95b37463__pvf724da2a, ...)
  s81 DRC: 6 (col_h9_r2__t1__clce45cab5__pv31e47bd5, col_h9_r2__t1__clce45cab5__pv37074264, col_h9_r2__t1__clce45cab5__pv467913cc, col_h9_r2__t1__clce45cab5__pvb7e88dd2, ...)
  s81 hold: 7 (slice_station__t24__cl64811a5d, slice_station__t24__cl66b71008, slice_station__t24__cleece78ec, slice_station__t30__cl1653104c, ...)
  s81 setup timing: 8 (col_h9_r2__t1__cl774acf45__pvea45273b, col_h9_r2__t1__clc9ad8f7e__pv45d0c698, col_h9_r2__t1__clce45cab5__pv6827937d, col_h9_r2__t1__clce45cab5__pvcd1d9f5f, ...)
  head dead, unexplained: 3 (hd_spn, hd_tile, hd_tile)
  head DRC: 3 (hd_host_n, hd_host_n, hd_host_n)
  head setup timing: 4 (hd_ctl, hd_ctl, hd_ctl, hd_host_w)
  qc cancelled/superseded: 5 (slw_fw_v1__cl51d45468, slw_fw_v1__clf51c11d8__clc7ddab13, slw_fw_v1__clf51c11d8__clc7ddab13, slw_su_l1__cla2a78701, ...)
  qc real tool crash (signature): 4 (cbx_q10__cl94a12200, coll_ftc, slw_fe_v1__clfe325744__cl08d14f0d, slw_fe_v2__cle312294d)
  qc dead, unexplained: 17 (cbf_q00__cl870de686, cbx_q10__cl89936551, cbx_q10__cl89936551_h, cbx_q10__cl94a12200, ...)
  qc DRC: 4 (sle_st_a_v1__cl67389ecd, sle_st_a_v2__pv30dda31f__pv88773f93, sle_st_a_v2__pv30dda31f__pvd2ec7769, sle_st_a_v2__pv4242de79)
  qc hold: 27 (coll_s, sle_hc0__cl05696ed1, sle_hc0__cl05696ed1, sle_hc0__cl929603c0__cl38badc56, ...)
  qc setup timing: 3 (sle_su_l1__cl5ea486db, slw_fw_v2__cl8537f156, slw_sc_v1__cl63e5a7a2)
  kv congestion/overflow: 2 (kv3_hgi_v1__cl42bc8b12, kv3_pc_v3)
  kv dead, unexplained: 3 (kv3_hgi_v3, kv3_pc__cl254f2e73, kv3_pv_v5)
  other hold: 1 (sle_hc0__cl929603c0__cl38badc56)

The 11-19 first block (23:5x) counted 79 'tool crash'; only 5 have a crash signature. 12 were cancelled/superseded (ot-run cancel signal or wave CANCELLED row) and 62 have no record at all (no process, log idle >= 120 min), mostly the d8i col_h10_r1 and QC cbx/cbf kits: those are not counted as failures but need an owner to say why they stopped.
