# OPUS-FIX-S81-LEAF-TAPHOLD-R2 handoff (Opus; succeeds FABLE-FIX-S81-LEAF-TAPHOLD, Fable 429 until 11-29; started 11-22 22:3x PST)
Pairs with OPUS-FIX-S81-LEAF-R10 (owns leaf GRTCONG, REACH, SRE-SRC). Rows go to S81-J6-ASSEMBLY-R5 (J9 cut 11-23 12:00, manifest lanes/handoff/S81-J9-MANIFEST-1123.txt).
Background: lanes/handoff/FABLE-FIX-S81-LEAF-TAPHOLD.md (measured cause, plan f, gate f, family rows).
Lane dir epyc7 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-taphold-r2 (R2). Predecessor dir L = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-taphold (probe scripts th_probe.sh / th_tt2.sh there).

## State 22:4x PST 11-22
- TAPHOLD A (t39 plan f) + B (79 types, hold_hb4 3 + pregrt guard 100) rode J8 cut v2 c67f4f6ba285 (S81-J8-INTAKE-1122.txt). NOT a kit proof yet.
- k1 (t39 plan f) ADOPTED: unit oth-ubuntu-973805-1795399191, ot-run client PID 422840 on epyc7, run_kit.sh route from placed DB.
  K = epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/FABLE-FIX-S81-LEAF-TAPHOLD/ot_s81sl_leaf__t39_1122071812/gen/ot_s81sl_leaf__t39
  - CTS read (predecessor 20:09): port_in 2,577 -> 3, cross_tap/same_tap/port_out 0 at +100 guard, 33,880 hold cells; TT after CTS repair -184 / TNS -925.
  - GRT 06:24 UTC: routed 0 overflow after 30/50 extra iterations (7017 s), 0 GRT-0273, 1 clock leaf net repeated. Prerepair saved 5_1_grt.prerepair.odb. Then repair_design (227k nets) + GRT hold repair.
  - NOTE: K/FAIL_PREFLOOR (stale, 17:24) makes `ot-wait --kit` report DIED at once: use the unit waiter.
- Waiters: epyc7 durable ot-wait unit -> ~/.local/state/ot-wait/durable/3dd1cec53a050288.out (R2/unit.wait); local background poll for 5_1_grt.odb.
- No other builds of this lane. k2 cancelled (predecessor); k2 dir + src_g cleanup owed (guard-protected).

## Next
1. On final 5_1_grt.odb: `ot-run --hosts epyc7 --dir L --stage K -- env TH_VCLK_MEAS=385.95 bash L/th_probe.sh K 5_1_grt.odb R2/probe_k1` + th_tt2.sh. Judge internal FF hold >= 0 and TT >= -42.
2. If TT is pad-limited: J9 row = guard 60-75 (pads + latches stand). Post to R5 / R10 / COORD.
3. Let route/finish continue to sign-off; LEC routed.

## State 23:4x PST (after limit outage, COORD resume)
- k1 unit still live. Attempt-1 post-GRT repair_design (max_wire 100) flat 1800 s -> OT_GRT_REPAIR_NO_PROGRESS 06:58 UTC: GRT re-run once in a fresh process with max-wire repair skipped (5_1_grt.repair_nostall.json). At 07:37 UTC in extra iteration 9/50. Waiters unchanged.
- If attempt 2 also stalls: flow row (OT_MAXWIRE off for leaf GRT) -> FLOW lane + R10, not a plan row.
- Fast-review rule f95aac4: self-review renders allowed; probes never wait for review.

## State 01:3x PST 11-23 (after 01:17 limit; Codex handoff: nothing for this lane)
- k1 final 5_1_grt.odb 09:18 UTC (attempt 2, max-wire repair skipped): 0 overflow, 0 DRV, 0 antenna. Flow GRT hold repair: ws +17.4, 0 violators. Post-GRT repair stall-stop at kit corner setup -573.9 / TNS -17,918 / 96 ends; hold -62.3 / 6 ends (corner unconfirmed). Kit now in tt_setup_repair.tcl (inside container dpkit-ot_s81sl_leaf__t39-1181364).
- Probes launched 09:3x UTC via ot-run epyc7, read-only: th_tt2 -> R2/tt_k1 (log R2/tt_k1.otrun.log, client PID 2797813); th_probe FF (TH_VCLK_MEAS 385.95) -> R2/probe_k1 (PID 2797814). Local background waiter armed.
- PROBE-PASS now needs a full-cause census (hub fe8a2a5): every overflow cluster + every failing path class with a row. Apply this to the t39 read.

## State 01:4x PST 11-23: GRT reads done (hub a7cbbbd GRT READ, next post HOLD READ)
- FF hold final 5_1_grt.odb: 6 < 0 = 4 port-only (spare ft3_i[595]/[596] -62, arst_n -46, cland_tstart_in -32) + 2 internal -2.5/-1.2 (u_vn_u_a hq_d -> vp driver_hqd_c_q). Hold rows PROVEN. probe tcl crashes at line 99 report_checks on port ft1_o[555] (census TSV already written).
- TT raw -892 / 250 ends = GRT attempt 2 skipped max-wire repair; kit tt_setup_repair_grt.log repair_design -> -283.8 / TNS -3,369, repair_timing running. Waiter bmrs735pl (local) on OT_TT_SETUP_REPAIR final line.
- TT classes (raw): u_vp cst_hi src->src (clk_t30->t25 etc., data delay), native_memory ly/lr/cf -> cst_hi, cst_ho -> driver_hw_d, lpad leafdn_i0 q -> u_rr reset (-295, ~1,000 um: the open no-row reset class), driver_wl_d -> ist_leafup_o0.
- Next: when TT repair ends, re-run th_tt2 on the newest ODB the kit writes; if TT > -42 fails -> rows: reset relay_split for lpad q -> u_rr, station for driver_wl_d -> ist_leafup (~450 um), guard lower only if hold cells sit on the failing paths.
