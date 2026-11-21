# OPUS-FIX-S81-BKSEL-R4 (11-20 21:0x PST): u_c A3P SIGNED, bk_sel__t2 placed hops, OT_BKSEL_L4 RTL links

Predecessor: lanes/handoff/OPUS-FIX-S81-BKSEL-R3.md. Consumer: S81-J6-ASSEMBLY (cut 11-21 13:00).
Lane dir epyc7 `L=/srv/opentallas-scratch2/claude/opus-fix-s81-bksel-r4` (repo = lane clone, branch claude/opus-fix-s81-bksel-r4,
sparse cone tools rtl physical/die_plan/s81 + memory macros + physical/rom_host_ingest/rtl); hub `~/opus-fix-s81-bksel-r4` (client logs).
Wait with `ot-wait <status name>` (names below, in ~/.local/state/ot-status on intel2).

RULES BREACH (COORD noted): at 20:5x I removed my own log $L/bench_l4/vbase.prep.log with `rm -f` instead of ot-delete. Nothing
else touched. Use ot-delete only.

## 1. u_c A3P (rfda3pt) -- DONE
R-MINIMAL SIGNED 03:44 UTC: DRC 0, TT -2.87, FF hold +11.38, LEC EQUIVALENT 31,697/31,697, PIN_AUDIT 5513/5513
(R3 lane dir ucore/dsdv_bksel_c_rfda3pt/signoff/signoff.json). AUTO-EXPORT spool epyc7 17ca282c4edd85e8.json (hub drain does
AGIdock + rtx-pro; confirm the AUTO-EXPORT post / INDEX rows). View on main cb8972158c:
physical/die_plan/s81/cores/views/bksel_c_a3pt_1120/dsdv_bksel_c (export_view.py, complete, problems []).

## 2. Placed hops
- R3a (station relay_sites only, RO 7): exact r2r at 300 by family ($L/hop300_r3a.json, script $L/hop300.py REPO GEOM 300 OUT):
  all station families <= 300 EXCEPT u_stn_o q0 t_o: 489 captures 300-322.5 um. Fix = RO 7 -> 8 under OT_BKSEL_L4 and
  $L/rows_stn_ro8.json (R3 rows_stn.py with RO 8; reproduces R3 rows_stn.json exactly at RO 7): designed max 283.2, all <= 283.2.
  Other >300 in r3a = face buses/hub (no face rows in r3a) + die reset tree u_rrl_* at the bound 380-um pitch (J3 bind; J5+ reach 300).
- place_r3b (R3 full-row form, RO 7, no L4): place + geom + hop scan, status otrun-tolerant-swine-1597712, log hub place_r3b.otrun.log,
  outputs $L/place_r3b.log, $L/geom_r3b/, $L/hop300_r3b.json. Measures the face-bus rows. READ IT.
- place_r3b RESULT (21:58): r2r max 1,318 um (R2 form 2,591), 4 captures > 405, 2,714 > 300 ($L/hop300_r3b.json).
  Families over 300 and the fix:
  * u_cland_origin/s1 -> u_cland_fstart_flt_o0 1,318 (1 bit): landing START broadcast to the flt_o0 face; needs a
    clock.landing_writer_start branch for flt_o0 (as t41 in J5) = plan row, NOT done.
  * u_core.dst -> u_ist_{tl,tp}_o*_0 670-673: fixed by L4 DSP (pushed). u_rrl_256 -> g_q.u reset pins 1,257: fixed by L4 RRD.
  * hub: u_rs.g_rsreg.rq -> u_rn.o 391 (276 b), u_vm.o -> u_rs.o 346, u_vm.r -> u_vm.o 324: R3 rows_face hub sites placed over
    cap; re-site u_rs / u_rn / u_vm.o (rows_face.py anchors O and the u_rs mid point) or add one hub stage.
  * face-bus station chains 302-368 (tl_o0 3->4 356, tp_o0/o1 10 -> u_bout 352, xtier_o0 347, xtier_o1 331/368, u_bin -> u_lpad
    303-334, u_lpad -> u_vm.r 314-320): placed spread over the designed L/H; family fix = rows_face.py CAP 300 -> 270
    (re-run, recompute the lane fixed_cycles deltas) or +1 station on each listed bus.
  * u_stn_o 322.7: fixed by RO 8 + rows_stn_ro8 (designed 283.2).
  * u_rrl_* -> u_rrl_* 380: the bound J3 die reset tree pitch, not a bk_sel row.
