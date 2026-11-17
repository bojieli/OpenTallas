# FABLE-CLOSURE-STRATEGY 2026-11-17 01:30 PST (0155): delta on 00:50, top 3 levers checked against kit data

Reviewer: FABLE-CLOSURE-STRATEGY-0155 (Fable). Read-only on builds. Technical PD only. HBM parked.
Blocking gates (R-MINIMAL): DRC 0 route, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.

Marking: **V** = I opened the file / DB record myself this round. **R** = reported by the named lane, not opened.

## 0. What changed versus 00:50

1. **S81 strip "die reset 106 / -1096" is mostly a different class (V).** On t47, 97 of the 106 ends are reset relay -> next
   reset relay hops launched on the FALLING edge and captured on the rising edge (134 such pairs, all `u_rrl_* DFF_N -> u_rrl_* DFF_P`,
   Manhattan median 363 um, max 387, worst -232). They obey the 405 um reach rule and still fail, because the hop has 416 ps.
   Only 6 ends are the corner -> FSTART broadcast (-1096) and 3 are corner -> origin (-539). The 01:04 C4 rows fix those 9 and the
   69 START ends. Nothing posted fixes the 97.
2. **QC cb is a kit placement-order fault, not reach (V).** Lever 3 of 00:50 (station row, +1 cycle) is withdrawn. My 955 ps -> 1.5-2 mm
   inference was right about the wire and wrong about the cause.
3. **S81 col h9_r2: pg2 gave no design result (V).** It died on ENOSPC writing 3_place.odb. Its relay sites would have recrossed the
   e14 macro body anyway. pg3 (wall-avoiding relay path) is the form; its sites are macro-clear.
4. **S81 SerDes H3p fails the gate at GRT (R, reconciled by the lane):** TT -54.29. H4 no longer waits for the routed read.
5. **HEAD -2 ns landing hold was a tool defect (R)**, removed from the reset / START class. The HEAD residue is three separate legs.
6. KV tap rows are built (V: packet sha and tolerance figures). KV reset / START relays moved to HG6.

## 1. Evidence I opened

