# FABLE-PD-HEAD-1650: HEAD open types (hd_host_e, hd_host_w, hd_ctl, hd_serdes) -- PD review

Reviewer FABLE-PD-HEAD-1650, read-only, 11-15 16:35-17:25 PST. No build, no STA run by me: every number below is read
from the lanes' own kept logs/reports. Tags: MEASURED = read from a log/report/kit file named here; INFERENCE = my
arithmetic or expectation, not built. Gates: DRC 0, TT setup >= -42, FF hold >= 0 non-port, bind + LATCHECK.

Kits read: hd_host_e v1 = epyc10 /srv/opentallas-scratch2/claude/head-host-close-1115/v1k2/hd_host_e (fanout 64),
v1f = .../v1f/hd_host_e (fanout 20), lane STA dump .../v1d/out; hd_host_w = intel1 .../head-host-close-1115/hwv/ka (64)
and kb (20), baseline dump .../hw5/out; hd_ctl = epyc7 kw43-wave-1109n/.../head_rp21z20NF6/items/hd_ctl/attempt_5/gen/hd_ctl
and proof epyc10 /srv/opentallas-scratch2/claude/drt0255-proof/var/p_hd_ctl; hd_serdes = epyc2 .../head-host-close-1115/sd9k/hd_serdes.

## 0 Answers

1. hd_host_e input side is NOT RTL depth, NOT placement distance, and fanout 20 makes it WORSE. It is two ~385..770-load
   control nets of the ISLICE (read-pointer select isl_rp; write enable isl_take from u_ski.o_valid) carried by a
   DRV-only buffer tree that no TT setup repair ever touches, plus 64-69 ps of die tap window on cross-tap paths.
2. FLOW CLASS (new, all HEAD kits read, probably all dies): the GRT-stage `repair_timing -setup` runs in an FF-only
   session and prints "No setup violations found" while the TT gate of the same DB reads -77.72 (hd_host_e) and -261.02
   (hd_serdes). CTS repair is skipped (SKIP_CTS_REPAIR_TIMING=1). TT setup is measured, never optimised.
3. hd_host_w: the loader pipeline removed the RTL-depth part, but pre-GRT TT setup is still -66.3; fanout 20 changes
   nothing (-66.6). The clock side is the next cause: 9 of 12 taps sit at the 3000-sink cap, tap means 359..446 ps.
4. hd_ctl: same class as hd_spn (FABLE-PD-HEAD-1115): M7 face pin under the kit's own M7 strap, core-phase pdn, no PG
   flags in the wave kit. Proof with die-phase pdn is already past CTS (DRT0255-PROOF-1115).
5. hd_serdes on NF9 taps: GRT gate TT setup -261.02. The tap re-derivation did not close it; it needs its own lane.

## 1 hd_host_e -- measured

- v1 gate (postcts_gate_tt.json, 5_1_grt.odb, TT): setup -77.72, TNS -6,877, 212 violators; FF setup +124.29; hold est
  -13.47 TT / -3.92 FF, all 39 hold violators start at input port coll_i1[*] (v1d/out/sum_hold.txt) = port paths, not
  in the hold gate. MEASURED.
- Violators by start -> end (v1d/out/sum.txt, 212 rows). MEASURED:
  - 34: isl_rp -> u_epc/in_data[302..383], worst -77.72.
  - 176: u_ski.o_valid -> isl_d0[*]/D (158), u_ski.u_head prev_q/cur_q (15), SRAM r_ce_in (3); worst -48.9. These do NOT
    end at u_epc; the lane's "all on the u_epc input side" is right only for the 34.
  - 1: isl_cnt.
- RTL (kit rtl/ot_s81hd_mesh_ep_core.sv 1544-1567): `isl_q = isl_rp ? isl_d1 : isl_d0` = one flop selects a (W+1)-bit
  2:1 mux (in_data index up to 383 seen); `isl_take = iv && ir_g` gates 2 x (W+1) enable muxes. Logic after the select
  is 2 gates. MEASURED. The comment "write enables come from registered state only" does not match: o_valid passes
  OR2/AO21/INV/AND2 (308 ps) before the tree.
- Worst path isl_rp -> in_data[342] (postcts_gate_TT.log): data 619 ps = flop QN 124 (DFFASRHQNx1, 12 loads, slew 169)
  + 5 place-stage buffers 262 + fanout23209 BUFx2 on 64 loads 129 (slew 308) + NAND2/OA21 94 + wire 10. 515 of 619 ps
  is the tree. Per-stage net caps 6-29 fF, last wire 10 ps: no long wire. MEASURED; "not placement distance" is
  INFERENCE from those caps (no xy read).
- Capture: clk_c0 source latency -107.32 = -(38.32 early + 69 window). constraint.sdc line 11/35: 69 is the FALLBACK
  window for "unmeasured ports clk_t10 clk_c0"; measured ports are 20 (t2,t3,t5) to 69. The launch tap clk_t2 has 20.
  So 49-69 ps of the -77.72 is an unmeasured-port default. MEASURED.