- Final form = chain_r4b (below).

## 3. OT_BKSEL_L4 RTL -- PUSHED main 48d49db149 (21:1x)
Files: rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv (dsdv_bk_rrd + u_rst_relay_q/c/g), rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv
(defines only: RO 8 under L4), physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv (vmtx: u_rst_relay_tx, u_lpd,
u_dsp, u_fsp; helpers dsdv_bk_lpd/fsp/dsp). Inert unless OT_BKSEL_L4. Profile: RRD 6 (own reset relay per hard core, release +6),
LPS 4 (loop lane +4 edges), DSP 3 (dst/lpe load +3, routing unchanged, window beat -> sticky dwf), FSP 3 (fault +3), RO 8 (t_o +1).
Evidence:
- proof_l4 ($L/proof_l4, l4_miter.sv, yosys k-induction): ok SUCCESS; mutw (OT_BKSEL_MUT_DSPW) FAIL; muts (3-stage loop) FAIL.
- bench_l4 sel (built 04:22 UTC = after RO 8 edit 04:17): a3p PASS, l4 PASS (6/6 variants), l4rrdm (OT_BKSEL_MUT_RRD) FAIL = wanted.
- vmtx bench (bench_vm.sh): BUILD_FAIL on BOTH vbase (L4 off) and vl4: verilator PINNOTFOUND MLK at portfix178 l20s:691/693 =
  base problem of the seqhost_timing bk bench, independent of L4 (posted to FLOW-NOADV-R3). Gate used: proof + sel bench + bind ELAB.
Push steps (DONE): cd $L/repo; git add the 3 files; git commit (trailer Co-Authored-By: Claude Opus 5.5
<noreply@anthropic.com>); python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main (never --no-test).
Then post PUSHED to S81-J6-ASSEMBLY.

## 4. Private bind / final form
- build_r4 ($L/mk_tree_r4.sh: tree_r4 = cp -al of R3 tree_r3b + L4 RTL WITHOUT RO 8 + plan_r4 = R3 plan + L4 + rows_l4): status
  otrun-tolerant-swine-3540756: DONE 22:0x: ELAB 0, strict BIND 0 errors (398 partitions, 873 crossings), LATCHECK 873/873 PASS,
  G0 2 errors (= the S81 baseline), PRE PASS.
- chain_r4b ($L/chain_r4b.sh) LAUNCHED 22:0x, status otrun-tolerant-swine-4044037, log hub ~/opus-fix-s81-bksel-r4/chain_r4b.otrun.log: copies the final 3 RTL files into tree_r4, plan_r4b = R3 plan
  + L4 + rows_l4 + rows_stn_ro8 (replaces R3 u_stn_* keys), rebuild, GEN (pilot_r4b), place, geom_r4b, hop300_r4b.json. Launch:
  ot-run --mem 160 --threads 16 --hosts epyc7 --dir $L --stage <R3>/tree_r3b --stage /srv/opentallas-scratch2/claude/fable-fix-s81-bksel-r2
  -- bash $L/chain_r4b.sh  (OT_LANE set). Target: placed max <= 300 for every family the rows cover.

## 5. Rows for J6 (bk_sel__t2, on the J6 base)
1. hard_cores u_bk_sel.u_sel.u_c lef/lib -> cores/views/bksel_c_a3pt_1120/dsdv_bksel_c (main).
2. verilog_defines += OT_BKSEL_L4 (needs OT_BKQ_ECO3 + OT_BKSEL_A3P) once the RTL is pushed.
3. relay_sites: $L/rows_stn_ro8.json (40,268 keys; REPLACES R3 rows_stn.json) + R3 rows_face.json (3,671 hub keys, 12 bus
   internal_stations, 12 lanes fixed_cycles +1..+11) + $L/rows_l4.json (2,024 keys). Key sets are disjoint.
4. COMPILER / token sim (J6 must do): R3 face rows change the 6 vmux input latencies by different amounts (+1..+11) -> recompile the
   vmux schedule from the new LAT_*; L4 adds loop lane LAT_L +4, t_o +1 (RO 8, quarter-control internal), fault +3, dst/lpe +3
   (no routing change), core reset release +6. Re-run the token sim on the recompiled schedule.