| lever | host, path | what I read | result |
|---|---|---|---|
| S81 col h9_r1 (ir1) | epyc8 fable-fix-s81-col/ir1/col_h9_r1__t1__cl49d7a23e__pv047ea3b3: grt_policy.json, postcts_gate_{tt,ff}.json, pregrt_ff_hold.log, run_route.log, 5_1_grt.log | GRT congestion report, TT / FF policy | Overflow 0 / 0 / 0 on both GRT runs (usage 12.3 %, 11-12 extra iterations each). TT -31.70, 91 violators, TNS -608. FF hold at GRT -42.66 on 522 ends, all port-start (frame_int_i0 / i1, needs parent); pre-GRT internal FF 0 ends with 5,074 hold cells, setup +0.04. Second GRT finished 01:22; DRT follows |
| S81 col h9_r2 (pg1) | epyc8 .../pg1/.../signoff/signoff.json | routed sign-off record | TT setup -138.10, 318 violators, TNS -5917. FF setup -90.44 on 203 (fails at the fast corner too, so it is structure). Internal FF hold -11.24. TT OCV5 setup -230 |
| S81 col h9_r2 (pg2, pg3) | epyc8 .../pg2, pg3: run_route.log, ot_relay_mid_stations.txt, place_macro lines | relay station sites against macro origins | pg2: 63 stations fitted, 0 fallback, then `cp: error writing 3_place.odb: No space left on device`. rt_28b_1 (1063, 838) -> rt_28b_sk (942, 444): both x inside e14_w (x 864.1-1132.5, y 587.5-816), so the hop crosses the body again; rt_24b_3 / _4 sit 8 um apart and _4 -> _5 is 509 um. pg3: rt24b on y 820 then the east column x 1412; rt28b (852, 794) (852, 600) (1003, 557): clear of both macro pairs |
| QC cb pilot | epyc2 scratch3 fable-fix-qc-dieclk: setupP/setup_rows.tsv, setup.log, posout/pos.log, coords/coords.log | endpoint table (I re-classed it), stage-DB positions | 147 ends, WNS -302.85, 92 below -42. Classes: x_1_2 b_d -> a_d.r 63 (60 below -42), -> tap_d 44 (23), -> cap 13 (2); x_0_3 b_d 18 (3); `u_lk_nk_*_tap -> u_t*/tap` 4 ends at -159..-186; n_b 4 above -42. Positions: 3_3 b_d[460] (672, 129), r[0][460] (663, 1234); 3_4 both re-sited to (674, 532) / (675, 812) while inverter `_79485_` stays at (674, 136). Street x 540-690 util 2-8 % per band |
| S81 strip t47 | intel1 fable-fix-s81-strip/sta/t47_ov25td30_kitrc/setup_paths.tsv, rank.json; review_t47_corrected/review.png | 796 path rows (I re-classed them), placement render | 655 below -42. rrl -> fstart 6 / -1096 (wire 2,880 um, Manhattan 2,576, 28 buffers); rrl -> origin 3 / -539; origin -> reader_start 69 / -463 (1,558 um); **rrl -> rrl 134 / -232, all falling-edge launch**; driver_dv -> vp_cf memory 277 / -264 (Manhattan median 690 um, wire / Manhattan 1.15); vpw 283 / -249, **all from one pin `u_vs/x_wa[0]`**, Manhattan median 411, max 528, wire / Manhattan 1.88 |
| HEAD tile landing | epyc7 head-die-r/tp2/land1/pair/ep_base_{TT,FF}_*.tsv, plan.tsv | per-pin pair hold | FF -59.20 on 1,254 of 2,272 D pins; TT -44.42 on 496. Setup at those pins about 698 FF, so pads are affordable. Plan 1,575 pins |
| KV HG5 rows | epyc7 kv-clk-r2/rows_e9_hg3b: HG5_rows.json, offset.log, compose_receipt.json | sha, tolerance summary | sha 3ec72ddb1e41 matches. 56 types / 6,202 ports, half range max 16.0, p99 11.3, 0 over 20, tol max 26.1, seam 100, latency delta 0, overlaps 0 |

Not opened: every HEAD number except the tile pair; KV relay table; S81 H3p DB; rm3; QC M2 bind; all renders except t47.

## 2. Levers now, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: ordered rows + PG cap + wall-avoiding relay path as kit defaults; pg3 is the h9_r2 pilot | 203 col types | FABLE-FIX-S81-COL, S81-TYPES-R2 |
| 2 | S81 | strip: C4 bind with XR, CFR, START / FSTART rows, **and the half-cycle relay fix** | 75 leaf types | S81-DIE-R2, FABLE-FIX-S81-STRIP |
| 3 | QC | cb: re-site head hops after station siting (fb5250cc), pilot re-read | 18 cb types / 192 partitions | FABLE-FIX-QC-DIECLK, QC-TYPES-R |
| 4 | KV | HG5 e9 tap rows now; reset / START relay table adopted for HG6 | 50 unsigned KV types; KV die gate | KV-R, KV-CLK-R2 |
| 5 | HEAD | three landing legs, each with its own form (tile ring pads, region reset / START relays, sp4 -> sp3 fork) | HEAD die gate | HEAD-TILE-LAND, HEAD-DIE-R |
| 6 | S81 | SerDes: H4 in parallel with the H3p route | 11 serdes types | S81-SERDES-R2 |
| 7 | all | post-place detour check on zero-logic nets (new, from lever 3) | repeat of the cb class on any die | QC-TYPES-R writes it, wave owners adopt |
| 8 | all | final-mile hold ECO recipe (unchanged from 00:50 lever 7) | near misses | HOLD-FLOW-R |

### Lever 1. S81 col (203 types)

Root cause, three parts, all confirmed in kit data: unordered station rows (ir1: overflow 0 twice), PG cap over the station band
(pg1: DRC 0), relay stations whose hop crosses a paired-macro body (pg1: -138.10 TT and -90.44 at FF).

