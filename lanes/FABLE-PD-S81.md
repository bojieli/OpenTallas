# FABLE-PD-S81 2026-11-14 22:20 PST: S81 physical-design review (B6c / B6c4_cg / B6d, col families, leaf, die GRT)

Reviewer: Fable, read only. Nothing launched, nothing changed. Plan data read from epyc7 `s81-b3-clk/ev/*.json`; kit data from
the wave runs `kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items` on all 7 hosts (266 col attempts and 181 leaf attempts
of the last 30 h). One in-memory dry run of `reset_replicate.py` on a bound r2 module (no file written).
MEASURED = read from a plan, log, report or source file. INFERENCE = fits the numbers, not proven.

## 0. Verdict

- No col type and no leaf type has finished detail route. Col builds end in GRT (clock taps, wall congestion); leaf builds end
  at DRT-0255 and would then fail TT setup. The wave still builds the pre-B6 plan, so none of today's fixes is in any kit.
- B6c, B6c4_cg and B6d are structurally sound in what they change, but all three binds will stop at the same line that stopped
  B6a and B6b (lever 1). Until that is fixed no B6 content reaches a kit.
- B6c C1 removes most of the col clock problem but leaves the 8 element halves per type 41-80 ps late by construction (lever 2).
- The col floorplan itself is the second wall behind the clock (lever 3). Leaf: three known walls unchanged, plus 69 types
  whose cores still sit behind their pin windows after the B6 leaf delta (levers 4-6).

## 1. Levers, ranked by types unblocked

| # | lever | types | owner |
|---|---|---|---|
| 1 | dead-input re-proof under the 26-define list, then re-run bind only | all B6 content: 251 changed types | DIE-S81-92 |
| 2 | col clock: finish C1 (cap at 250 ps, 6 understated taps) | 216 col | DIE-S81-92 |
| 3 | col re-floor: streets, face clearance, wire rule over macro rows | 216 col (84 need more than a shift) | DIE-S81-92 + new lane S81-COL-STREET |
| 4 | leaf tap window in the kit SDC | 79 leaf / kv_leaf | KIT-OPS-5 / KIT-OPS-6 |
| 5 | leaf PG keep-out into `die_gen_env` s81 | 79 leaf (every leaf route ends DRT-0255) | PG-AWARE-1 + KIT-OPS-5 |
| 6 | leaf block shift off the pin faces (F1-F3 of FABLE-LEAF-FTSLOT) | 69 (64 have room for a rigid shift) | S81-LEAF-PLAN |
| 7 | C2 `rest` region split | 60 col_h9_r2 | S81-COLGEN-1 |
| 8 | C4 proof GRT before volume | 12 col_h10_r1 | S81-COLGEN-1 |

### Lever 1. B6c, B6cg and B6d will end BIND_RC=2: "stale dead-input preprocessor defines" (MEASURED)

- `run/b/B6a/bind.log:2` and `run/b/B6b/bind.log:2`: `bind: ERROR stale dead-input preprocessor defines`
  (`log/B6a.log`: G0_RC=1, ELAB_RC=0, BIND_RC=2; same in `log/B6b.log`).
- Gate: `tools/die_plan/dead_inputs.py:104`. A re-proof counts only when it was made under exactly the manifest defines
  (`_reproof_matches`, line 68).
- The only re-proof passed (`REPROOFS=results/token_pass/s81_dead_inputs_2148/proof_rsttree_reprove_1114.json`) lists 21
  defines, ending at OT_S81_SERDES_RST_TREE. The manifests (`run/b/<tag>/asbuilt_run.json`) have more:
  B6a +3 (TXPIPE, RXPIPE, GUNIT_FWDOWN), B6b +4 (RXNEG), B6c / B6cg / B6d +5 (OT_SVC_ATT_MEM_MACRO).
- `dead_inputs.py` and the re-proof file are byte-identical in B6b, B6c and B6d trees (md5 c6f136c7 / 840cfb82).
  So the three live chains (G0 stage at 22:18 PST) reach the same error about 70 minutes after their start.
