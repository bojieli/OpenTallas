# FABLE-TYPES-S81-COL 2026-11-14 ~20:00 PST: unclosed col_h9 / col_h10 types

Scope: col_h9_r0 p3 / p4 / p5, col_h10_r0 p1 / p4, and the r1 / r2 layouts of S81-COL-INHERIT (col_h9_r1 2, col_h9_r2 5, col_h10_r1 1, col_h10_r2 2 with a build on record; singletons cld01bb4ae, cl8b686b3e, clac068e56 have no GRT record and are skipped). p1 / p2 / p6 are in FABLE-HARD-S81 sec 3 and are cited only where new numbers change them.
Method: read-only. 366 distinct `5_1_grt` logs and 136 `4_cts_final.rpt` of the last 40 h on all 7 hosts, congestion reports, kit Tcl and bound RTL. No job launched, nothing changed. No col type is signed off.
Status words: MEASURED = read from a log, report or kit file. INFERENCE = fits the numbers, not proven.

## 0. The one finding that changes the plan for this group

Congestion is no longer what stops r1 / r2, and it is not the last wall for r0. Every col layout that gets through global route stops in timing repair on a clock cause (C1). All forms now running (density, M8 / M9, allow-congestion, max-wire) change routing only, so they end at the same place.

| family | GRT congestion today | where the build ends |
|---|---|---|
| col_h9_r2 (5 layouts), col_h10_r2 (2) | overflow 0 after 10-20 iterations | hold -245 to -287 ps on 5,571-8,628 endpoints, setup -360 ps; RSZ-0060 / GRT-0183 / time cap |
| col_h9_r1 clf32cde8d | overflow 0 at 27 iterations | in repair, same clock numbers at CTS |
| col_h9_r1 cl49d7a23e | 44 (M6 3) after repair_design, later kits 284-346 | GRT-0232 (kit without allow-congestion) |
| col_h10_r1 cl95b37463 | 44,569 (M6 40,502) | GRT-0116 (C4) |
| col_h9_r0 p3 | 157,505 (M6 142,102) | GRT-0116 (C5) |
| col_h9_r0 p5 | 66,314 (M6 57,368) | GRT-0116 (C6) |
| col_h10_r0 p4 | 62,197 (M6 59,928), old plan only | GRT-0116; no result on the current plan yet |
| col_h10_r0 p1 | never placed | Tcl error at place (C3) |

## C1. Hard cores on grid clock taps: tap spread 200-340 ps, structural hold and setup (all families)

MEASURED, kit epyc10 `kw43-wave-1109n/.../items/col_h9_r2__t1__cl87f3ff59/attempt_3/gen/...` (`4_1_cts.log`, `4_cts_final.rpt`, `5_1_grt.log`):
- 79 hard-core clock pins. 14 have an early core tap (`clk_c0..c13`, the element halves and the bf view cores; pin arrival -53 to -238 ps) and land at 283-324 ps effective against target 250.
- The other late cores sit on ordinary grid taps and carry 256-301 ps of internal latency: `bn10/11/12/14`, `bs10/11/12/14`, `n24/25/26/28`, `s10/11/12/14`, `t6/t7/t8_payload`, and the bf element `u_e13` (5 clock pins on `clk_t13`). Effective arrival 311-519 ps. The tool prints for each: "needs an early core tap (clock.taps kind core, clock.core_taps early; pair.py --core-taps)". 40 of 79 pins are outside target +/- 20 ps.
- OT_TAP_BALANCE then delays the flops of such a tap to follow its core. `clk_t13`: 12 delay buffers (274 ps) before the register tree, 250 flops at 427 ps (415-473). Tap means end at 226..427 ps, spread 201 ps.
- Worst hold path in the CTS report: core `u_e13w.u_view.u_c` (tap `clk_c11`, source latency -365.57 ps, clk-to-out 521.54 ps, data at 165 ps) into relay flop `u_y_rt_26a_0.u.o[58]` on `clk_t13` (clock at 426.65 ps): slack -295.85 ps.
- At GRT after wire repair (39,027 buffers): setup WNS -406.8 to -360.5 ps, 4,590 to 4,408 endpoints, 5,732 s of repair_timing, "Unable to repair all setup violations". Then hold: ws -245.64 ps, TNS -476,939 ps, 6,126 endpoints; 437 buffers later ws is -198 ps and the log ends at 3:11 h.
- Same class in every family (CTS logs of today):

