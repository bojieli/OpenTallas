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