- o_valid -> isl_d0[118]: launch clk_t6 at 438.7, capture clk_t4 with -64 window, data 811 ps (gates 484, tree 327 incl.
  fanout23192 BUFx2 on 64 loads 114, slew 271). MEASURED (v1d/out/p2.txt). The ISLICE flops sit on three taps
  (t2, t4, t6) + clk_c0, so every control path pays a window.
- Flow: config.mk SKIP_CTS_REPAIR_TIMING=1; 5_1_grt.log reads 7 liberty files, all `-corner bc` (FF), binds
  core_taps_ff.sdc / vclk 342, then line 457-459 `repair_timing ... -setup` -> `[INFO RSZ-0098] No setup violations
  found`, again at 524-526. Same two RSZ-0098 lines in hd_serdes sd9k (TT -261.02). MEASURED.
- Fanout 20 (v1f, same kit, only OT_PLACE_MAX_FANOUT 64 -> 20): place repair inserted 1,057 buffers in 641 nets (v1:
  132 in 121). pregrt_ff_hold.log, TT scene, same stage: setup_wns v1 -23.70, v1f -88.45. MEASURED: 64.7 ps worse.
  v1 lost 54 ps from that stage to the GRT gate, so v1f at the gate is about -140 (INFERENCE). v1f gate not printed yet.
- v1k2 itself: in DRT, 1st iteration, 24,616 violations after iteration 0. Routed setup will stay near -78 (INFERENCE):
  it can give DRC and hold evidence, not a sign-off.
- Tap balance v1: means 416..458 (spread 42), clk_c0 effective 451. Not the cause. MEASURED.

## 2 hd_host_w -- measured

- Baseline (hw5/out/p1.txt, -195.0): loader shadow -> owner.ready, 27 cells, data 912 ps; launch clk_t2 at 455.5,
  capture clk_t10 at 344.3 (366.3 raw - 22 window): 111 ps of the -195 was the capture tap arriving early. MEASURED.
- With the loader pipeline (bind PASS, LATCHECK 329/329): pregrt_ff_hold.log TT setup_wns ka (fanout 64) -66.34,
  kb (fanout 20) -66.63; kb inserted 1,500 buffers vs 358. MEASURED. Fanout is not the limiter here.
- 4_1_cts.log ka: `OT_TAP_BALANCE done: tap mean insertion 359..446 ps (spread 86)`; clk_t10 = 359 (338-494, 3000
  sinks), clk = 410, clk_t6 = 408, clk_t9 = 392 (379-497); 9 of 12 taps hold 2,968-3,000 sinks = the OT_TAP_MAX_SINKS
  cap; the check asks to re-pitch taps. kb: 385..460, spread 74. MEASURED.
- Both kits are alive in pre-GRT FF hold repair (log growing 16:30/16:41; hold -147 / -131 on ~6,500 endpoints); no GRT
  gate yet. Expected gate about -100..-120 if the GRT adder is like hd_host_e's 54 ps (INFERENCE). Which path is the
  -66 was NOT read (no STA by me); if it is still a t2 -> t10 path, the 67 ps tap-mean gap + 22 window explains all of it.

## 3 hd_ctl -- measured

- attempt_5 (NF6, epyc7): two DRT-0255 in the 1st iteration, b_i[67] box (190.38, 6.84) and b_i[101] box
  (198.36, 6.84)-(202.35, 10.83): the same box row as hd_spn.
- pdn.tcl M7: `-pitch 8.64 -offset 4.128` (core phase); config.mk has no OT_PG_* line. b_i[101] = M7 pin x
  198.800-198.832, inside the VDD strap 198.768-199.056 (pair centre 23 x 8.64 = 198.72). 74 of 1,137 M7 pins overlap a
  strap, 70 on the bottom face (io.tcl arithmetic). MEASURED. Cause identical to FABLE-PD-HEAD-1115 section 0.1.
- The earlier fail (06:02, plan rp21z4 attempt_8) was an INTERNAL net u_core.u_logic.f2d[530], box y 134.52-138.51,
  which contains the M6 strap pair row 135.744/136.128 (6.144 + 30 x 4.32). INFERENCE: that one is the dead-row guide
  class (track truth), so hd_ctl can show a second DRT-0255 after the face pins are cured.
- Proof p_hd_ctl (die-phase pdn -offset 8.448 MEASURED in its pdn.tcl, TRACK_TRUTH=1, keep-out 0): 4_cts.odb written
  16:21, going to GRT. p_hd_spn: in GRT (stall_resume odb 16:18). No route verdict yet.

## 4 Ranked fixes