| family (kit) | core pins / outside +/-20 | tap spread ps | worst core ps | CTS hold (clk min) ps | CTS setup (clk max) ps |
|---|---|---|---|---|---|
| col_h9_r2 cl87f3ff59, clce45cab5 | 79 / 39-40 | 196-201 | 519 | -296 to -306 | -610 to -625 |
| col_h9_r1 cl49d7a23e | 85 / 45-50 | 199-224 | 519 | -351 to -395 | -796 to -902 |
| col_h10_r1 cl95b37463 | 97 / 63-68 | 301-340 | 571-620 | -349 to -382 | -770 to -1,048 |
| col_h9_r0 p6 | 93 / 54-56 | 200-223 | 465 | -261 to -332 | -850 to -874 |
| col_h9_r0 p2 / p4 / p5, col_h10_r0 p4 | not read | not read | not read | -280 to -393 | -803 to -908 |

- GRT hold start in 8 other r2 kits: ws -251 to -287 ps, 5,571-8,628 endpoints; each ended RSZ-0060, GRT-0183 or at the cap after 1.0-5.8 h of repair_timing.
- `lanes/S81-TAPSKEW.tsv` (06:23 today) holds the same numbers for 66 kits (col rows: spread 162-220 ps, FF hold -257 to -394 ps, 8,564-11,371 endpoints). I found no plan event that acts on it for the col family.

Caveat: the CTS setup numbers are before wire repair and overstate setup. The hold numbers and the GRT numbers are after repair and are the ones to judge.

Dead ends: every form that changes only density, top layer, max-wire or allow-congestion (S81-COL-INHERIT forms a / b, TYPE-COLH10R1 fa-fd, TYPE-COLH9R1 g / h, wave relaunches). Padding 6,000-8,600 endpoints by 250 ps is 20-45 k hold buffers in channels that are already the congested part; that is what produces RSZ-0060 and GRT-0183 (net boxed in). Raising the buffer cap or the time cap does not change this.

Fix (DIE-S81-92, one clock event for all col bases; structural):
1. Give every core with more than about 100 ps of internal latency an early core tap, as the tool asks: in col_h9_r2 that is 26 more pins (bn, bs, n, s, t*_payload, e13 x5); the same core kinds in r0 / r1 / h10.
2. Raise `insertion_ps` of the 14 existing core taps by 33-74 ps ("early core tap still late").
3. Kit side (gen owner, INFERENCE that it helps alone): OT_TAP_BALANCE should hold every flop branch at the type target and never pad it to a late core. This is a side A/B, not the fix: a late core then misses setup on its outputs instead.

Proof in one build: col_h9_r2__t1__cl87f3ff59 (smallest, 72 k non-tap cells) to CTS only, about 2 h, under 10 GB. Pass = OT_TAP_CORE reports 0 pins outside +/- 20 ps, tap spread under 40 ps, and `OT_HOLD_GUARD_GRT start` under about 500 endpoints. Until that passes, one live build per layout is enough; more forms cost 15-21 GB each for 5-10 h and end at C1.

## C2. One register drives the flush / reset of the whole partition in one cycle (r2 measured; INFERENCE for the rest)

