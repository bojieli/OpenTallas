# FABLE-FIX-KV-PV handoff, status 2026-11-19 16:25Z (newest first; SUPERSEDES the 13:40Z and 12:55Z sections below)
## One timing-only kv3_pv_v8 proof kit RUNNING. All private die binds RED (4 pv errors fixed on main, 2 hgi_v1 errors are in the control too). No TT number.
- Private trees epyc7 + epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/compose/: tree2 dense 300-um +843 (plan 3e5f74e1cf88),
  tree3 route-priced +500 (6f99ce9d8336, bound only), tree4 = D25e form from cbc-rules kv_pv_p2p.json, 128 lanes +464, astk lanes 0,
  pads 10/10, V-D-H 0 (a04c96f9ee3a). All PRE + G0 0 errors vs D25c. tree4 G0 has +32 hop>405 warnings from the file counts.
- Binds: tree2 and tree4 RED with 6 EMIT: 4 pv "reset relay rst_n_t<N> not found" (v2, v5n, v6n, v7) = emitter gap of
  reset.consumer_sites_um, FIXED on main 83494dde2c1 (lane clone epyc10 fable-fix-kv-pv-resetkey); 2 kv3_hgi_v1 raw Q errors = same as
  the D25c control (not ours; fix = d25d4 with FABLE-FIX-KV-HG / KV-D23-COMPOSE). R8 FAIL = control baseline, line-identical.
  LATCHECK cannot run on any KV bind until the hgi_v1 errors are gone.
- Kit v8b (dense form), TIMING-ONLY, die bind RED: ot-run unit oth-ubuntu-796442-1795105396 on epyc8, --priority proof, goal grt, kit dir
  compose/kit/v8b/gen/kv3_pv_v8 (written files return to epyc10), client log intel2 ~/tmp/ffkpv/compose/kit_v8b.log. Built from a
  PRIVATE bind copy (error list emptied, stub bound top) because the component-proof path refuses a red bind.
- Kit v8d (tree4, D25e form): kit-rtl running on epyc10 since 16:19:59Z, launches by itself.
- Rebind of tree4 with 83494dde2c1 ported: epyc10, gate compose/bindgate4b, since 16:19:59Z; expect 2 hgi_v1 errors left.
- Read results only from tt_setup_measure logs, 4_cts_post_hook.rpt, 5_global_route.tt.rpt; read GRT markers near cl_ft0_i (1978-2160, 237-432).
- Handover pack compose/pack (tree4 form) is NOT to be taken yet: G0-clean, not bind-clean, unproved. T/C/D tool patch not on main.
- Next: rebase the D25e form on d25d4 when live; rebind; LATCHECK; hand over; push T/C/D patch; then family kits, sign-off, export.

# FABLE-FIX-KV-PV handoff, status 2026-11-19 13:40Z (newest first; SUPERSEDES the 12:55Z section below: tree/plan 85a1a20ea9b7 is dead)
## Proof tree = compose/tree2 (reset.consumer_sites_um form). PRE + G0 PASS. Bind RUNNING. Kit NOT started. No TT number.
- epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/compose/tree2: plan 3e5f74e1cf88, asbuilt 044908412a29, built from live D25c
  by compose/compose_rows.py (B, T, C, D, E, A). Tools = D25c b3c4d97 + 5 files of main b7b2095a5066 + T/C/D patch.
- G0 0 errors, 2447 warnings (control 0 / 2446): +1 cl_ft0_i lattice (B), +1 pvfin ck depth (E), -1 v8 R-CAP NEAR. R-REACH-5 7 = control 7.
- Reset tree identical to D25c on kv3_pv, v1, v12, v2, v5n, v6n, v7; kv3_pv_v8 931 relays vs 928 (class B only).
- Strict bind + LATCHECK: ot-run unit oth-ubuntu-423522-1795094078 on epyc7, started 13:14:40Z, 2.5-3 h. Gate file
  compose/bindgate2/gate.out (ALL_DONE = finished), out compose/bind2.
