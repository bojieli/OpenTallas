# OPUS-FIX-KV-PV-R3 handoff (KV pv family owner: kv3_pv*, pv_pair; successor of FABLE-FIX-KV-PV-R2)

Written 2026-11-20 18:5x PST. Posts lanes/posts/OPUS-FIX-KV-PV-R3.md. D27 is assembled by KV-PLAN-R2 (cut 11-21 20:00).
Lane dirs: epyc7 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r3 (repo = ot-lane-clone of main 95661471cd, tools/, out/, rleg/, replay/),
intel1 same path (stage/ = copies of v8p 3_4/3_5 odb, v8p kit files, por_v8p, kit rtl; db/v8p_3_place.odb; out/v8p_hops.tsv).
Hub chains intel2 ~/tmp/okpvr3 (chain_census.sh, chain_i1.sh, chain_replay.sh, chain_pos.sh, chain_rleg.sh; logs *.log).
Predecessor kits / chains untouched: epyc7 fable-fix-kv-pv-r2/kit/{v8m,v8c,v8p}, intel2 ~/tmp/ffkpvr2 (watch_r2.sh posts AUTO-KIT).
The predecessor's census chain ~/tmp/ffkpvr2/chain_hops.sh (pid 4135070) still waits on epyc7: not mine, left alone.

## Found 18:2x (census v8p 3_place, intel1, 19,038 zero-logic hops > 450 um)
- The 1,228-um class is NOT a stage hop. pad_min_stations 16 cut the trunk lines per stage (sg0..sg9, latch u_fl_*_sg<j> between),
  and the LATCH + its repeaters sit off the hop, toward the run start:
  astk_E owner_response_255_t_10: sg5 (1584.6,596.3) -> 8 bufs west along y 596 -> latch u_fl_..._sg6 (480.6,924.6) -> sg6 (1970.7,596.0)
  (1,433 + 1,819 um, n 120 / 192); astk_W 188_t_10 1,233 / 1,509 (latch 913.7,1306.7); pvw ctl_cmd_7_t_10 1,366 / 1,627 (latch 403.9,1230.3);
  vport W/E d3 t_41 latches 942-968 um.  Stage-to-stage distance is only ~386 um.
- Cause (strong hypothesis, replay running): v8p's kit dly_spread.tcl predates DLY-REPAIR-1 f2e64e5d3b (13:45 PST, on main):
  "a hop that ends on an anchor which also starts the next run took f1 = 0.0 ... repeaters went BACKWARDS along the route".
  The latch counts as a repeater of the hop in SEGMENT form, so it went backwards too.  v8m / v8c have the same old copy.
- Proof job: intel2 ~/tmp/okpvr3/chain_replay.sh -> intel1 replay/ (kit PRE_DETAIL_PLACE hook on 3_4_place_resized.odb with main's
  dly_spread.tcl + OKP MAXHOP_AFTER print; replay.log, pos_after.txt).  Expect max_hop << 1,228 and the latches on their hops.
- Fix = D27 kits GEN on current main (has f2e64e5d3b and PLACE-SLEW 320).  No new row needed if the replay confirms (ROW C = tools re-pin).

## Reset legs (item 3)
- RESET-RELAY-GEN-1530 rows for kv3_pv_v2 in lanes/handoff/RESET-RELAY-GEN-1530-rows.json (10 inst_taps rows, 13 -> 0 legs > 300 um,
  read on the D25e3 bind; tap ids are per bind: re-run tools/die_plan/reset_leg_plan.py on the D27 bind).
- kv3_pv_v8 read on the v8p placement queued: intel1 tools/run_rleg_i1.sh (geom dump + reset_leg_plan; out rleg/report.json, plan_rleg.json).

## Kits (item 1), epyc7, all in CTS at 18:1x (OT_STB done, tap balance it0/it1); no setup number yet
Read order: 4_1_cts log tt repair "before" wns; then GRT iteration 5 (congestion) v8m vs v8c on upper strip / pin edge / centre street.