MEASURED, same kit: the worst setup endpoint through all 1,900 repair iterations is `u_bound.u_u_e13e.u_view.u_c/rst_n_pin`, launched by `u_bound.u_d7_6_Y.q` (last stage of a 7-stage `ot_dp_dly`). At CTS the same register gives recovery -440.78 ps on `u_y_rt_23b_0.u.o[21]` (arrival 1,415 ps) and the core setup -624.82 ps (arrival 1,267 ps, library setup 174.83 ps, core clock at about +9 ps against flops at 265 ps). Removal at CTS: -237 ps.
Not measured: the fan-out of `u_d7_6_Y.q` (the netlist was cleaned from the kit), and whether recovery / removal count in the R-MINIMAL setup / hold gate.
INFERENCE: about 250 ps of the -360 ps is the early core clock of C1; the rest is distance.

Fix (bind generator, with the C1 event): replicate the last stage of that delay chain per sink region (one copy per bf view core and per relay group), fed from stage D-2. No latency change, same function. Proof: same CTS-only build; the `asynchronous` max group and the `rst_n_pin` path at or above -42 ps.

## C3. col_h10_r0_p1: "unmapped flop in exact packed bank" is a generator bug, not a design failure

MEASURED, kit epyc8 `.../items/col_h10_r0_p1__t1__cl574cc59d__pv67036687/attempt_10/gen/...`:
- Bound RTL line 1378: `ot_dp_dly #(.W(1105), .D(1)) u_lpad_x_i0` (lane pad, latency table 26 cycles).
- `istations.tcl` line 305 calls `is_packed_exact_banks {u_lpad_x_i0} 1104 1 ...`; line 262 accepts only flop names `r[j][bit]`.
- With D = 1 yosys names the single stage after the output: the netlist has `u_lpad_x_i0.q[...]` and no `u_lpad_x_i0.r[...]`. The first flop, `q[0]$_DFF_P_`, raises the error 23 s into global place. All 4 failed identities (pv67036687, pvb095fa2f, pvf60ac9dc, cl911743eb) are this; pvd7af8531 is infrastructure.
- The earlier failures of this type today were other, already fixed, causes (LOCAL parameter, off-grid ft site).

Fix (gen owner / KIT-OPS-5, cc TYPE-FLOWERR-2): in the `is_packed_exact_banks` emitter accept `q[bit]` as stage D-1 (bit W is the epoch bit, as for `r`). No netlist change, so LEC identity is kept. Do not relaunch before it; it is blocked 3x already.
Proof: place of pv67036687 gets past line 38 of `3_3_place_gp.log` (under 1 minute into the stage). Any other type with a D = 1 packed lane pad fails the same way; a grep of `is_packed_exact_banks {.*} [0-9]* 1 ` over fresh kits lists them (not done).

## C4. col_h10_r1: a 5-stage, 1,265-bit lane pad marches along the 52-um strip under the bf wall

MEASURED, kit epyc10 `type-colh10r1/fa/col_h10_r1__t1__cl95b37463__pv799da6f8` (M8, allow-congestion): overflow 44,569; 2,509 congested gcells, all at x 680-900, y 0-120. Top nets: `u_lpad_frame_int_i1.r[1]` / `r[3]`, `frame_int_i1_q`, `u_lpl_11_w.q`, `u_e5e.u_view` rows.
- `frame_int_i1` enters on the south edge at x 6-276. `ot_dp_dly #(.W(1265), .D(5)) u_lpad_frame_int_i1` (latency table 11 cycles) has its stages sited by `istations.tcl` at y 0.0 and x 337 / 536 / 734 / 929 / 1,322: four hops of about 200 um, 1,265 bits each, in the strip between the die edge and `bf_col3_c` (x 691-899, y 52-250), where the wall leaves no M6 above the strip.
- TYPE-COLH10R1 reports form fc (density 0.4, M8, max-wire 200 / 220) at overflow 0 after 35 iterations (their post 19:3x; not re-read by me). M8 inside a col partition has no grant (FABLE-HARD-S81 sec 0), so a sign-off of fc needs the M8 track check.