- Fix: run the dead-input prover once under the 26-define list of B6d, add that file to REPROOFS, and re-run the bind step
  with ELAB_FROM (no new G0, no new elab). Do it before the three chains end; nothing else in B6 can be judged before.
- Not a physical finding, but it is the deterministic cause that every B6 event has failed so far.

### Lever 2. Col clock (C1 in B6c2): right fix, two gaps (MEASURED)

What B6c2 does: 7,796 early core taps on 220 types (`b6c2.py`, `early_core_taps.add(common_ps=250, merge=True)`).
In col_h9_r2 it adds the 24 pins the kit asks for (bn, bs, n, s, t*_payload, e13 x5; internal 256-301 ps).
Today's kits, all families: `OT_TAP_CORE 79-104 core clock pins, 38-63 outside target +/- 20 ps` (266 attempts, none better).

Gap a: the element halves cannot be made early enough.
- Kit `core_taps.txt` (col_h9_r2 clce45cab5 pvb3258867 attempt_5, epyc7): `clk_c0 u_e10_u_w clk 250 532.993`,
  `clk_c1 u_e10_u_e clk 250 553.179`. The early offset is capped at the common latency 250 ps; the cores need 283 / 303.
- `4_1_cts.log:1944-1957`: these 8 pins land at effective 291-330 ps ("pin -223..-242 + internal 533 / 553"), 41-80 ps late.
  merge=True keeps these rows, so B6c does not change them. They are the largest cores of every col type (8 x 268 x 221 um).
- Fix: none by tap value. Either the 12 col bases get a type target of about 310 ps (flop taps +60, halves then inside
  +/- 20), which G0 R4 forbids today (`b6c3.py` comment: insertion_ps must equal die common 250), or the residual is accepted
  and the hold cells go to the half input pins only. COORD decides; my recommendation is the type target, because the col
  tiles abut each other and their other faces are landed.

Gap b: six existing taps are understated.
- Same log: `u_view.u_c` internal 476 ps against plan 435 (effective 291); `u_ha` / `u_hb` internal 336 against plan 303
  (effective 283). B6c2 leaves them. Fix: set insertion_ps to 476 and 336 in the same event (both stay under the cap).

Also in the plan: 8 taps `u_eN.u_{w,e}.ck` at 465 ps (ROMQ-SPLIT-1106) beside the 8 `.clk` taps. The kit lists no `ck` pin on
these halves. INFERENCE: stale rows; check that the die clock tool does not build 8 landings per type for them.

Proof (one build, as asked on 11-14 20:00 and not yet run): col_h9_r2 cl87f3ff59 to CTS on the B6c plan. Pass marks:
`OT_TAP_CORE` at most 8 pins outside (the halves) with gap b fixed, tap spread under 90 ps, GRT hold start under 1,500
endpoints (today 6,126-8,628 at -245 to -287 ps).

New failure mode to watch: 7,796 more die clock landings, each with its own offset. The die GRT prototype runs on B3x2d
and does not contain them. Re-run it on the B6 plan once bound.

### Lever 3. Col floorplan: the buses run where the macro rows are (MEASURED geometry, INFERENCE for the fix)

Numbers from plan `B6c4_cg.json`, all 216 col types:
- Macro area 46 % (median), up to 55 % (col_h10_r1); standard cells fill 2.7 % of the free area (p2 attempt_7 auto_geom).
  Area is not short. It is cut into strips.
- Core distance to the faces, median: W 17.3, E 42.7, S 43.2, N 43.2 um. No col type has a free side.
- 144 of 216 types have a core closer than 86.4 um behind a window of 512 bits or more (rule R-LEAF-2b applied to col):
  bf wall core `u_c` behind the N window in 144, a node behind the E window in 66, an element half 17.3 um behind the
  W `xo_o0` window in 36. A rigid shift has room in 60 types; 84 need a row re-stack.
- Core-to-core slots 4.3-43 um wide: median 2,611 um of slot length per type.

