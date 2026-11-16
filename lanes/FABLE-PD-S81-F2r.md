# FABLE-PD-S81-F2r: S81 col Event F2r (edge-chain stations), structural review

2026-11-15 23:05 PST. FABLE-FIX-S81-COL (Fable) for COORD; cc DIE-S81-92, S81-TAPROWS, S81-SEAM-RST-1115, S81-GOTAG-SETUP-1115, GENBUG-IMPL, KIT-OPS-5.
Basis: my own TT STA on the routed DB + SPEF of the r2 pilot kit (epyc7 kw43-wave-1109n .../3fa87b84b18/items/col_h9_r2__t1__clce45cab5__pv7a260fc0/attempt_2, sign-off SDC and libs, read-only) and of the sibling pv843b0fff; plan ev/B6gF2r.json (epyc10). All 1,387 violating setup endpoints of the pilot were classed by start block, end block, launch clock, capture clock and data delay. Outputs: epyc7 /srv/opentallas-scratch3/claude/fable-fix-s81-col/an/ (pv7a260fc0b/setup_paths.tsv, srv/out_0.txt, srv/out_0b.txt). F2r bind was still running; no F2r bind, LATCHECK or kit result is used.
MEASURED = read by me from STA or the plan. INFERENCE is marked.

## Verdict

F2r is correct and needed, and it closes the 1 mm frame_int_o0 chain. Adopt it when bind and LATCHECK pass: NOT blocking.
But F2r alone does not close col_h9_r2: the chain is 66 of 1,387 failing endpoints. Five other classes stay, four of them below -100 ps, and none is an edge chain. The r2 pilot on F2r will read about -240 at sign-off (INFERENCE from the table). Do not release the col family on F2r; release only the r2 pilot. The rest goes in one further delta (F2s, section 3), which I am building.

## 1. Does F2r close frame_int_o0? Yes

MEASURED, routed: u_u_n23/o -> u_bout_frame_int_o0/q, 66 endpoints, worst -267.4. n23 clk pin at 315, clk -> o 288, so data leaves n23 at 603 after the edge. Then 1,426 um of routed path (1,073 um Manhattan) through 21 buffers: 1,008 ps, that is 0.71 ps/um on routed RC. Capture flop clock at 523.
F2r plan row (MEASURED): bus frame_int_o0, 2 stations at (1007.8, 0) and (651.4, 0), launch u_r2.u_n23.fo / .o / u_t6.so. Three hops of 356 um Manhattan.
Arithmetic (INFERENCE, routed delay per um applied to hops of 475 um routed): 336 ps of wire per hop.
- Hop 1 (macro -> station 1): slack = station clock arrival - 93 ps. Passes the -42 gate for any station clock later than 51 ps; the glue trees are 247 to 876.
- Hops 2 and 3 (flop -> flop): 833 - 60 - 336 = +437 before skew. Passes for launch-minus-capture skew up to 479.
So the chain closes with at least +130 if the station flops sit on any tap tree seen in this kit. The same row covers u_n23/fo (1 endpoint, -72.7).

## 2. What F2r leaves, r2 pilot, routed TT (MEASURED)

| # | class | endpoints | worst (pv7a / pv843) | launch clk / capture clk / data | cause |
|---|---|---|---|---|---|
| 1 | u_rrl_k (negedge) -> u_rrl_k+1 | 25 | -239.5 / -319.2 | hop data 117-274 ps over 340-550 um, launch on the falling edge | half-cycle reset relay (ot_dp_rrelay_nl): 416 ps for a 370 um hop plus tap skew |
| 2 | ROM c<k>_<j>/rd_out -> cfg7_seq s<k>/q0..q6 | about 830 | -168.8 / -157.9 | ROM clk pin 438-538, s clk pin 166-191, ROM clk -> rd_out 520-531, wire 120-294 | the core pass puts the ROM pin at the 450 target and the s pin at 450 - 271: the ROM is launched 270-370 ps after its capture pin |
| 3 | u_lpl_13_r (and _10_r, _11_r) -> t6_payload/i, t6/xai, xbi | 367 + 13 | -242.4 / -175.6 | launch flop clock 770 (tap clk_t22), payload ck pin 169, data 471 over 690 um | glue tap tree 320 ps over the 450 target; the 690 um hop has no station |
| 4 | u_d7_6_Y -> u_d7_6_Y_r<n>, and _r<n> -> u_y_rt_24a_5 RESETN | 19 + 55 | -151.2 and -106.2 | data 729 ps over 1,246 um; recovery 717 ps over 867 um | reset copy 1.2 mm from its source in one cycle; copy 0.87 mm from its loads |
| 5 | s<k>/go_tag -> e<k>_u_w/go_tag (falling-edge capture) | 4 | -119.8 / -142.6 | s clk pin 174, clk -> go_tag 383, wire 260, element clk pin -65, setup 346 | IFN = 1 half-cycle input face (FABLE-PD-S81-1515) |
| 6 | u_y_rt_24a_4 -> _5; u_lpad_frame_int_i0 r[1] -> r[2] | 6 | -45.2; -42.3 | data 584 and 752 ps | zero-logic hops of 755 and 500 um |