Fix (DIE-S81-92, plan `internal_stations`): pad stages are pure delay and need not travel. Fold stages 0-3 into a bank beside the entry pins (x 6-330, above the south edge) and let only the last hop cross, or run the chain through the band north of the wall. Either keeps the 11 cycles. Same check for every `u_lpad_*` site list in the family (col_h10_r0_p1 has one at x 1,452.6; col_h9_r2 has `u_lpad_frame_int_i0`).
Proof: place + plain GRT on M7; target is the 2,509 gcells going to 0 without M8.

## C5. col_h9_r0 p3: the ft0_i landing band at the east edge

MEASURED, wave kit epyc7 `.../items/col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898/gen/...` (18:31 PST): overflow 157,505 (M6 142,102, max H 38). 5,191 congested gcells, 4,933 of them at x 1,400-1,440 and all at y 960-1,240. Nets: `u_bound.u_cland_ft0_i` ring and `ft0_i[]` pins, then `u_ist_frame_int_o0_0`.
This is the band of FABLE-HARD-S81 sec 3 (21.6 x 240 um for 6,147 ring flops, fill 1.041). New here: the plain form does not only fail OT_CLAND in CONS kits, it also fails GRT. The p3 routes now in iteration 12-22 and the p1 routes share it.

Fix: DIE-S81-92 B3x2d (band fill 1.041 to 0.52), already live. Nothing else to add. Proof: plain GRT of p3 on B3x2bd; target is the x 1,400-1,440 column going to 0.

## C6. col_h9_r0 p5 (p6 class) and col_h10_r0 p4

MEASURED, wave kit epyc10 `.../items/col_h9_r0_p5__t1__pvee6f8140/attempt_4/gen/...`: overflow 66,314 (M6 57,368). 6,940 congested gcells, all at y 1,080-1,240, x 280-960: the top strip over the bf wall. Nets: `u_bin_frame_int_i0`, `u_rrl_186`, `u_u_r0_u_lpl_0_r.o`, `u_ist_frame_int_o0_3`, `frame_int_o0_is3_q`. Same wall as p6 (FABLE-HARD-S81: 832 gcells at x 600-720), wider.
col_h10_r0 p4: 62,197 (M6 59,928) on the old B3v plan; its congestion report lists 45 gcells only, so the place is not established. The B3x2b forms fa / fb / fc and wave attempt 10 are at CTS; no GRT result on the current plan.
The p4 / p5 wave routes at iteration 18-24 after 9-11 h are the single-thread maze search of FABLE-HARD-S81 sec 3, not progress.

Fix: as FABLE-HARD-S81 for p6 (event B4: east-west M8 grant over front_roots and the top strip, or the frame_int_o0_3 polyline through the channel). p5 belongs in the same event. Proof: plain GRT of the p5 `3_place.odb` with the grant on.

## C7. r1 / r2 congestion is closed; two reading traps

- col_h9_r1 cl49d7a23e after the slot blockage: overflow 44 (M6 3) in 11 kits, and it appears only after repair_design. It dies on GRT-0232 because those kits have no allow-congestion. No structural work left here; kits generated after 18:30 pass this point and meet C1.
- In `s81-col-inherit/<tag>/<form>/` every log older than the form launch (about 18:2x) is a copy from the representative's wave kit, not a form result. Forms a and b of h9r1_cl49d and h9r2_clb8d show the wave failure with the wave timestamp.
- Form b sets M9. M9 inside a partition has no grant (FABLE-HARD-S81 sec 0).

## Order of work

1. C1 + C2 clock event and its CTS-only proof on col_h9_r2 cl87f3ff59. Nothing in this group signs off without it.
2. C3 one-line emitter fix; unblocks col_h10_r0_p1 today.
3. C4 lane-pad sites, C5 = B3x2d, C6 = B4, in the plan events already open.

## Not done

- No STA or GRT what-if was run (fleet memory); C1 item 3 and the C1 / C2 split of the -360 ps are inference.
- Fan-out of `u_d7_6_Y.q`; whether recovery / removal are gated.
- Core tap tables of r0 p2-p5 and col_h10_r0 (only the CTS slack groups were read).
- Location of the col_h10_r0 p4 overflow on the current plan.