col_h9_r0_p2 as the example (cl9f71e63d pva4376595, 84 macros):
- Rows span x 17-1115 with one 25-um break (x 553-579): ROM row y 69-132, elements 216-437, ROM 458-521, elements 648-869,
  ROM 916-979, bf wall 993-1192. Free streets between rows: 84, 21, 127, 47 and 15 um; N strip 86 um.
- `ft0` (1,104 bits, E to W) has its windows at y 981-1221, on the wall row. The two `bf_col3_c` cores block M1-M6 over
  2 x 208 um, so `ft0` has no horizontal layer there and runs in the N strip (its bit sites are at y 1251).
- `frame_int_o0` (1,167 bits) starts at (1410, 674) and leaves through the N face at x 6-260: 3 station ranks at y 1226.9.
- So the 86-um N strip carries 2,271 long east-west bits plus about 10 station ranks. M2 + M4 + M6 there give about
  5,550 tracks before the PG derate (26-31 % in `geom/grt.log`). This is the dense N band of the render, and the place of
  the p5 / p6 overflow (60,676-66,314, top strip over the wall, `5_1_grt.log` of pvee6f8140 a4, pvea45abf3 a5).
- `xo_o0` (1,104 bits) leaves on the W face at y 740-980 with element `u_e2.u_w` 17.3 um behind it. auto_geom:
  pin-to-register p90 207 um, max 376 um; 7,385 captures over 405 um, worst 1,321 um (`u_y_xo3_0 -> u_y_xo3_1`).
- E face: 2,565 pins on 47 % of the face with the node columns 43 um behind: the E pin band of the render.
- Repeaters: 164,628 cells at place (attempt_7) against 294,448 at GRT (tl-colh9r0p2/ff, FABLE-HARD-S81), +79 %. The
  100-um wire rule cannot be met over a 536-um element pair, so the repeaters and the hold cells all go into the strips.
  That is what ends in RSZ-0060 and GRT-0183 (r2: 9 attempts today) and GRT-0116 / 0232 (r1: 71 attempts, 26,865-31,506).

Root cause: the row arrangement was made for the cores; the four 1,100-bit bus windows and their station ranks got the
leftover strips. The M8 grant (p5 / p6) and the R-COL-2 slot blockage treat single strips.

Fix, one event for the 12 col bases (moves only, core shapes kept; owner pre-approved re-floor):
1. Two full-width streets of 130 um or more: abut each ROM row to the element row it serves (the 21-, 47- and 15-um
   strips go away) and give the freed 83 um to the N strip and the mid street.
2. Wall row at least 60 um lower, so `ft0` and `frame_int_o0` get a 146-um N strip; or stations of `ft0` on both sides of
   the wall with M6 over the `bf16_half` and `front_roots` cores (obs M5).
3. Element rows at least 60.5 um off the W face where a 1,104-bit window sits behind them (36 types); E node columns
   86 um off the E window (66 types).
4. Kit: nets between two station ranks that cross a macro row take a slew / drive rule, not the 100-um rule.
Tool: `core_place.py --face-clear W:60.5 E:86.4 --window-clear` plus a street term; today it has neither a row abut nor a
street objective, which is why the lane is new.
Proof: plain GRT of the p2 `3_place.odb` after the move, M7 top, no M8. Pass: overflow 0, cell growth at GRT under 30 %.
A 1-h A/B on the existing p2 `4_cts.odb` (max wire 100 against 300) tells first how much item 4 gives alone.

### Lever 4-6. Leaf: nothing has changed in the kits (MEASURED)

- t69 attempt_7 (epyc7, kit of 14:36 PST, routed 19:50): `config.mk:51 OT_TAP_WINDOW = 162`, 52 early source latencies in
  the SDC, no `OT_PG_CELL_KEEPOUT`; `5_2_route.log:325` DRT-0255 at x 38.8, y 549.5 (W strip, `u_ft_ft1_o_2`);
  `postcts_gate_TT.log` setup -201.47. Same three walls as FABLE-TYPES-S81-LEAF found at 20:00.
- Last 30 h, 181 leaf attempts: 4 reached detail route (t25, t42, t69 x2), all DRT-0255 in iteration 1 with 24,334-31,552
  violations; 13 attempts on 10 types ended RSZ-0060 in GRT hold repair (-12 to -108 ps left); 8 GRT-0116; 0 finished.
