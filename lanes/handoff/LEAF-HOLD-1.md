# LEAF-HOLD-1 handoff (S81 leaf hold family; COORD lane) -- started 2026-11-13 ~18:35 PST

## Scope
- S81 leaf hold family: ot_s81sl_leaf__t6 a4 (OT_HOLD_STRUCTURAL at GRT, -87.5 / 7,919) and ot_s81sl_kv_leaf__t5 a7
  (GRT time cap, hold -227.8). COORD 18:4x: do not re-diagnose. Check S81-FORMS-1's 10:31 STATE, scan the family, prove
  leaf__t6 privately with core_tap_fix + tap cap, and land the fix in the S81-FORMS-1 leaf event (not a separate event).
- Rules: DO_NOT_COUNT private, no wave changes, plan freeze until 11-15 04:00, nothing on epyc9.

## Diagnosis (STATE posted, on origin)
- A CORE-TAP REACH (R-CLOCK-5): 21 of 22 CTS-reached ot_s81sl_leaf kits of event 7073a6b4a59 (all except t2) have 15-23 ln core
  taps late (effective 543-789 ps vs 250). t6: 20/27 pins late, worst g_ln[9] 601 ps; cts_final worst hold -309.5 into the ln ROM.
- B POCKET TAP OVERLOAD: kv_leaf t5 (clk_t5 11,278 sinks) and kv_leaf t4 (8,954); leaf t29 3,667. kv_leaf core taps are on target.
- C port-out vclk boundary (t6 ft0_o[258] -121.5): open list.
- Scan table: epyc7 /srv/opentallas-scratch2/claude/leaf-hold-1/leafscan2.tsv (scanner: same dir, leafscan2.py).

## Proof build (private)
- epyc7 /srv/opentallas-scratch2/claude/leaf-hold-1/
  - plan/p2.json (dd5b131bceef) = the wave plan 18c864518844 + S81-FORMS-1 core_tap_fix.py (t6 only: 15 taps, worst 772 -> 11.8 um)
    + tapcap.py 1500 (t6 only).
  - src/ = symlink farm of kw45/src_s81_main_7073a6b4a5. It has its own physical/die_plan/s81/plan_h2_2249.json (= p2.json).
  - t6p1/ = work dir. rtl/ + plandir/ are copied from wave a4 (paths rewritten), gen.sh = the wave gen command, gen/ = the kit.
- Launch logs: intel2 ~/lh1/*.log (ot-run clients).
- Gen ran 2026-11-13 ~18:50-19:2x (GEN_RC 0). The kit has OT_TAP_MAX_SINKS 1500. core_taps.txt now gives the 16 ln taps early 0 (before: pin legs up to 341 ps).
- Route run: intel2 ot-run client (log ~/lh1/route.log) -> epyc7, `run_kit.sh K route 48 8`. Compare to a4: post-CTS FF gate
  -287.5/7,266, OT_TAP_CORE 20/27 late, GRT -245.6/8,712 -> OT_HOLD_STALL -87.5/7,919.

## Next
1. Read 4_1_cts.log OT_TAP_CORE + hold gate, then 5_1_grt.log OT_HOLD_GUARD_GRT. On route: the 6_* reports.
2. RESULT/READY to the queue (cc S81-FORMS-1, HOLD-TAP-1). The fix lands in the S81-FORMS-1 leaf event (leaf_post.sh already runs
   core_tap_fix + tapcap 1500). Ask S81-FORMS-1 to add kv_leaf t4 to the pocket list.

## 2026-11-13 12:25 PST update
- p1 (core_tap_fix + cap 1500): CTS gives OT_TAP_CORE 7/27 outside +-20 (was 20/27). The ln taps are at 260-274 ps, except ln_7 at 323
  (its pin leg is 63 ps; the tap was under the 50 um far threshold). Post-CTS FF gate PASS -150.60/7,143 (a4: INFO -287.54/7,266).
  clk_t8 keeps 1,584 sinks ('no tap with room within 200 um').
- Bucket STA (hold_gate.tcl context; all violators dumped): epyc7 leaf-hold-1/{a4ref,t6p1}/bucket/k/lh1_hold_viol.tsv; cls.py.
  a4: reg->lane ROM 1,181 (ws -287.5); reg->reg 3,616 (-125); vclk ports 1,473 in + 493 out; vsw 321; sram 131. <-200: 64.
  p1: lane ROM 1 (-0.5); reg->reg 4,570 (-150.6, zero-logic cland/ft/leafdn pad chains = cross-tap); ports unchanged; <-200: 0.
- R-CLOCK-1 hold build (train-44 pregrt_ff_hold.py from epyc7 wt/die-kv-100, guard 45) standalone on the p1 4_cts.odb copy
  (t6p1/hbuild): class before: port_in 1,473 ws -60.9 / same_tap 82 ws -80.4 / cross_tap 5,095 ws -150.6 / port_out 493 ws -18.0.
  After: 0/0/0/0, wns +4.34, cross-tap +45.0. 17,350 hold cells (5.9% of 296k insts), TT setup -360.6 unchanged, 1,708 s,
  open list empty.
- p2 = p1 kit + that hold-built 4_cts.odb, resume.json start=grt, run_kit route (intel2 ~/lh1/route_p2.log).
  The post-CTS gate re-ran: PASS +4.34/0. GRT running since 20:22 UTC.
- p1 GRT (no hold build) still running as the comparison arm (intel2 ~/lh1/route.log).
- NOTE: t6 has TT setup WNS -360.6 at CTS (a4 cts_final -329.8: grid FF -> SRAM u_vp.u_b0 w_mask, ~1 ns of logic). That is a
  separate R-RTL/setup item. The hold fix does not touch it.

## CODEX handoff 2026-11-13 17:15 PST

CLAUDE BACK; new launches stopped, active jobs preserved. Complete exact S81 frame/leaf source, geometry, jobs, failures and next-step packet: `~/coord/handoff/codex_s81_to_claude_20261113_1715.md`. Keyterminal: joint216refloor32244.48x25980.48/0conflicts/checkclean (geometry-only); freshleafstrictbind+873/873latPASS; K52/K72actualKI source materializationPASS, mapped synth/clock/P&R stillpending. ProvideraliascurrentTT TIMING HOLD/RC2notbuilt; fullvectorreset/sourcegraph/softsites remain gated. Descendant lane-specific records appended separately.
