# FABLE-PD-S81-1415: S81 col seam reset removal (async hold)

2026-11-15 14:20 PST. Fable PD review for COORD; cc S81-SEAM-RST-1115, DIE-S81-92.
Type col_h9_r0_p6__t1__pv082a7609, pilots pc2 / pg of S81-SEAM-RST-1115 (epyc10 s81-seam-rst-1115/pilot), 4_cts.odb, the lane's ac5 STA form (RVT libs, placement parasitics, 4_cts.sdc).
My scripts and outputs: epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-1415/ (common2.tcl, a2/d/dff2/e .tcl, *.out). Read-only on the pilots, nothing written to a kit.

## Verdict

Removal on the col types is NOT a reset-tree problem and needs NO new reset form. It is ordinary cross-tap hold debt, and the flow's own hold repair closes it with about 30-90 cells. The pilots were read at 4_cts.odb, which is BEFORE any hold repair (SKIP_CTS_REPAIR_TIMING=1; R-FLOW-5 puts the repair at the FF GRT step). The lane's blocker ("delay cells cannot close: recovery +61, removal needs +230") compares the worst recovery pin of the type with the worst removal pin: they are different pins.

Stop forms A (clone ECO, pilot pg4) and B (rq per tap + reset port per group). Pilot the hold build on pg.

## Measured

1. My run reproduces the lane: pg removal 198 fails worst -228.6, recovery 0 fails worst +60.8; pc2 579 / -237.9, recovery +103.8.

2. Per pin, every failing removal pin has large recovery slack (MEASURED, all 198 pg pins and all 579 pc2 pins): pins with recovery + removal < 0: 0 in both. Lowest recovery slack on any failing removal pin: pg +362.7, pc2 +349.6. The worst pin (d14 r77 -> rt_2b_1 rq) is removal -228.6, recovery +590.1. The +60.8 recovery pin is d14 r37 -> lpl_9_w g_chunk[9].r[15] through an AND2 and 9 buffers (808 ps data), and its removal is met.

3. What the -229 is made of (worst pg path, full clock expanded): launch tap clk_t24, capture tap clk_t7.
   - 208.0 ps: the kit tap WINDOW (constraint.sdc: set_clock_latency -source -early -208 on every clk / clk_t<i> port). Paid in full by any pair on two ports (no CRPR across ports), nothing on one port. RULEBOOK R-CLOCK item 2.
   - 70.4 ps: real insertion difference (t24 leaf 300.4 early, t7 leaf 370.8).
   - 25.0 hold uncertainty + 30.3 library removal - 105.1 data (flop QN + INV).
   With the window set to 0 (same DB, nothing else changed): pg 198 -> 12 fails worst -20.6; pc2 579 -> 12 fails worst -29.9. With the window kept and hold uncertainty 0: pg 187 fails -203.6.

4. Tap membership from the DB (clock pin traced back to its port): pg 188 of 198 failing pins are cross-tap, 10 same-tap (worst -8.9, driver xb_1_0 rq on clk_t2); pc2 569 of 579 cross-tap. In pg each failing rq has all its failing sinks on ONE other tap (rt_4a_4 rq t24 -> 26 sinks on t7; rt_0b_4 rq t18 -> 27 on t2; x2_1_0 rq t20 -> 60 on t18).

5. The taps of this pilot are not balanced (pg run_cts.log, last OT_TAP_BALANCE line): tap mean insertion 225..434 ps, spread 209, target 250 +-10. Slow taps: clk_t13 434 (403-543, 1,464 sinks), clk_t7 373, clk_t10 342, clk_t14 325 (221-480 inside one tap, 2,738 sinks), clk_t15 319. The balance only adds delay, so it cannot bring these down.

6. Hold repair closes removal and keeps recovery (plain `repair_timing -hold -hold_margin 0 -max_buffer_percent 100` in memory on 4_cts.odb, placement parasitics, DB not written):

   | run | removal before | removal after | recovery after | hold cells total | cells on async cones | setup WNS |
   |---|---|---|---|---|---|---|
   | pg TT, 1 call (15 s) | 198, -228.6 | 0, +3.0 | 0 fails, +65.1 | 7,485 | 29 (28 HB4 + 1 BUFx2) | -369.2 unchanged |
   | pc2 TT, 1 call | 579, -237.9 | 0, +0.9 | 0 fails, +46.0 | 7,126 | 50 | -369.2 unchanged |
   | pg FF, call 1 | 382, -230.3 | 2, -140.9 | 0 fails, +79.5 | 16,324 | 56 | -307.6 unchanged |
   | pg FF, call 2 | | 0, +0.4 | 0 fails, +79.5 | +1,735 (18,059) | | unchanged |
   | pc2 FF, call 1 | 1,045, -237.7 | 4, -148.1 | 0 fails, +35.7 | 14,940 | 90 | unchanged |

   The 2 pins left after FF call 1 (d14 r100 -> rt_8a_3 rq, d14 r77 -> rt_2b_1 rq) had recovery +593: the tool stopped its pass, room was there; call 2 closed them (+30.0 and +8.4), call 3 added 0. FF hold of the whole type after call 2: -1.87 ps, TNS -9.
   Limits: FF runs use the TT SDC (no FF core-tap overlay, vclk TT), so macro and port rows of those runs are not a verdict; async pairs are internal and not affected. Placement parasitics, not routed.