- Plan after the B6 leaf delta (`B6c4_cg.json`, 79 leaf / kv_leaf types): 72 types have a core closer than 86.4 um behind a
  pin window, 48 closer than 43.2 um, 69 behind a window of 512 bits or more. 73,850 pin bits sit behind a core under
  43.2 um. Core-to-core slots of 4.3-43 um: median 3,269 um per type. So classes L2 / L3 are still in almost every type.
- 64 of the 72 have room for a rigid block shift: median free side E 88.6, N 127.4 um; 42 types have an empty side of
  250 um or more. No room on one axis: t1, t9, t14, t47, t62, t65, t72, t75.
- t54 cl501e5681 (the render): cores at x 43-1102, E 341 um empty, S clearance 17.3 um with `leafdn_i0` (597 bits) 34.2 um
  and `leafup_o0` (668 bits) 42.8 um in front of lane cores. All data pins are on S and N at x 6-724. 34 taps: 16 grid +
  18 explicit; the E grid column drives 1-11 sinks while `clk_t29` has 3,217 (plan `tap_max_sinks` 1500). t54 a2 ended
  RSZ-0060 with hold -75 ps on 3,202 endpoints.
- Why the plan did not move: the four `core_place` causes of FABLE-LEAF-FTSLOT section 3 (restore-all, one face per
  sweep, station repair reverts face clusters, `--take-regs` excludes bus rows). F1-F3 are not in the tool yet.

Fix order for leaf:
1. Lever 4: tap window over data-related taps only (`die_sta_related --kit-window-out`), and one landing per leaf with a
   local tree. No leaf route passes TT setup without it (13 of 13 builds at -164 to -267 ps).
2. Lever 5: PG keep-out in `die_gen_env` s81. No leaf route passes iteration 1 without it.
3. Lever 6: F1-F3 in `core_place`, then one block-shift event for the 64 types (+1 on leaf bus rows where needed,
   pre-approved). For types with an empty E third, shift the block east and north until W / S clearances reach 86.4 um.
4. Taps: drop grid taps with under 50 sinks, split taps over 1,500 (t54 `clk_t29`, t40 `clk_t32` 3,020, t24 `clk_t6` 3,922).

## 2. Plan events

### B6c (ev/B6c4.json): sound
- Changes against B6c1: 251 types. C1 taps on 220 types; 14 TX latency rows back to B3z2sc2; serdes `tap_group`;
  16 svc types get OT_SVC_ATT_MEM_MACRO; 15 landing bands densified (bk_sel, eng, iqf, seqhost).
- G0 of B6c4 (`run/b/B6c4g`): 252 errors against 250 in B6a, same classes. New: 4 hop errors (dn_s_2N_L0 hop 532 um,
  dn_s_6N_L4 454 um, xtier__seqhost__bk_sel 494 um, sid_s_0S_C__s_0N_C 540 um) and the cut error moved to s_6S_L0 (0.63).
  The first two are new lanes over reach; they came with the leaf delta and need a station each.
- Gaps: lever 2 a and b.

### B6c4_cg (S81-COLGEN-1): sound, two items
C2 `reset_replicate` on 60 col_h9_r2 types:
- Dry run on the bound module of clce45cab5 pvb3258867: driver `u_d7_6_Y` (D 7), 112 loads, 70 regions without core
  positions. Latency stays 7 for every load; the copy cell `ot_dp_rrelay` is a plain posedge flop (`gen_rtl.py:132`).
  Only one driver matches per type, so the stale-index case in `apply()` (second hit after an insert) does not occur here.
- Gap: all `assign` loads share the region "rest": `w_14_Y` and the flush bit of `w_u_e10_0_Y`, `e11`, `e12`, `e14`.
  One copy still drives the four element pairs in the four quadrants in one cycle, into cores whose clock is 223-242 ps
  early. The measured worst endpoint (`u_e13e.u_view.u_c/rst_n_pin`) gets its own copy; the elements do not.
  INFERENCE: they become the next worst setup path. Fix: region of an `assign` load = its left-hand wire (4 more copies).
