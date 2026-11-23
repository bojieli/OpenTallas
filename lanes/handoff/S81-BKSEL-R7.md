# S81-BKSEL-R7 handoff (Claude Opus; successor of S81-BKSEL-R6; started 2026-11-21 11:2x PST)

## State
- R6 try 4 (oth-ubuntu-3077726) ended at ENV-PROVENANCE preflight (rc 14, no flow). lef_override (DRT-0073, main 8d1cff9b1b) confirmed applied in its gen.
- Sign-off kit try 5 = proper private-spec kit: spec ~/coord/autopilot/private_specs/S81-BKSEL-R7/s81_bk_sel__t2_1121112702/spec.json
  (plan tree_r6 plan_h2_2249.json 84af570f = chain_r6 bound plan, tree/bind /srv/opentallas-scratch2/claude/s81-bksel-r5/w/tree_r6 (epyc7), src_manifest off, rt c54a7596fc81 (has override)).
  run-item on intel2, log ~/s81-bksel-r7/run_item1.log; work epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/S81-BKSEL-R7/bk_sel__t2_1121112702.
  run-item goes to place+geom; then route -> sign-off via the kit's run_kit.sh route (ENV-PROVENANCE then passes).
- J7: v7 plan (355ae5b4) carried none of the bk_sel work. GEN step handed to S81-J6-ASSEMBLY-R4 (post 11:4x):
  GEN bksel_r6 python3 -I -B /srv/opentallas-scratch2/claude/s81-bksel-r7/j7/bksel_r6.py {IN} {OUT} /srv/opentallas-scratch2/claude/s81-bksel-r7/j7/bksel_r6_rows.json (epyc10).
  Tested on v7/out/plan.json -> BKSEL_R6_OK. Keeps J7 taps / landing_contract / band_fixed_um / landing_local_resets / reset_tree_anchor; drops R6 landing_writer_start (J7 fstart_2 serves flt_o0).
  Sources: epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r7/w (mkrows.py, bksel_r6.py, cmp*.py, j7v7_bksel.json test output). Awaiting J6-R4 ack.
- Family: S81 bk_sel family = bk_sel__t2 only (siblings: none on the current plan found in OWNERS-SWEEP).
- 12:03 J6-R4 ACK: GEN bksel_r6 is a step in J7 plan v8/v9 (candJ7d gate on rt 8d1cff9b1bb6 proves it; J6-R4 posts result).
- 12:5x COORD ask (dsdv_idx_tx_n32 rst DRT-0073, FLOW-OBS-GCELL-R2): only bk_sel__t2 binds it. In-context DRT pin_access on try-3 4_cts.odb: no u_tx/rst error (308 unique insts); plan snaps u_tx MX y to 475.188 so rst lands on track. No re-export unless try 5 GRT shows it. Evidence epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r7/w/pa/pa.log.
- try 5 place (wave place service) since 12:01. Waiter: poll ~/s81-bksel-r7/run_item1.log / spec result.json.

## 18:xx after RESUME (weekly limit 13:4x; Codex 14:23-18:1x)
- try 5 route unit oth-ubuntu-3722601 ended 16:15: FAIL GRT-0116 (16,786 overflow, 85% vertical, x2250-2450 y350-450). No DRT/sign-off. Kit: epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/S81-BKSEL-R7/bk_sel__t2_1121112702 (route_r7.log, run/reports/.../congestion.rpt, geom/geom.tsv).
- Root cause: ~11.6k channel station relay_sites on one y line (388.8/389/395, x1645-2700) -> placed 6,949 cells in y390-400 over x2250-2450 at u_g N pins; rows 400-475 empty.
- Fix r7a: epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r7/w/plan_r7a.json (sha dfd669b1), spread.py K=10 DY=4.32 Y0=386 (bit lanes, reset relays excluded, 11,583 sites moved, max |dy| 40.7). 0 cycle change; lane totals = R6.
- Codex adopted: u_g -12.96 um audit (intel2 tap-grid-r4/bksel_j7_ug/out/ug_phase_audit.json) = optional, needs bind; not used in r7a.
- J7: preferred a6771d121e95 carries bk_sel R6 rows + R6 taps (BIND+LAT873+PRE PASS). r7a positions go to J8 once proven (GEN: apply the same spread to bk_sel__t2 relay_sites).
- BLOCKED: fleet drain; private-spec refuses epyc7. Auto-launcher (my session) intel2 ~/s81-bksel-r7/launch_r7a.sh, log launch_r7a.log: makes the r7a spec + run-item when epyc7 admits. Successor: re-run it if my session is gone. After place: hop300 scan (R4 hop300.py) + geom, then run_kit route 48 16 via ot-run in the kit work dir.

