FLOW-HOLD-3/V2 2026-10-29 08:16 PDT -- calibrated GRT clock-leg RC for the q3 hold root cause (COORD 07:58, KV-KITS-21 b6e065553c).
Inputs (read-only): intel1 kv-kits-20-1029/q3_t2/kit (5_1_grt.odb, 6_final.odb/spef, route.guide, setRC_rcx.tcl = kit LAYER_PARASITICS_FILE, FF libs + golden.sdc).
Probe runs: intel1:/srv/opentallas-scratch2/claude/flow-hold-3-v2/p1 (docker diag, 16 GB cap). Scripts here: probe.tcl (per clock net stage/wire delay + all register CK arrivals,
est = 5_1_grt + setRC_rcx + estimate_parasitics -global_routing [+OT_RC], rcx = 6_final + RCX SPEF), wl.py (guide vs routed length per layer, clock nets), spef.py, cmp.py, m5.py.

VERDICT: V2 FAILS -- the GRT->routed clock gap on q3 is NOT a unit-RC error, so no per-layer GRT table can close it.  [CHECKED own probes]
1. Unit R matches: net that stays on its guide layer (mp_ck_Tp_br_out, 60.8 um M4 guide and route): table R ~1.15 kOhm vs RCX 1204 Ohm.
2. Cause = DRT LAYER DEMOTION of the NDR (ot_core_ck_2w2s) clock legs: guides put the vertical runs on M5 (route.guide, e.g. mp_ck_Tpq_br_out 27.4 um M5),
   DRT routes them on M3/M2 + extra vias (mp_ck_Tpq_br_out routed M3 26.85 + M4 6.08 + M2 0.86 um, 19 vias; RCX R 1312 Ohm vs ~630 Ohm on the guide layers).
   All 410 clock nets: routed M2 1420 / M3 3620 / M4 3306 / M5 1111 um (53 % on M2/M3) while the GRT guides carry ~0 um on M2/M3.
   M5 PG cover is only 5.1 % of the die area, and the two SRAMs obstruct M1-M4 only, so this is not a blocked layer. The DRT reason was not isolated (time box).
3. FF clock-sink arrival est-minus-RCX over 5490 register CK pins (kit table setRC_rcx): mean -17.67, p5 -30.59, p50 -17.73, p95 -8.90, min -41.40 ps
   (RCX range 185.1..229.9). The error depends on the branch (which legs were demoted): the late Tpqs* branch is -30..-41 ps, and q3 fails hold there.
4. Best table try (M4/M5 R x1.8, rc_m45x18.tcl): mean -5.76, p5 -15.99, p95 +1.41, min -23.76 -> a ~17 ps p5..p95 spread and a 24 ps worst case remain, beyond the 10 ps margin.
   It would also move the signal nets, which stay on M4/M5 (set_layer_rc has no clock class in OpenROAD 26Q3, FLOW-RC-1), so it is not a valid flow table.
5. Probe slacks (golden SDC, no vclk source latency, comparative only): hold est -36.96/934, rcx -25.99/1075, est_x18 -26.38/939.
q3 was NOT rebuilt with a calibrated table: no calibration closes the error (estimate before build, 12.14).
=> The fix must see the ROUTED clock: V1 (hold repair after DRT on RCX, clock frozen), or pre-route the clock with DRT before data hold repair (infra-first, 12.x),
   or stop the demotion (GRT/DRT layer agreement for NDR clock nets; open question for the CLK-TOOL owner: why DRT leaves the M5 guide).