- Proof: same CTS build as lever 2; the asynchronous group and the element `Y` pins at or above -42 ps.

C4 lane pads on 12 col_h10_r1 types:
- `frame_int_i1` (1,264 bits) now runs S strip x 141-641, north at x 641 through the 56-um channel between
  `front_roots` (x 518-635) and `bf_col3_c` (x 691-899), then east at y 300.6. Hops 189-377 um, 5 stages, 0 cycles added.
- The y 300 line crosses `u_t4`, `u_t4__payload`, `u_s7`, `u_n14` and `u_bs7` (all obs M5), so only M6 is open there. The
  free corridors are y 251-294 (43 um) and y 324-371 (47 um). 1,264 bits need about 28 um at full M2 + M4 + M6 use: it
  fits at about 65 %. The 56-um channel takes the bus at about 50 % of M3 + M5 + M7.
- New failure mode: that channel is the p6 hot spot (832 gcells at x 600-720). Stage 2 (1,265 flops at 641, 66) sits in
  its mouth. Run the proof GRT (place + plain GRT, M7) on one col_h10_r1 before the 12 types build. If the mouth
  overflows, put stage 2 at (641, 20) in the S strip and stage 3 at y 270, clear of `u_t4`.

### B6d (B6c4_cg + eng__t1 core move): sound
- `u_eng.u_e` moves 77.76 um south and flips R0 to MX (shape kept); `h0` / `h1` move with it; top edge now 121 um under
  the N face. The `ft0_i` band grows 6,423 to 14,165 um2 (10.35 um2/bit) at y 1119-1166. Stations kept (4 registers).
- It targets the measured cause: eng attempt_7 GRT-0116, 36,705 overflow, 88 % ring nets (FABLE-WAVE-REVIEW).
- Remarks: the band is 60.5 um under the face (R-LEAF-1 limit exactly), hop 261 um. RUDY V stays 142 k (-7 %), so the
  move is a band fix, not a congestion fix: judge it by one GRT of eng__t1, not by the RUDY line.
- Wirelength +18.6 % (162 to 192 bit-mm) is the price of the clearance; no timing violation reported, eq OK.

## 3. Die GRT prototype (DIE-S81-GRT0)

Not landed. epyc8 `die-grt0-s81/s81/b3x2d`: started 21:44 PST, clock kit at 37 of 98 DME regions after 23 min
(`tree/kit.log`); no GRT or STA output yet. Expect about 1.5 h more. It runs plan B3x2d with plan-shape abstracts, so it
answers die routability and regional clock on the old tap set, not the B6 taps (lever 2).

## 4. Stop list

- More col wave attempts on the pre-B6 plan: 266 attempts in 30 h, every one with 38-63 core pins off target. r2 ends
  RSZ-0060 / GRT-0183, r1 GRT-0116 / 0232, p5 / p6 GRT-0116 at 60-66 k.
- Forms that change only density, top layer, max wire or allow-congestion on col (already in FABLE-TYPES-S81-COL).
- Raising `insertion_ps` of the element-half taps: the offset is capped at 250 ps.
- Waiting for the B6c / B6cg / B6d binds as launched: they stop at `dead_inputs.py:104`.
- Leaf routes on kits without the PG keep-out and with OT_TAP_WINDOW 68-162 (t69 a7 is the fourth proof).
- More stations in leaf feed-through slots, and M9 over leaf cores, as a slot fix (FABLE-LEAF-FTSLOT).
- Judging the eng move or any core move by RUDY alone.
- M8 grant as the col answer: 750 tracks at 4w over a 240-um window against 2,271 bits.

## 5. Not done

- No GRT or STA run of my own; the col fix of lever 3 is geometry plus inference and needs the proofs named there.
- The G0 reports of B6c / B6cg / B6d (still running); bound RTL of B6cg.
- ROM-to-element pin sides (needed before abutting ROM rows); die clock capacity for the 7,796 added taps.
- Hold-cell count that 41-80 ps on the element halves costs after C1.