## 18:4x COORD ruling applied
- tree_r6 plain copy (rsync -a, no link-dest/delete) epyc7 -> intel2 /srv/opentallas-scratch2/claude/s81-bksel-r7/tree_r6 (+ w/plan_r7a.json, w/spread.py) via ot-run --hosts localhost on intel2 (script w/copy_tree.sh; plan_r7a.json appears last = copy done).
- Launcher (detached nohup, intel2 pid 483341): ~/s81-bksel-r7/launch_r7a.sh, log launch_r7a.log; every 5 min tries private-spec on intel2 (after copy) then epyc7; on success runs run-item (log ~/s81-bksel-r7/run_item_r7a.log). Old launcher killed.
- J8 candidate row (PROOF-PENDING) posted to S81-J6-ASSEMBLY-R5: lanes/handoff/S81-BKSEL-R7-J8-rows.json; GEN spread.py {IN} {OUT} 10 4.32 386.0.
- Next after place: hop300 scan (R4 /srv/opentallas-scratch2/claude/opus-fix-s81-bksel-r4/hop300.py on the geom.tsv), then ot-run route (run_kit.sh KIT route 48 16) in the kit work dir; read final 5_1_grt.odb / signoff.json; post to J6-R5.

## 20:3x
- intel2 fallback copy cancelled (oth-ubuntu-315702) + partial tree ot-deleted per COORD 18:5x.
- r7a spec ~/coord/autopilot/private_specs/S81-BKSEL-R7/s81_bk_sel__t2_1121185210 (epyc7, rt 18a2688b741f): gen OK, gen_lint killed rc 143 after 4479 s -> run-item FAIL. Cause: epyc7 docker hung (trivial docker run > 60 s; ~25 lanes' docker stages stuck).
- Detached retry: intel2 pid 584384 ~/s81-bksel-r7/retry_r7a.sh (log retry_r7a.log): reruns run-item on the same spec after 2 consecutive docker runs < 15 s; output ~/s81-bksel-r7/run_item_r7a_2.log. Successor: check it; then hop300 + route as above.

## 20:4x COORD: relaunch moves to epyc10 via FAM-S81-COL-R6
- My retry (intel2 pid 584384) killed (cmdline checked; no run-item started). COL-R6 copies tree_r6 to epyc10 (unit oth-ubuntu-1521480-1795321728) and relaunches the r7a spec there. Asked COL-R6 (post 20:4x) to carry plan_r7a.json and post spec/work dir.
- Mine after place on epyc10: hop300 scan, run_kit route 48 16 (ot-run, kit work dir), sign-off read, J8 row result to S81-J6-ASSEMBLY-R5.

## 21:1x COL-R6 ended -> I own the epyc10 relaunch
- Copy unit oth-ubuntu-1521480-1795321728 (COL-R6 script /srv/opentallas-scratch2/claude/fam-s81-col-r6/copy_e10.sh) copies tree_r6 to epyc10 SAME path /srv/opentallas-scratch2/claude/s81-bksel-r5/w/tree_r6 + plan_r7a to /srv/opentallas-scratch2/claude/s81-bksel-r7/w/ (31/54 GB at 21:08).
- Detached intel2 pid 2476582 ~/s81-bksel-r7/launch_e10.sh (log launch_e10.log): ot-wait copy -> verify -> private-spec --host epyc10 --goal auto -> run-item (log ~/s81-bksel-r7/run_item_e10.log). goal auto = through route/sign-off.
- hop300: epyc10 /srv/opentallas-scratch2/claude/s81-bksel-r7/w/hop300.py <rt/current> <kit geom/geom.tsv> 300 <out.json> (via ot-run) once 3_place + geom exist.

## 22:1x
- My duplicate epyc10 launch (pid 2476582 + run-item 223174, spec S81-BKSEL-R7/s81_bk_sel__t2_1121215915) killed per COORD; it only reached kit_rtl.
- r7a proof = COL-R6 run: spec ~/coord/autopilot/private_specs/FAM-S81-COL-R6/s81_bk_sel__t2_1121220051, work epyc10 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/FAM-S81-COL-R6/bk_sel__t2_1121220031, run-item intel2 pid 281955 (tied to COL-R6's ssh session).
- Guard (detached setsid, intel2 pid 462774, ~/s81-bksel-r7/guard_e10.sh, log guard_e10.log): when 281955 exits without result.json, resumes the same spec (max 3 tries).
- J8 row 2 READY: bksel_seatmiss.py (drop 575 seat-miss keys; all co-located with seated keys), posted to J6-R5; rows file updated.
- Next: on 3_place: hop300 (epyc10 w/hop300.py with rt/current on kit geom/geom.tsv) + check placed y-spread at x2250-2450; then route result (spec is goal auto? COL-R6 spec: check), sign-off -> J8 row 1 status.

## 23:1x r7a PLACED (epyc10, COL-R6 spec)
- 3_place.odb 07:01 UTC. hop300 (w/hop300_r7a.json): 0 groups >405 except known R2R_MAX 1202.5 u_rrl_11 -> u_cland_fstart_flt_o0 (unchanged since R4). Non-reset >300: u_sel.u_stn_s.g_r chain 78 caps max 314.7, u_sel.u_rn rsreg->o 54 caps 313.7 (both <405; R6 had only u_ids.vr->lo 303.4). Reset relays u_rrl 300-383.
- Hot window x2250-2450 placed y: cells now spread y380-430 (3138/2576/1765/2035/1728 per 10 um) instead of a single line stack.
- Geom GRT running (spec geom.live.log); goal auto continues to route. Waiter on my session.

## 11-22 03:xx RESUMED after the weekly limit
- r7a proof (COL-R6 spec) ended 02:19: route FAIL_POSTCTS at GRT TT gate. GRT overflow 323 (try5 16,786) -> J8 row 1 spread PROVEN for congestion.
- STA breakdown (epyc10 s81-bksel-r7/w/bksel_ids: viol_tt.tsv, sta_path.log, sta_r01.log, sta_mac.log; scripts sta_*.tcl/sh, docker openroad full path /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad):
  4,876 eps g_q -> u_stn_s/o r[0] -337/-362 (quarter eco3 view OLL 2 negedge out-face; core tap padded 262 ps by tap_balance tb0 chain), 463 u_ids to -1928, 110 u_c->u_stn_c -62, u_g +/-65, fstart -406.
  Per-core window: g_q OUT -251..-362, IN +217..+286 -> no clock-only fix. NEG0 r0->r1 half-cycle -72/-57/-46.
- Posted BLOCKER with options A (re-sign bksel_q OLL 0), B (+1 stage; t_s/t_c blocked: u_c XDX uses RS/RC), C (NEG0 + quarter clock ~100 ps early + r[0] re-site). Default A at 05:00 if no ruling.
- RTL candidates (epyc10 w/bksel_ids): selids_A/B.sv (u_ids remaining-count; B + cnt/pre registered from vo[99:84]), dsdv_bk_sel_neg0.sv (dsdv_bk_stn NEG0, define OT_BKSEL_NEG0, inert unless set). Sim PASS (tb3 23,607 x3 MUT; tb_stn 1,990). Formal BMC/induction yosys running (eq_*.log).
- Private fork tree_ids (ot-tree-fork of tree_r6, 53.7 GB) patched: dsdv_bk_sel.sv eb490a6c, portfix178 dsdv_idx_l20s.sv 5716d3de. plan_r7b.json (8e55cee7) = r7a + row3 fstart + OT_BKSEL_NEG0. Strict elab/bind/LATCHECK/PRE running (bind_r7b.sh, log w/bind_r7b/).

## 11-22 03:1x COORD ruling A + C executing
- A (core re-sign OLL 0): kit epyc2 /srv/opentallas-scratch2/claude/s81-bksel-r7/coreA/bksel_q_oll0 = copy of signed base kit
  fable-fix-bksel/fx6/bksel_vC9fx6 (eco3 base form) minus run/, VERILOG_TOP_PARAMS OLL 0 RFH 2 HLAT 1; gate tools
  (signoff/lec/sdc_lint/rtl_lint/legacy_gate/pin_audit/lec_async/kit_modes) from rt 787530142d79; stale lec_async identity
  moved to s81-bksel-r7/tmp/coreA_stale. ot-run unit oth-ubuntu-788310-1795345327 (epyc2, 72G), log intel2
  ~/s81-bksel-r7-logs/coreA.otrun.log; run_kit.sh finish 64 16 -> signoff/signoff.json. fx6 GRT took ~10 h; a hold-only
  route-keep ECO (fx6/hei_fable/run_hei_fable.sh) may be needed after route. Then export view + plan row (row4).
- C: plan_r7c.json (epyc10 w/, sha dd0f05d4123ba8ae, mk_r7c.py) = r7b + quarter core tap insertion 750.69 -> 587
  (early 137) + clock.core_tap_direct + u_stn_s/o/c r[0] relay sites min(120 um, half hop) toward r[1].
  Bind: bksel_ids/bind_r7c.sh via ot-run epyc10 (r7b bind cancelled: r7c supersedes it), logs w/bind_r7c/.
  Next: private-spec s81 bk_sel__t2 --plan plan_r7c --tree tree_ids --bind-out <tree_ids native_bind/out> --goal finish.
- J8 rows 1-3 READY (posted 03:1x).
- 04:2x C launched: plan_r7c sha e18e5ce80896fce0 (core_tap_direct key dropped: tree_ids schema refuses it; same switch as
  gen env OT_TAP_CORE_DIRECT=1 via --ab). bind_r7c GREEN (ELAB 0, BIND 0 errors 0, LATCHECK PASS 873/873, PRE_PASS).
  spec ~/coord/autopilot/private_specs/S81-BKSEL-R7/s81_bk_sel__t2_1122042135, run-item pid 1685261 on intel2, log
  ~/s81-bksel-r7-logs/r7c_runitem.log, work epyc10 .../kit-wave/s81/18a2688b741/private/S81-BKSEL-R7/bk_sel__t2_1122042103.
- u_ids formal: EQUIVALENT by strengthened 1-induction (epyc10 w/bksel_ids/inv_B.{sv,ys,log}, xo.sv/xb.sv).

## 11-22 08:3x state (resume here)
- main 5b1b2e8b5f9 PUSHED: portfix178 dsdv_idx_l20s.sv u_ids-B (formal EQUIVALENT, strengthened 1-induction,
  epyc10 w/bksel_ids/inv_B.{sv,ys,log} + xo.sv/xb.sv) + dsdv_bk_sel.sv define OT_BKSEL_NEG0 (default off). Lane clone epyc7
  s81-bksel-r7/repo (sparse).
- C (evidence, unsealed): spec ~/coord/autopilot/private_specs/S81-BKSEL-R7/s81_bk_sel__t2_1122054404 (goal auto; goal finish
  is broken: KWRS stage resume refuses finish), run-item log ~/s81-bksel-r7-logs/r7c3_runitem.log, work epyc10
  .../private/S81-BKSEL-R7/bk_sel__t2_1122054328. Place done, geom FAIL advisory (same class as r7a, r2r fixed), CTS queued
  for CPU admission on epyc10/epyc8 since 07:23. Next read: FAIL_POSTCTS / postcts_gate_TT.log, OT_TAP_CORE lines (quarter
  pins should read ~-137 pin, no clk_c0..3 pad), then 5_1_grt.
- Sealed C on die src 3c913db: bind refuses (svc_hi_dsdv_svc_pvso_entry__t1 dead-input proof not in manifest; src lacks L4).
  Ruled: countable build = J8 wave kit on main >= 5b1b2e8b5f9. tree_sealed in w/ is ot-delete-protected.
- A: epyc2 coreA kit, GRT FF hold repair: outputs done, internal macro pins (u_hc g_bank i_en) ~-12 ps at 07:3x.
  After route: signoff/signoff.json; if FF hold short, hold-only route-keep ECO per fx6/hei_fable/run_hei_fable.sh.
- 08:4x COORD ack: C rt 2bc14507b4dc contains 36d0a6df8f6 (chain runs "goal route attempt 1"); new private kits use explicit --goal route.
  Row 4 goes to J6-R5 as soon as A or C gives the answer (pre-routed evidence OK). DISK for EPYC10-DISK after C ends:
  epyc10 /srv/opentallas-scratch2/claude/s81-bksel-r7/w/tree_sealed (54 GB, unused sealed fork) - reclaim via ot-delete; do not touch before C ends.
- 17:3x RESUMED after weekly limit. Landed while down: A routed (E2 6_final; Codex recovery fork coreA/signoff_recovery_codex, missing helper modules) -> signoff NOT SIGNED only on FF hold -0.77 ps (TT setup -2.98 info, pin audit 1803/1803). One-endpoint hold-only route-keep ECO (one_hold_pad, u_q.sqd[373]) running on epyc2 since 17:25 -> signoff in one_hold_pad/signoff.
  C: CTS rc0 (quarter taps pin -49, effective 463-465 vs target 450 OK; no pad), GRT running on epyc10 since 16:32.
  J8 cut 16:00 shipped BKSEL1-3 without row 4; row 4 now goes to J9 via S81-J6-ASSEMBLY-R5.
- 21:0x C ENDED, unsignable: GRT-0116 congestion (total ovfl 1039, M3 431/M5 230/M7 227; render GRT max 116%, 75436 gcells >90%),
  post-CTS TT setup -372.45 after repair (stalled at -270), FF hold -256. Worst post-CTS: async reset recovery u_bound.u_rrl_30 -> u_ids.b1[*] RESETN
  (one INVx3 drives 199 sinks, 1.1 ns wire). Kit epyc10 .../private/S81-BKSEL-R7/bk_sel__t2_1122054328 (spec s81_bk_sel__t2_1122054404). C closed; row 4 = A.
  DISK RELEASE for EPYC10-DISK (ot-delete): epyc10 /srv/opentallas-scratch2/claude/s81-bksel-r7/w/tree_sealed (54 GB) and the C kit dir above.