7. The setup WNS -369.2 TT of this DB is not reset: u_u_s1/go_tag[1] (ot_s81_cfg7_seq, 397 ps clk->out) -> u_u_e1_u_w go_tag[1], a falling-edge capture on core tap clk_c with 346 ps library setup. Listed for DIE-S81-92; outside this review.

## Answers to the questions

- Is the cause the driver being on a different tap than its sinks? Yes, cross-tap (188 of 198). But not an "early tap": 208 of the 229 ps is the modelled window that every cross-tap pair of the type pays, data paths included; the real insertion difference is 70 ps on the worst pair. It is a clock contract quantity (R-CLOCK), not a reset-tree fault.
- Would driver-on-sink-tap close it? For that pair yes (same port = CRPR, same-tap fails are 10 pins at -8.9). pg already does this: 579 -> 198 pins. It cannot cover a driver whose sinks sit on two taps, and it does not need to: the rest is 29 cells.
- Legal: METHODOLOGY 4.5 (delivered reset with timed recovery/removal); R-MINIMAL gate 3 (FF hold >= 0; `worst_slack -min` includes removal, MEASURED: pre-repair hold WS = the removal worst); R-FLOW-5 / R-CLOCK-1 (hold built once, FF, target 0); related-pair skew 80 ps is a target, not a gate (12.4a). No rule is bent.

## Ranked fix

1. PILOT FIRST: hold build on pg, no new form. Owner S81-SEAM-RST-1115.
   - Kit: pilot pg as it is (rows/s81_seamrst_rr.json reset_replicate + OT_TAP_RESET_AFFINITY=1). Continue it from 4_cts.odb through the normal flow to route; do not stop at CTS.
   - Turn on the R-CLOCK-1 hold build for the type (plan `clock.pregrt_ff_hold: true`, tools/die_plan/pregrt_ff_hold.py: FF hold repair on 4_cts.odb, placement parasitics, before the first GRT). Reason: this type carries 18,059 FF hold cells in all; the in-GRT repair re-routes per buffer and is the known stall class (R-CLOCK item 4).
   - Read with ac5 at FF and TT on the built DB and again on the routed DB: pass = removal 0 fails and recovery 0 fails.
   - Two checks in the tool (INFERENCE, I did not read pregrt_ff_hold.py): (a) its endpoint classes include RESETN/SETN pins (the async path group), not only D pins; (b) it repeats the repair call until a call adds 0 cells (my FF call 1 left 2 pins at -141 with +593 room). If either is missing it is a small fix in pregrt_ff_hold.py, owner S81-SEAM-RST-1115.
2. KEEP tap_reset_affinity.tcl (branch claude/s81-seam-rst-1115 @c830c7a4b), opt-in, on for the col types. MEASURED: async removal pins 579 -> 198 TT, 1,045 -> 382 FF; async pad cells 50 -> 29 TT. Clock pin only. Not pg2 (per-tap copies: 177 pins / 17 nets, worse worst, 111 copies: no gain).
3. Event F part 2 rows: rows/s81_seamrst_rr.json (recovery) are sufficient on the reset side once the pilot of item 1 passes. Owner DIE-S81-92: add `clock.pregrt_ff_hold: true` and the affinity key to the 216 col types in the same event. S81-TYPEMERGE-IMPL: no reset work from this review.
4. PARALLEL, not blocking F2 (owner DIE-S81-92 with S81-TAPROWS / CLKSITE-RESERVE-1115): the type's real hold cost is the clock, not the reset.
   - Flat window 208 on all 32 ports ("208..208"). R-CLOCK-2c: above ~100 ps fix the die clock for the region or give measured per-port values (die_sta_related --kit-window-out + tap_window_floor.py). MEASURED cost here: 18,059 FF hold cells = 16.9 % of 106,927 logic cells (budget line 10 %). INFERENCE: a 100 ps window would roughly halve it.
   - Tap trees 225..434 against 250: clk_t13 / t14 / t15 carry 1,291-2,738 sinks with up to 259 ps inside one tap. INFERENCE: split these taps (sink cap near 1,500 instead of OT_TAP_MAX_SINKS 3000) or add a tap row there; this is CLKSITE / TAPROWS work.

## A / B / C and the other forms

| form | verdict | why |
|---|---|---|
| C hold repair on the async group | DO (item 1, as the type's normal hold build) | MEASURED closes 198 / 579 pins with 29 / 50 cells, recovery kept |
| A clone driver flop per sink tap (ODB ECO, pg4) | STOP | about 300 flops plus ECO, power connect, legalise and LEC risk to save 29 cells |
| B rq per tap group + reset port per group | STOP | plan/bind change keyed on a tap map from an earlier CTS; the map moves with every placement |
| per-tap local synchronizer / retime at tap | STOP | rq already is the local stage; per tap it is form B |
| driver into the capture tap's sink group (clock_landing_plan) | not needed | pg does the legal part at kit level (majority tap) |
| negedge release (ph) | STOP | MEASURED recovery 757 fails -233 |
| one tap per relay station (region_re) | not now | would cut cross-tap data pairs too, but it is a tap-assignment event; consider only under item 4 |

## Stop list

- pg4 clone ECO in tap_reset_affinity.tcl; form B rows / relay master reset ports; ph; pg2; plrc / plrs / RSSLICE / RQSYNC.
- Reading async removal on 4_cts.odb as a verdict (it is before hold repair).
- Comparing the type's worst recovery with its worst removal; use recovery + removal per pin.
- Any margin or uncertainty change to pass removal.