Fix.
1. pg3 form = h9_r2 pilot: `OT_RELAY_MID_RE [._]u_y_` + `OT_RELAY_POLY=1` + `OT_PGCAP=1`. pg2's fit without the wall-avoiding path
   is not a form: it measures a hop as Manhattan and put rt_28b_1 -> sk across e14_w. Do not relaunch pg2.
2. S81-TYPES-R2: `OT_RELAY_POLY=1` becomes the col default with the row emitter e943f1f62f4 in the next S81 tree. Add a fail-closed
   line to relay_mid: any relay hop whose straight segment intersects a macro body = FAIL before GPL.
3. C4 site rows (dispatch (C) of 00:53) are a pin of what pg3 chose. Do not hold the C4 bind for them.
4. ir1 at TT -31.70 is inside the gate but has 91 violators; the route can move it by 10 ps. If the routed read is below -42,
   read the path class first. No margin ECO before that.
5. Volume: h9_r1 (60) on ir1 routed sign-off; h9_r2 (60) on pg3 reloaded-GRT TT >= -42 and no rt_* end below -42; h10_r2 (12) on rm3.
   The r0_p* relay-depth groups stay behind their bind.

### Lever 2. S81 strip (75 types)

Root cause by class on t47 (V). Four structural classes, in endpoint order:
- vpw 283: one macro output pin `u_vs/x_wa[0]` drives 283 flops 411-528 um away. One net, one stage: XR at the bank is right.
- driver_dv -> vp_cf 277: 690 um, direct wire (ratio 1.15). Pure distance. CFR with XR is right.
- reset relay ladder 134 (97 below -42): falling-edge relay -> rising-edge relay at 363-387 um. **New.**
- START 69 and corner reset 9: single-cycle legs of 1,560-2,880 um. Rows exist (01:04, R).

