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
