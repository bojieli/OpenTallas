# FAM-S81-COL-H9R0 handoff (started 11-21 04:2x PST, split from FAM-S81-COL-R3; updated 04:5x)
Family: S81 col_h9_r0_p1..p6 (~60 unsigned). R3 keeps col_h9_r1/r2 + shared J7 col relay/ft rows; COL-H10 has col_h10_*.
## State
- J6 (dc92652f0d5) applied 04:15; every col_h9_r0 J6 row is in hold_items (S81-J6-ASSEMBLY-R2 "J6 reps first"). Old-plan (J5 224567138ab) kits keep running and count (any-plan).
- 13 J5 route jobs live (autopilot queue). Closest to sign-off (GRT TT setup / hold before final hold ECO):
  - col_h9_r0_p2__t1__cl9f71e63d__pva4376595 job 0d6487d7a8c6 intel1: GRT -15.6 ps, DRT running  <- REPRESENTATIVE
  - col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a job 4e4323c4d5b1 epyc10: GRT -24.5, DRT running
  - col_h9_r0_p2__t1__cl0045af7b__pva2793873 job 3283f16cae2b epyc10: GRT -37.6, DRT running
  - col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67 job 64e24c10ad78 epyc10: GRT -39.5, DRT iter2 (148k->25.7k viol)
  - CTS-only so far: p1 pva2e3974f -214, p1 pvb49c16c8 -262, p3 pv1489a898 -125, pv625eef47 -121, p5 pveda1ecc9 -215, pvc6e5797f -211 (epyc9), p6 pv0012ba28 -46, p2 pv5752c4ff -275, p2 pv2744f675 in CTS.
- Route work dirs: /srv/opentallas-scratch{2,3}/claude/ot-jobs/<item>-route-<host>-*/work/run (metrics logs/asap7/*/base/*.json).
## Done
- 04:4x pv697f40c9 gen overlap (OT_MACRO_MOVES u_r0.u_c3_6 / u_r0.u_e3.u_e): the __pv* glob 4-move set moves u_e3 onto u_c3_6. Set exact item_env OT_MACRO_MOVES = Codex three-move set (e1/cf/t0, no e3), coord 36b66310fdc. Codex E8 2930371 placed that set clean (geom PASS-COND; geom rc1 = GRT dump timeout only). Placed scan still: 26 groups > 405 um, 413 bits > 580 um (u_lpad_x_i0 -> u_y_xo3 630 um) -> needs relay stages (xo family; R3's J7 rows cover the h10 xo chains; check same rows apply).
## Next
1. Waiter on the 4 DRT jobs; on sign-off of any: export, credit, hand row/settings to S81-J6-ASSEMBLY-R2 (J7) and relaunch siblings.
2. If a rep fails: read the post-route reports; hold <0 after ECO -> structural hold; setup -> stations.
## seg405 structural rows (FABLE-PD-S81-0440 item 6; COORD 04:5x) - 05:0x
- Generator intel1 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0/mkdepth405.py IN OUT ROWS [TYPE_RE]: every col_h9_r0 relay_depth row to D >= ceil(path/405)-1 (review metric path/(D+1)); RLYBR far-branch sinks of one xa_K/xb_K copy (bs0.i_x*, t1.x*i) share one D; cc_K_0 >= that D. Then FAM-S81-COL-R3 mkxalign.py (TYPE_RE ^col_h9_r0_) re-aligns bs1 (D = cc - x).
- On J5: 300 rows / 60 types (bs0.i_x0/i_x1 1->2 x36, t1.xai/xbi 1->2 x60, y_cc_1_0 1->2 x60, y_x2_2_0 2->3 x48) + 72 xalign rows (bs1 i_x0/i_x1 D2, 36 types). rows_d405_j5.json, rows_xalign_d405_j5.json, plan_d405x_j5.json (sha 3fb28438).
- ORDER for J7: after R3 relay rows and R3 xalign; run mkdepth405 then mkxalign on the J7 base (do not take R3's J5 h9_r0 xalign rows verbatim: cc D changes).
- Gate: tree src1 (J5 src + rt f3db2d0e628f tools, as R3 src5), bind.sh = strict --all-gaps bind + LATCHECK + G0 (check.py, base vs new) via ot-run intel1 (bind_otrun.log; queued for memory 04:57). Hub chain intel2 fam-s81-col-h9r0/chain.sh -> kit_wave run-item wave/spec.json (rep pva4376595, spec from the live J5 a3 spec, src_manifest off) -> place/geom. Then route via run_kit.sh GOAL=route.
- Not covered: xo0..3 port->port bus (placed hops 600-756 um on the rep, 580-630 on p1 pv697f40c9) is not a relay_depth row; next delta if the rep route misses.
## xo bus rows (COORD 05:1x) - 05:0x
- intel1 fam-s81-col-h9r0/mkxo.py IN OUT ROWS NATIVE_STATIONS_DIR [D=3]: u_r0_u_y_xo{0..3}_0 port o D3 (stages_existing 2), equal on the 4 slices (one 1104-bit bus); 144 rows on 36 types (p1/p2/p4/p5, whose bound RTL has the xo relays; p3/p6 have none). +3 cycles on xo lane. rows_xo_j5.json, plan_d405xo_j5.json (sha 903a7b86).
- J7 ORDER (col_h9_r0): R3 relay rows -> R3 xalign -> mkdepth405.py -> mkxalign.py ^col_h9_r0_ -> mkxo.py.
- bind1 (seg405+xalign, no xo) started 05:01 before the swap: kept as gate A. bind2 (src2 = + xo D3) queued on intel1 (bind2_otrun.log) = the variant the kit uses. Hub chain2.sh (intel2 fam-s81-col-h9r0/chain2.log) waits bind2 -> run-item wave/spec.json (event famh9r0s2, src2/bind2) -> place/geom. chain.sh (bind1) stopped by exact PID.
## STAND-DOWN 11-21 05:1x (context) - successor FAM-S81-COL-H9R0-R2
- Rows/plan-event owner is now S81-J6-ASSEMBLY-R3 (R2 stood down); J7 order reposted there.
- Live, do not duplicate: (a) J5 wave route jobs rep pva4376595 (0d6487d7a8c6 intel1) + backups pvd2159f4a (4e4323c4d5b1), pva2793873 (3283f16cae2b), pv11b73b67 (64e24c10ad78), all DRT; check with intel2 bash -s jobstate.sh pattern (state.json jobs[id].kind/history). (b) bind1 (gate A, no xo) running intel1 bind_otrun.log; (c) bind2 (seg405+xalign+xo) queued intel1 bind2_otrun.log; (d) hub chain2.sh pid on intel2 (fam-s81-col-h9r0/chain2.log) -> run-item wave/spec.json (event famh9r0s2) to place/geom.
- Next for R2: read bind1/bind2 RC lines (BIND/LATCHECK/G0_BASE vs G0_NEW: compare new findings); TOKEN-1121 answer on xo +3; after chain2 place PASS, route the private kit (ot-run run_kit.sh GOAL=route, intel1/epyc10/epyc7/epyc8, not epyc9); on any wave rep signing: export + credit siblings + relaunch with fix= keys when J7 lands.
