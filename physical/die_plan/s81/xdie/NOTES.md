# S81-XDIE (2026-10-24): copy-A/B reserve pair + in-band host on the S81 layer die (v4.8 plan)

One logic design for all layer dies (RELEASE_RACK 2.1): every die gets the 6th SerDes pair; the rack wires it on 64 dies.

## What changed
- Generator `gen_plan_v4.py`: 4 new 2-cell serdes partitions (PHY model ot_pdie_serdes, re-aspected):
  lk_WS2 (NW corner, cols 0-1 row 0), lk_WS3 (col 6 rows 0-1, 1x2), lk_EN2 (cols 14-15 row 19), lk_EN3 (SE corner,
  cols 20-21 row 19). s_0S slice now rows 2-11; s_7N rows 12-18. Corner keep-outs (0,0)/(20,19) given up (OWNER?).
- Endpoints (rack names: EN = s_7N pair B, WS = s_0S pair B): coll lanes s_7N_LP <-> lk_EN2/EN3 and s_0S_LP <->
  lk_WS2/WS3, 512 b tx / 514 b rx each (same as pair A). copyb_in uses EN2+EN3 (pre-group S dies), copyb_out
  arrives on WS2+WS3 (post-group S dies).
- Reserve lanes are routed and window-packed after all others, so no existing lane moves except inside the re-sliced
  s_0S cells: unit__seqhost__s_0S_LP 14 -> 13 cycles (LAT_UNIT__SEQHOST__S_0S_LP; shorter, no latency group).
- Host: lk_WS0 no longer host: true. die_io.json marks io_lk_WN2/WN3_u_phy host: "in_band" with the declared route
  lk_WN2 -> [coll__lk_WN2__s_0N_LP] -> s_0N_LP -> [ctrl__s_0N_LP__seqhost] -> seqhost (same for WN3).
  run_v4.sh now regenerates die_io.json (die_io.py plan --in-band-host ...).
- Tools: die_io.py (--in-band-host PART[=LANE+LANE]; check accepts in-band dies, re-checks a declared host_route,
  rejects mixed dedicated + in-band), schema (host true|false|"in_band", host_route), xdie_io.py (dedicated host =
  host is True / iface host; in-band windows must be rack-wired for the role). Tests in test_xdie.py / test_xdie_io.py.

## Results (before -> after)
| check | before (v4.8 committed) | after |
|---|---|---|
| G0 | PASS 0 err / 1106 warn, 174 types / 400 parts | PASS 0 err / 1133 warn, 180 types / 400 parts |
| G0C --completeness | 91 err (all hard_cores), 83/174 clean | 91 err (same 91 hard_cores set), 89/180 clean, die_io host_mode in_band |
| xdie_io (H=s81_head, S=B=s81) | FAIL 130 err (4x32 missing EN2/EN3/WS2/WS3 + host S + host B) | PASS 0 err, 2952 circuits, 4 warn (role B does not use EN2/3, WS2/3) |
| col_* frame types | 7 | unchanged (byte-identical type defs) |
| census dropped | 0 | 0 |
Files: g0_summary.json, g0c_summary.json, xdie_io_report.json here, all re-run on the committed tree (fix commit after
ffeace5ae4: that commit missed the regenerated census_map.json / instance_map.json / cells_est.json, so G0 at
ffeace5ae4 FAILs 12 census errors on the old s_0S_x / s_7N_x names; fixed in the next commit). census_cov dropped 0.

## unit__s_7N_LP__seqhost (604 b, 14 faces): keep
604 = f_host 515 + f_ks 53 + mu_rt 32 + f_lf 4 (census s81_lanes.tsv, u_s_7N -> u_seqhost); the reverse lane
unit__seqhost__s_7N_LP 176 = t_host 77 + t_kd 54 + mu_c 34 + mu_rc 11. It is the legacy host plane of the s_7N
host-plane endpoint (ot_s81sl_lep_mu HOST_EN 1) plus its MU control/return (mu_rt_7n). EN0/1 (TP d+2 mesh) carries
layer data, not this plane, so it does not make the lane obsolete. The HOST(b) in-band path (s_0N hb_f_host ->
ctrl__s_0N_C__seqhost 571 b -> hostb landing, select_hbe in dsdv_hostb_source.sv) can replace the f_host/f_ks part
(568 b) once the owner rules HOST(b) is the only host source on stage dies; mu_rt_7n + f_lf (36 b) stay either way.

## OWNER?
1. NW (0,0) and SE (20,19) corner bump/ESD keep-outs are now serdes slots (lk_WS2, lk_EN3). OK?
2. lk_WS3 is re-aspected to a 1x2 cell column (1442.88 x 2453.76 um); PHY model fit not checked beyond the slot.
3. RTL owed: s_7N / s_0S lep cores must expose pair-B coll ports (coll_i2/i3/o2/o3); today only lep_mu_ab (s_0S of
   the AB die) has tx2/tx3/rx2/rx3, and s_7N's HOST_EN endpoint has no AB variant ($fatal on HOST_EN && AB_EN).
4. Retire the f_host/f_ks part of unit__s_7N_LP__seqhost (HOST(b) only)? Not done without a ruling.
5. hard_core_gaps.json is NOT recommitted: here the vp closed_archive LEF is LOST, so a regen records vp as a gap
   (environment, not a design change). die_plan.json itself is byte-identical to v4.8 without the reserve edits.