## Update 2026-11-20 19:4x PST (read first)
- CONFIRMED on v8p stage ODBs (intel1 out/pos.txt): astk_E 255 sg6 latch 3_4 (1666,633) -> 3_5 (480,924), its repeaters to x 480-1267;
  ctl_cmd_7 sg7 latch (1395,736) -> (403,1230).  Last stage sg6/sg7 is FIRM = anchor -> DLY-REPAIR-1 bug (1).  Fixed on main f2e64e5d3b.
- Rows for D27: lanes/handoff/OPUS-FIX-KV-PV-R3-rows.json.  READY: B pad_min_stations 16, C tools pin >= f2e64e5d3b + 3098d89a95,
  D reset inst_taps kv3_pv_v8 (10 rows, 10 -> 0 legs, v8p bind) + kv3_pv_v2 (RESET-RELAY-GEN-1530), F pv_v6n ft9_i band widened.
  PROPOSED: E pv_v1n o_vport_E_N_f 7 stations on a route (+1 cycle, LATCHECK bundle mate), family follow-up for the face-bunched
  R8 bundle-mate fault rows; A flip (pending GRT it5); G ft0 not measured.
- v8q private kit (v8p plan, current main tools in my clone 95661471cd): hub ~/tmp/okpvr3/chain_q.sh v8q, log chain_v8q.log / kit_v8q.log,
  epyc7 opus-fix-kv-pv-r3/kit/v8q.  First read: 3_5 OT_DLY_SPREAD max_hop + NOROUTE, then CTS setup.  DO_NOT_COUNT.
- Replay (main dly_spread on v8p 3_4): intel2 ~/tmp/okpvr3/replay3.log, intel1 replay/replay.log (OKP MAXHOP_AFTER line).
- COORD (FABLE-PD-KV-1840): no held pv row goes to route.  u_bin reset class = RESET-RELAY-GEN-R2; take its rows when posted.
- Sign-off/export: none.  All 10 held pv D25e3 rows are -4.4..-26 ns at place; no pv type is near sign-off until D27 kits run.

## Update 2026-11-20 21:xx PST (read first; supersedes the 1,228 cause above)
- CORRECTION: the dly_spread max_hop 1,228 um is u_bin_i_pvw__u_ctl_cmd q[31], a 1-stage bin chain (main's dly_spread replay on v8p 3_4:
  still 1,228, fail 32 -> 0, NOROUTE 169).  The 1.4-1.8 mm hop-LATCH class (census) is fixed by main (astk_E 255 sg6 latch -> 1872,596).
  OPEN: the u_bin ctl_cmd[31] single-stage leg (find its driver/sink on v8p 3_place: intel1 db/v8p_3_place.odb, tools/pos.py with a PAT).
- STATION-ROUTE-SPREAD on main c8876644a5 (tools/die_plan/station_route_spread.py + test, 5 tests).  Fault rows for 7 pv types:
  lanes/handoff/OPUS-FIX-KV-PV-R3-fault-rows.json (26 rows, all <= 300 um; +1 cycle v5n E_f_d1, v7 W_f).  kv3_pv_v12 has no placed geom: run
  the tool on its first D27 placed kit.  Without --conn the tool also re-sites the 405-era rows (+17..+49 cycles per type): separate opt-in.
  Batch scripts: tools/srs_batch.sh (all rows), tools/srs_rows.sh (rows by conn RE) on epyc7 / intel1; hub chains chain_srs.sh / chain_srsf.sh.
- v8q (proof kit, current main): GEN still waiting for memory on epyc7 at 21:0x (chain_v8q.log).  Read 3_5 OT_DLY_SPREAD max_hop + NOROUTE,
  place WNS (3_4 log / tt repair), census (tools/run_hops2.sh on a copy of 3_place.odb), then CTS.  Not watched by watch_r2.sh: add it.
- Flip: v8m/v8c still in CTS (tap balance it2 at 02:5x UTC).  Read CTS tt setup, then GRT it5 congestion on upper strip / pin edge.