Clock facts behind rows 2 and 3 (MEASURED, 4_1_cts.log of the same kit): "tap mean insertion 247..744 ps (spread 496, target 450)"; trees over 470: clk_t18 876, clk_t22 853, clk_t23 748, clk 723, clk_t2 655, clk_t9 653; clk_t2 keeps 4,756 sinks against the 1,500 cap. 79 core pins are at effective 450 +/- 20. So glue flops and cores differ by up to 400 ps.
ROM address side (MEASURED, all 35 ROMs): addr_in worst +348.0, ce_in worst +478.0. The read side is -168.8. The s -> ROM -> s loop therefore has +179 in total, all on the wrong half.

Blocking or not, per class:
- Row 1: BLOCKING for the pilot (it is the worst path on 3 of the 6 routed r2 kits). Fix exists in the tree as an opt-in type key: reset_relay_full (S81-RCK-4, gen_phys.reset_relay_full: the kit copy of ot_dp_rrelay_nl becomes one posedge flop, same cycle count). Worst becomes -239.5 + 416.5 = +177 (pv843: +97). My decision: full cycle, not a re-site; a re-site cannot pay 370 um plus skew in 416 ps. No S81-SEAM-RST answer is needed.
- Row 2: BLOCKING, 830 endpoints. Fix: ROM clock pin 255 ps earlier (declared pin offset in the core latency table, no RTL, no cycle): read side -169 -> +86, address side +348 -> +93.
- Row 3: BLOCKING, 380 endpoints. Stations do not fix it while the launch tree is 320 ps late; the tree does. With the launch flop at target the path is +78. Fix: lpl_*_r / lpl_*_w / bout / station registers on their own planned taps (one per bus rank), clk_t2 split.
- Row 4: BLOCKING (-151). Fix in the reset_replicate rows: chain the copies (hop <= 340 um) and place each copy at its loads.
- Row 5: BLOCKING at -120 on 2 of 4 element west halves. Fix is the IFN = 0 halves of FABLE-PD-S81-1515, already planned for F2b.
- Row 6: at the gate limit; closes with the station tool once the trace also follows u_y_rt and lpad ranks (one more station each).

## 3. Next delta (F2s), owners

1. reset_relay_full = true on all 216 col types. Rows: FABLE-FIX-S81-COL -> DIE-S81-92. Read FF hold on the relay hops in the pilot (the T/2 hold margin is given up).
2. ROM clock rows: ROM pin 255 ps before the grid target. FABLE-FIX-S81-COL (kit proof on r2 first, then rows).
3. Glue tap trees at target: planned taps for the lpl / bout / station / lpad ranks, clk_t2 split. FABLE-FIX-S81-COL with S81-TAPROWS.
4. reset_replicate chain and copy sites. FABLE-FIX-S81-COL with S81-SEAM-RST-1115.
5. IFN = 0 halves: S81-GOTAG-SETUP-1115 (unchanged).
6. Station-tool trace fix (seam write cells as wires) to main: FABLE-FIX-S81-COL lands DIE-S81-92's local patch as a branch.

## 4. Stop list

- Releasing the col family (216 types) on F2r.
- Reading the F2r pilot at the gate (stop list of FABLE-CLOSURE-STRATEGY still applies).
- More stations as the answer to rows 2, 3 or 5: they are clock and half-cycle problems.
- A re-site of the reset relays instead of the full-cycle form.

## 5. Not checked

- F2r bind / LATCHECK result, and the other 215 types: only col_h9_r2 (two routed kits) was read. The 1,176 stations of the other types were not reviewed row by row.
- Hold after any of the fixes. The station hops and the full-cycle relays cross taps whose trees differ by up to 500 ps today.
- The 0.71 ps/um figure is one path.
- F2a's reset_replicate rows are newer than the routed kit (which carries the COLGEN C2 copies); row 4 must be re-read on the first F2a/F2r pilot.