- Kit chain: intel2 ~/tmp/ffkpv/compose/chain_kit.sh v8b (log chain_kit_v8b.log): on RC_BIND 0 + BIND_ERRORS 0 + RC_LATCHECK 0 it runs
  kit-rtl -> gen -> ot-run --priority proof kv3_pv_v8 to GRT. If LATCHECK is non-zero (possible C3 INTERNAL_PIPE_UNACKED warning) the
  chain does NOT start the kit: read gate.out and decide.
- First tree (compose/tree, hand re-indexed taps): bind cancelled 13:14Z, files kept, do not use.
- Handover for KV-D23-COMPOSE: compose/HANDOVER.md + compose/pack (UNPROVED). --zero-cycle = B, T, C inject sites, D sites, E, A (0 lanes move).
  Cycle rows PROVISIONAL (132 lanes +843; D pad lifts TRUNK_D 74->86, FLAG_D 78->86): compose/cycle_rows.tsv.
- Open: V-pad table has an unexplained -5 residual on 488 members vs the table of record. Tool patch T/C/D not on main.
- After the kit: read tt_setup_measure / 4_cts_post_hook.rpt / 5_global_route.tt.rpt and GRT markers near cl_ft0_i (1978-2160, 237-432).

# FABLE-FIX-KV-PV handoff, status 2026-11-19 12:55Z (newest first; older sections below are history)
## Composed D25e pv rows: PRE + G0 PASS, bind running, kit NOT started
- Tree epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/compose/tree, built from fresh live D25c (plan 4a40f1dbe86d) by
  compose/compose_rows.py (order B, T, C, D, E, A; 3 passes to a fixed point). Composed plan 85a1a20ea9b7, asbuilt 5ec7f199462a.
  18 types change: 16 pv, kv3_hgi_v3 (sender pins of ft0_i + one raw branch), kv3_hub_C (pvfin lef/lib).
- PRE PASS 0 findings. G0 PASS 0 errors, 2447 warnings (control 0 / 2446): +1 cl_ft0_i y origin off the 8.64 lattice (B), +1 pvfin ck
  depth 275 ps no early tap (E, hub_C owner), -1 kv3_pv_v8 R-CAP NEAR.
- Class T defect found by G0 and fixed ONLY in compose_rows.py (added taps shift reset tap indices): never apply rows/T standalone.
- Cycles, ALL PROVISIONAL (owner rule: no +cycle from distance alone; CBC-RULES-1119 recounts): 132 lanes +843 (128 join status lanes
  +812, 4 astk response lanes +31), plus D pad-table lifts cmd +12 / pe2 up to +11. List compose/cycle_rows.tsv.
  0-cycle set: compose_rows.py --zero-cycle (B, T, C inject sites, D sites, E, A); moves 0 lanes on fresh D25c (in-memory check only).
- Running: R8 prepass since 12:14Z -> pad tables -> strict bind + LATCHECK (2.5-3 h) -> kit-rtl -> private kv3_pv_v8 kit, ot-run
  --priority proof, launched by a chain armed by the compose worker. The kit needs bind_of_record (bind_report.json + bound wrapper RTL).
- Also ready, unproved in a kit: rows/E (pvfin views, kv3_hub_C), rows/E2 (qkd_kvs_pcc/pcf + _h_head_p views, 48 rows, six kv3_pc types;
  3 of 4 fail child_lint face-pin access, bound anyway as advisory).
- Not done: bind verdict, LATCHECK, any TT number, HANDOVER.md, tool patch push to main, sign-off, export.

# FABLE-FIX-KV-PV handoff addendum 2026-11-19 (newest first; diagnosis section follows)
## D25e CBC rows: where they stand (nothing composed, bound or proved yet)
Worker outputs epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/rows/<CLASS>/{rows.py,NOTES.md[,tools.patch]}; brief CONTEXT.md.
- A landing control: READY. clock.landing_raw_branches on kv3_pv + kv3_pv_v8 only (the other 14 pv types already have it), 10 branches
  each, 48/46 flops, max hop 318/324 um, 0 cycles. Emitter validation passes on bound wrappers. APPLY LAST (names depend on final taps).
