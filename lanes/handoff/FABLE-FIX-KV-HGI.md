# FABLE-FIX-KV-HGI handoff (Fable; owner of KV hg / hgi: kv3_hg*, kv3_hgi*; since 2026-11-20 19:26 PST)

Posts: lanes/posts/FABLE-FIX-KV-HGI.md. Read first: lanes/FABLE-PD-KV-1500.md, lanes/FABLE-PD-KV-1840.md, lanes/handoff/KV-PLAN-R2.md.
Lane dirs: epyc7 + epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-hgi (b8, b8d kits; wt = lane clone, epyc7 only),
epyc8 same path (root7 private plan root, rows/, out7/), epyc9 same path (krprobe). Hub logs: intel2 ~/tmp/fablefixkvhgi
(launch.sh NAME TYPE GOAL MEM THR; OT_LANE set inside).

## 1. Hold root cause (state 20:1x: mechanism MEASURED on hgi_v1 kR; v3-v8 A/B queued, not yet measured)

Evidence (read): epyc9 fable-kv-hg0/kR_readback/FF.readback.log (5_1_grt.odb 477b6b4aaede, propagated, GRT RC) and the kR
4_1_cts.log.
- Worst hold end -277.63 FF: u_hst3_t2_rls_a.q[146] -> u_head3_e2/g_front_1_u_front__q_data_in[124].
  Launch clock clk_t2 at the flop 133.3 ps. Capture clock: port clk_c13 0 -> clk_c13_tb0_d0 (BUFx4) 153.4 -> three
  clkleafrepg 213.4 -> core clock pin 380.8. Uncertainty 25, library hold 118.96.
- The core tap is direct by plan: port clk_c13 (M7) at the centre of the 216 x 216 um core, the core clock pin (M5) at
  LEF (108, 108). core_taps.txt: early_ps 0, internal insertion 237.8 TT / 189.3 FF, so the pin is meant to see ~0.
- tap_balance.tcl pads every tap more than OT_TAP_TOL_PS (10) under the 250 target with BUFx4 cells seeded AT THE TAP PORT.
  Inside a core they legalise outside it. Log: it0 clk_c13=230 (20 short) -> it1 312; "OT_TAP_CORE ... pin 75 + internal 238 =
  effective 312 WARN early core tap still late". 10 of 16 head cores on kR. At GRT RC the detour is 381 ps FF.
- So skew 247.5 (capture later than launch) + hold 119 = the -277. The same detour delays every core output: kR TT -310 at GRT.
- All head cores have internal insertion 236.7-246.9 TT, i.e. 3-13 ps under target: cores at 236.66 (d = 13.3 > 10) are
  padded, 246.92 (e0) is not. That is a constant of the family, so v3-v8 are expected the same (NOT yet measured).
- The D26 lockups (clock.core_input_lockup) treat the symptom on the data side; they do not cover the 22 rst_n pin ends
  (FABLE-PD-KV-0945) and do nothing for the core-output setup loss.

Fix (structural, CTS balance; clock period untouched): opt-in OT_TAP_CORE_DIRECT=1: tap_balance.tcl never pads a core-only
tap whose port is inside the outline of the core it clocks; shortfall logged (OT_TAP_CORE_DIRECT line, WARN over 60 ps).
Lane clone epyc7 fable-fix-kv-hgi/wt, branch claude/fable-fix-kv-hgi-1120, commit 49c46f1e15 (tap_balance.tcl,
gen_phys.tap_core_direct -> config.mk line, test_tap_core_direct.py 21 focused tests pass). NOT pushed: push after the A/B.
Enable on KV: plan clock.core_tap_direct true on the 19 hg/hgi types, or OT_TAP_CORE_DIRECT=1 in dies.qwen_kvsys.die_gen_env.