Fix.
1. S81-DIE-R2 + FABLE-FIX-S81-STRIP, before the C4 bind: the reach script prices a falling -> rising relay pair at half the reach.
   Either both relays of a pair on the same edge, or hop <= 180 um for a mixed-edge pair (416 ps: about 60 clk-q + setup and
   0.9 ps/um on this kit's placement RC, which is what the 1,560-um START leg measures). The C4 reach report must print
   mixed-edge hops separately and show 0 above 180 um.
2. Check the new 01:04 rows the same way. Reader depth 9 with a 303 um worst hop and writer 335 um pass only if every hop is
   same-edge. If the emitter alternates edges, those rows fail by 100-150 ps as built. This is a question to the strip worker, not a result.
3. Rest as 00:50 lever 4: one full C4 bind with XR + 16 dswp copies + bank-end placement + CFR + lane reset copies on t34 / t62,
   t75 repack, FSTART local resets from the strict bind. All 75 after the t34 / t62 reloaded-GRT read.

### Lever 3. QC cb (18 types / 192 partitions)

Root cause (V on stage DBs). Global placement buffered the b_d -> a_d net while the two registers were 1,105 um apart. The kit then
re-sited both registers to 280 um apart and left the polarity inverter and the place* buffer chain where they were. Repair added
wire* buffers to reach them: 1,740 um of wire on a 280 um hop.

Fix.
1. claude/qc-nk-headhop-resite-1117 @fb5250cc (core_input_chain.tcl no longer skips shared head hops after re-siting), then the
   same pilot cbn_q01 from place. Pilot gate at post-CTS TT: no `b_d -> a_d / tap_d / cap` end below -42 **and** the four
   `u_lk_nk_*_tap -> u_t*/tap` ends (-159 to -186 today) at or above -42. They are a second class in the same table; if the branch
   moves only one of the two, the other needs its own re-site step.
2. Hold stays closed on this source (R: 526 -> 0 ends with 929 cells). Re-read it after the fix; fewer detour buffers shift arrivals.
3. No plan row, no cycle. QC-PLAN-R keeps N free of a cb station.

### Lever 4. KV: HG5 now, relays in HG6

HG5 = e9 compound rows on the D14 base, one bind. The packet is consistent (V). First D14 / HG5 pilot stops at the post-CTS FF gate
and prints cross-tap ends: expected under 200 on hgi (R projection 163).
One open reading: `clock.tap_window.per_port_ps` in the packet runs to 190 ps (median 56), while the offset log says tol max 26.1.
I did not resolve what that field holds (window including offset, or tolerance). KV-CLK-R2 states it in one line before the bind.
HG6: the 80-stage START / reset table (74 + 74 hops over 405 um, worst 2,996 um, R) gets relays at <= 380 um, and the same
mixed-edge rule as lever 2.

### Lever 5. HEAD: three legs, three forms

- Tile ring landing (V: FF -59.20 / 1,254 pins, die 11 ps worse): land1 pads (3,015 HB4 on 1,575 single-sink D pins) are the right
  size for a signed view with 698 ps of setup room. Longer term the contract is wrong, not the tile: sender data lands 23 ps after
  fclk against an 80 ps kit assumption. NF15e re-derives `OT_FWD_RING_MIN` from the pair read, or the next tile build repeats it.
- arst_n / start_i region seams about -1013 (R): a relay class, not a pad class. Reach-scripted rows in NF15e.
- sp4 -> sp3 START setup -396 (R): the two-FF clock fork; plan rows when the model is in, else NF15f.
- Stand-ins (ctl MCHK_LOCAL1, lep0N NF15e, serdes sd9e / sd9f, mesh on NF15e rows): unchanged from 00:50. lep0N reach read is blocked
  by 7 missing `rst_start_raw_*` ports in GEN35 (R); fix in the NF15e compose.

### Lever 6. S81 SerDes

H3p GRT TT -54.29 on `u_rck_transport4.q[544] -> u_syn.am_ok` (R). A routed read does not recover 12 ps on a predicate cone. Start H4
(predicate beside the alignment FSM, 0 cycles) now, beside the H3p route. J6c rows in C4. G4 still needs the PHY keepout replaced.

### Lever 7. Post-place detour check (new)

The cb class was read as reach for two rounds because nobody compared wire to distance. Check after 3_5_place_dp: for every
register -> register path with no logic cell, buffered path length / Manhattan > 3 and length > 400 um = FAIL_POSTPLACE with the
net name. Calibration on t47 (V): vpw 1.88 (fanout tree), dv 1.15, START 1.03: none trips. QC b_d[460]: 6.2: trips.

## 3. Stop list (changes only; 00:50 list otherwise stands)

1. QC: the cb station row / +1 cycle in any event; more cb setup repair; cb rollout before the fb5250cc pilot read.
2. S81 col: pg2 relaunch; any relay fit without the wall-avoiding path; holding C4 for hand-drawn outer-face rows.
3. S81 strip: C4 bind with mixed-edge relay hops above 180 um; treating "die reset 106" as one broadcast leg.
4. S81 SerDes: waiting for H3p routed sign-off before H4; quoting 5_1_grt.json (FF corner) as TT.
5. HEAD: hold cells on the n3_turn seams (tool pads, fixed); pads on the -1013 region seams.
6. KV: reset / START rows in HG5; HG4 on e8 rows.

## 4. Not checked

- Mixed-edge behaviour of the 01:04 START / FSTART rows: inferred risk from the t47 ladder, not read from the rows file.
- A per-pin STA probe of the t47 vpw and ladder paths was queued through ot-run on intel1 (16 GB, behind 44 waiters) and had not
  started at 01:30. If it runs, output is intel1 /srv/opentallas-scratch2/claude/fable-closure-strategy-0155/t47/run.log (PX / PXP lines).
- pg3 routed timing; ir1 DRT; rm3 (its read-back command was refused by ot-run isolation, lane log rc_rm3.log).
- fb5250cc itself (diff not read); whether it also moves the lk_nk -> tap ends.
- HEAD -1013 and -396 legs, KV 80-stage table, QC M2 bind and SC reset rows, H3p DB.
- ir1 FF hold -42.66 at GRT is port-start only by the policy record; the parent pair was not read.
