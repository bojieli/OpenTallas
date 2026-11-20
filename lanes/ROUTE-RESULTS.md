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