- B ft0_i hard ring child: worker waiting on its G0 comparison. No result yet.
- C core/child output stations: worker waiting on G0 runs + join RTL lookup. No result yet.
- D core inputs: READY with caveat. tools.patch (9 files: tail split K from routed run, pad generators --min-pad, pad_reach_census.py),
  rows site u_bin flops. Command +12 cycles on all 64 columns, pe2 up to +11. Pad tables NOT regenerated; hub re-kit + compiler
  constants not done. Apply after C.
- T tap split from placed flops (target 1000/tap): worker running. No result yet.
- E pvfin views (fail class a11df238f3): cause = kv3_hub_C pvfin_lo/hi rows have no lef/lib, so kv_core_wave lists the SIGNED core
  qkd_pv_fin_s8_pin (signed-export-1114, ARCHIVED-BOTH-NO-VIEWPACK) as a core to harden with no recipe. Fix = view pack from the signed
  DB + lef/lib keys. Worker started; rows/E.
Compose order: T, B, C, D, E, A. Then one bind, one private kv3_pv_v8 kit to GRT TT (r712), then hand to KV-D23-COMPOSE.

# FABLE-FIX-KV-PV handoff (KV pv family owner; restarted 2026-11-19 01:0x PST; the 11-15 section below is history)

## Status 2026-11-19 01:45 PST (read this first)
Diagnosis of the D23H kv3_pv / kv3_pv_v8 TT setup (-2028 / -1703 ps) is DONE. It is NOT the clock: worst-path tap latencies are
211-260 ps at both ends. It is unpipelined data crossing the 2160 x 1520 um outline in one cycle.
Evidence (read-only STA on each kit's 4_cts_pre_tt.odb, same frame as tt_setup_repair.tcl): epyc7
/srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/out_{v8,pv}/{paths.tsv,worst3.rpt,diag.log}; script diag/diag.tcl; launcher
intel2 ~/tmp/ffkpv/diag.sh. NOTE paths.tsv columns "start"/"end" are swapped (start = endpoint pin, end = launch clock port) and
wire_um/depth include the launch clock path.
Classes (v8 endpoints below -42: 6012; pv: 1093):
 A cland control: u_cland_rst_ft0_i/q (at 2082,1420) -> u_cland_origin (175,7), tstart_o, raw_reset_o, fstart_* : 17 endpoints,
   -700..-2028, 2.2-3.3 mm of repeated wire, 50 buffers, fanout <= 12. Missing stations.
 B soft ft0_i landing ring (w1057, E face, pins y 370-475): 4228 endpoints fclk_in_ft0_i half-cycle, -200..-481, pin->flop data
   ~980 ps (v8). ft5_i already uses the hard child kv_cland_w1057_ns_94a44.
 C core/child outputs to far flops: bout o_pvw__u_sN_j_y_valid/fault 2.1-2.8 mm (-340..-1129); astk owner_response cland child ->
   u_bin 1.8 mm (129 endpoints, -531); pv u_pv_u_T?Q?_r.b[] 972 endpoints -278.
 D core input buses u_pvgN_pN/s*__bc, bcx, pe: 396 endpoints to -891, 2.5 mm, fanout 36; tail copies u_pd1 ctl_cmd 45 at -381
   (OT_TAIL_SITE over_380 1474, max hop 870 um).
 E async rst_n recovery -150 (port ri_pv_u_gN_j_rst_n -> relay flop, 900 ps of buffers).
Tap load from the kits' real counts (OT_CLOCK_TAPS per-tap sinks, cap 1200): kv3_pv 141,055 sinks, 17 taps over, +39 taps;
kv3_pv_v8 132,571, 10 over, +28 (root tap clk holds 10,056, missed by the earlier row); kv3_pv_v1 146,805, 16 over, +23;
kv3_pv_v2 165,403, 11 over, +30. v12 not at CTS; v3n, v1n, v2n, v3, kv3_io_cor: no route job on epyc7, unverified.
Tap split fixes CTS run time (4 h) and hold classes only; it does not move the setup number.

## Not done
No fix composed, no private proof kit, no sign-off, no export. Rows posted to KV-D23-COMPOSE are requirements, not sited rows.

## Next
1. A: bind/compiler: relay stations on the cland rst -> origin/start/raw_reset fan (9 stages for 3.3 mm at 380 um) or re-site
   u_cland_origin next to the ft0_i ring; extra cycles are pre-approved, check the START latency contract (LATCHECK).
2. B: make ft0_i a hard ring child (cland_w1057_ew_94a44 is signed and archived) in all pv types.
3. C/D: stations on the long core-out / core-in lanes (plan lanes, 380 um hop), fanout tree for bc/bcx/pe.
4. Tap split rows from real counts; then one private kv3_pv_v8 kit to GRT TT (r712), then D25e rows.
5. Rerun diag.sh on v1/v2/v12 4_cts_pre_tt.odb when they finish CTS to confirm the same classes.

---
# FABLE-FIX-KV-PV handoff (owner of the KV pv + hg/hgi families to sign-off; started 2026-11-15 22:20 PST)

## Decisions (measured basis: epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-pv/cnt_{base,after}/cnt2.tsv)
- kv3_pv_v1n placed movable 635k (base) / 748k (D=3 pipes unsited): landing rings 186k, repeaters 211k / 362k, pad+pipe flops 68k / 124k.
- pv split = STEP 1 big landing rings (W>=250) as hard ring child cores on 7y, all 16 pv types (hg v23 recipe), then STEP 2 3-way x cut
  at 622.08 / 1537.92 (g0 | g1+g2 | g3) for what still measures over 400k. PVGEN 2-way is not composed.
- Commit trailer used: Co-Authored-By: Claude Fable 5.2.

## In flight (workers report to FABLE-FIX-KV-PV, they do not post)
- RING plan: epyc10 fable-fix-kv-pv/ring/ (hgsplit23 on kvgeom7y e64265095f85, 16 pv types, G0/bind/LATCHECK).
- CUT compiler: branch claude/fable-fix-kv-pv-cut-1116 (type_split second rstart tx pin + dead forwarded lane), epyc7 fable-fix-kv-pv-cut/.
- ECTLK q0/q1/q3 at 37/26 (KV-ECTLK-RL silent since 14:xx): <host> fable-fix-kv-pv-ectlk/, logs intel2 ~/tmp/ffk/ectlk/. q2 SIGNED (kv-q2-clk/b_fin).
- KV ring masters (CLAND-MACRO-1 rk kits, epyc2 + intel1): 23 relaunched 22:35-22:50 PST. Status: intel2 `bash ~/tmp/ffk/ring_status.sh`;
  waiter logs ~/tmp/ffk/ringlogs/<master>.log; scripts ~/tmp/ffk/ring_scan.sh (classify), ring_resume.sh (STB-EDGE-1 resume).
  Classes: 19 x STB-EDGE-1 (old subtree_balance.tcl) resumed from 4_cts; 3 x FACE_GUARD land_slot d[511] (w652, w653, w672) with the
  guard fix installed by copy+mv; w257_ew_69586 rebuilt from place. Not relaunched: w292_ew_abd47 (unused by hg v23 rows).
- face_guard fix: claude/fable-fix-kv-pv-fg-1116 @7549e748c78 (clone epyc9 fable-fix-kv-pv/repo); gate log intel2 ~/tmp/ffk/gate_fg.out.

## Next
1. Masters: on each SIGNED -> AUTO-RESIGN row + archive (AGIdock + rtx-pro) as OVERSIZE-1 did; a new failure class -> one class fix, relaunch.
2. hg: joint event is KV-HGSPLIT-1115 v25 (v24n bind failed: native stations L382 fixed_cycles = the 7v top-level lane rows missing) -> KV-102
   composes with 7uh. Needs: 16 ring masters signed (2 were), ectlk q0/q1/q3 37/26 signed. Then pilot kv3_hg_v3 through the wave.
3. pv: ring plan rows -> KV-102 (one pv delta on 7y); placed census of kv3_pv_v1n on it decides which types take the 3-way cut; pilot one piece.