| # | Type | Fix | Evidence | Owner |
|---|------|-----|----------|-------|
| 1 | all (flow) | TT setup repair. Proof first, 15 min, no route: open v1k2 4_cts.odb with the TC libs + kit SDC (as postcts_gate.tcl does), `repair_timing -setup -setup_margin 0 -repair_tns 100 -skip_last_gasp`, report TT WNS/TNS before/after and cells changed. If it closes, the GRT-stage setup repair must run on a TC scene (OT_HOLD_MM=1 is the existing switch in KV kits; whether it maps to TC libs on HEAD kits is NOT checked). Do not use SETUP_SLACK_MARGIN for this: the hold repair call takes the same margin and would refuse pads | cause MEASURED (RSZ-0098 at -77.72 and -261.02); cure INFERENCE (sizing the two 64-load BUFx2 alone is worth ~80 ps each) | proof HEAD-HOST-CLOSE-1115; flow change GENBUG-IMPL |
| 2 | hd_host_e | RTL, 0 cycles: replicate isl_rp into 8 keep copies (one per ~48 bits of isl_q); same for the write-enable cone (isl_wp/cnt/up copies per 64 bits, u_ski valid copies like u_sko NR=3). Bind + LATCHECK + LEC with duplicate registers (as ot_rst_copies) | tree 515 of 619 ps MEASURED; after: flop + 1 buffer + 2 gates ~220 ps INFERENCE | HEAD-HOST-CLOSE-1115 |
| 3 | hd_host_e | Measure the clk_c0 tap window in the NF10 die clock proof instead of the 69 fallback (pairs clk_t2 -> clk_c0, clk_c0 -> t4/t6); feed clk_c0 from the die leaf of clk_t2. At W=20 the 34 isl_rp endpoints read -28.7 | 69 fallback MEASURED; -28.7 = -77.72 + 49 arithmetic | HEAD-100 |
| 4 | hd_host_e | One tap for the ISLICE (isl_d0/d1, isl ctl, u_ski.o_valid) with the kit's tap affinity pass: the 176 enable endpoints lose the 64 ps t6 -> t4 window (-48.9 -> about +15) | window MEASURED; result INFERENCE | HEAD-HOST-CLOSE-1115 |
| 5 | hd_host_w | Re-derive taps from the placed sink census as done for hd_serdes: ~24 taps, <= 1,500 sinks each, rows into NF10/NF11. Then read the worst path's launch/capture tap arrivals at the ka gate before anything else | 9/12 taps at cap, means 359..446, 111 ps clock loss on the baseline path MEASURED; gain INFERENCE | HEAD-HOST-CLOSE-1115 -> HEAD-100 |
| 6 | hd_host_w | Keep variant a (fanout 64) as the adoption candidate; b adds 1,142 buffers for 0 ps | MEASURED | HEAD-HOST-CLOSE-1115 |
| 7 | hd_ctl | Wave kit with die-phase pdn (item_env OT_PG_DIE_PHASE=1, OT_PG_TRACK_TRUTH=1, keep-out per the proof verdict); accept check before route: pdn.tcl M7 `-offset 8.448` and PG_PIN_CHECK bad_pins=0. If an internal-net DRT-0255 follows, send maze.log + 5_1_grt.odb to DRT0255-PROOF, no relaunch | cause MEASURED; cure waits on p_hd_ctl / p_hd_spn | DRT0255-PROOF-1115 (proof), KIT-OPS-5 (item_env) |
| 8 | hd_serdes | Own lane (NEEDS-LANE HEAD-SERDES-SETUP): NF9 gate TT setup -261.02, pre-GRT -218.2, hold est -407.59 (port share not read). First step: path dump as v1d (start/end groups, launch/capture tap arrivals), then fix 1 | MEASURED numbers; cause not read | new lane |

Order for hd_host_e: 1 (today, cheapest) -> 3 + 4 (plan/kit numbers, no RTL) -> 2 if 1 does not hold after route.
Fix 1 or 2 alone should bring both groups inside -42; 3 alone leaves the 176 enable endpoints at -48.9.

## 5 Stop list

- OT_PLACE_MAX_FANOUT=20 as a setup fix on hd_host_e (v1f) and hd_host_w (kb): measured -64.7 ps and 0 ps. Do not route
  v1f or kb; read their gate lines for the record only (stop is the owning lane's, not mine).
- No register stage at the u_epc input and no u_ski floorplan move: +1 lane cycle or a plan event for a path whose
  logic is 2 gates and whose wires are short.
- No further u_epc clock-early change for the input side: clk_c0 effective is already 451 ps.
- No hd_ctl / hd_spn_end / other M7 face-pin HEAD kit from the wave with pdn M7 `-offset 4.128`.
- hd_host_w READY-ROWS on the loader pipeline alone: wait for the ka gate; -66 pre-GRT will not read >= -42 after GRT.
- Do not count v1k2 as a sign-off candidate at -77.72; let it finish for DRC/hold evidence.

## 6 Not checked

- No STA or repair run by me: fix 1's result, fix 2's ~220 ps and fix 4's +15 are estimates.
- u_epc OUTPUT-side worst slack in v1 (needed before any clk_c0 skew trade) was not in the dumps.
- xy of isl_rp / u_ski / u_epc pins not read; distance is ruled out from stage caps only.
- The -66 path of hd_host_w ka/kb and every hd_serdes path: not read.
- Whether OT_HOLD_MM works on HEAD kits, and why the GRT session is FF-only while config.mk says CORNER = TC: not traced.
- Other dies: the FF-only setup repair was seen on 2 HEAD kits only; S81/QC/KV kits not opened.
- p_hd_ctl / p_hd_spn route verdicts: pending at 17:20.