A/B on the same placed DB (held D25e3 kv3_hgi_v8 attempt_6, copies; DO_NOT_COUNT):
- b8  = unchanged kit, goal cts.  log intel2 ~/tmp/fablefixkvhgi/b8_cts.log
- b8d = b8 + patched tap_balance.tcl + config.mk OT_TAP_CORE_DIRECT=1 (mtimes kept), goal cts.  log b8d_cts.log
Both waited for memory on epyc7 (20+ waiters); kits copied to epyc10 so ot-run can rebalance. Read after CTS:
grep "OT_TAP_BALANCE\|OT_TAP_CORE" run/logs/asap7/*/base/4_1_cts.log; then an FF propagated readback like
epyc9 fable-kv-hg0/kR_readback/read_grt.tcl on 4_cts.odb (estimate_parasitics -placement) for the head-core front pins.
Net-level probe of the kR path (locations, nets): epyc9 fable-fix-kv-hgi/krprobe/probe.log (queued, log krprobe.log).

Open question to settle with the probe: the 167.4 ps increment on the core clock pin line equals the lib
min_clock_tree_path (167.62). If OpenSTA adds the ETM clock-tree delay on a propagated clock while the hold arc (119) already
contains the internal latency, 167 ps of the hold requirement is model double count; if it is wire, it goes with the detour.

## 2. hgi_v1 collector path (-410, 1,320 um): fixed by the D26 plan itself, no station row
D25e3 plan: collector_children[1] (pv_S_0, monitor_1 band 1231-1257 x 17-26) -> node rst_n_t45 = pad tap 45 at (337, 441).
R3e a9f605cb1acf: the same child -> node rst_n_t34, relay u_rrl_147 at (1244.6, 21.6) = inside the monitor band: 0 um for
fault, ready and the monitor reset. collector_tree max_hop_um 275. To do: confirm in the R3e bound RTL
(u_cland_collect_rst_n_t34 takes cland_dn_word_1) when the bind ends; measure on the first D26 hgi_v1 kit.

## 3. D27 rows for KV-PLAN-R2 (hg / hgi were dropped from D27b r3 for this lane)
lanes/handoff/FABLE-FIX-KV-HGI-r7_hg_census300.py (+ -r7.json): the hg/hgi half of r3_census300.py, same d27lib form.
On R3e a9f605cb1acf (epyc8 fable-fix-kv-hgi/root7): plan_geom_census kv3_hg* 242 HOP rows / 19 types (worst 482) ->
2 rows, both the kept hgi_v1 section N tN row (D26 N3 sites, n3_check max 299.0; the census measures regs[-1] -> the stale
to_um (133, 935)). 114 buses re-spaced, 106 station adds, 268 lanes +572 lane-cycles (max +3), plan 7a1687c80a5d.
NOT gated: no G0 / bind / LATCHECK. The 2 core:u_head*_e7.kp_o -> u_head*_e0.u_kt rows per type go 2 -> 5 stations (off-macro
sites): check the kt latency parameter in param_regen / LATCHECK before taking them; drop them from the row set if refused.

## 4. Proof kit (not started)
After the A/B: generate one hgi representative (kv3_hgi_v8) from the applied D26 tree on the current runtime with
OT_TAP_CORE_DIRECT=1, run_kit.sh GOAL=route through sign-off (OT_LANE set). Compare hold with and without the D26 lockups:
with a direct tap the lockup costs half a period of setup into the core (launch at the falling edge), so if the direct tap
closes hold alone, propose dropping clock.core_input_lockup on hg/hgi in D27. Then: release the family (KV-PLAN-R2 lifts the
8 hg hold_items + the kv3_hgi* visual skip at D26 apply), export signed records to AGIdock + rtx-pro ~/signed-export-1114.

## Stop list
- No route of the held D25e3 hgi kits (v1, v3, v5-v8): unchanged from FABLE-PD-KV-1840.
- No hold-buffer ECO on head-core front ends; no clock period change; no new tap rows before the A/B.
- b8 / b8d are private copies: never export, never count.
