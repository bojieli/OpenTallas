# FABLE-PD-S81-2000 (2026-11-21 19:10 PST): svc hi4 fails placement on cut-bus order and macro-to-macro distance, not on the 17 um channel; START rows cover slice only

Reviewer: FABLE-PD-S81-2000 (Fable). Read-only: nothing built, cancelled, patched or deleted; no git in an owner checkout.
Marking: **V** = read or computed by me this round. **R** = reported by the named lane. **I** = inferred.
Earlier reviews stand: FABLE-PD-S81-1430, FABLE-CLOSURE-STRATEGY 18:30. Levers there are not repeated.
Measurements: three read-only ODB reads through ot-run on epyc7 (2 threads, 8 GB, stdout only; units oth-ubuntu-1410298 and two later ones) of the failed `3_3_place_gp.odb` of both hi4 pieces. Scripts: epyc7 and intel2 `/srv/opentallas-scratch2/claude/fable-pd-s81-2000/tmp/` (odbread.py, odbread2.py, odbread3.py; reach_j7el6.*; c2.py to c7.py).

## 0. Verdict

1. **svc hi4: both candidates miss the cause.** The cut-port flops already sit 5.8 um from their pins and the east strip holds 6 % of the cell area. The wirelength is in long reg-to-reg nets: cut buses whose pin window is far from both ends, and on the Att piece macro-to-macro nets of 1.3 to 1.5 mm.
2. **START rows: sufficient for slice_station in the plan (44 of 45 types), absent for serdes.** 104 types still have a writer START stage over 405 um, 38 a reader stage, 73 a raw reset hop over reach.
3. **c1x_C: one S strip cut at y 60.48 with 3 to 15 macro moves of 8.64 to 34.56 um per type.** For t9 that still leaves the body near 417k placed cells, so the xring landing must leave the body too.
4. **The "entry regs under face-touching macros" are not at the face.** Stage 0 of every north-entry svc slot sits 129.6 um inside the face by construction; two of them land in a macro. Both clear with a re-site of the register centre only.

## 1. svc hi4 PLACE-HPWL (owner OPUS-FIX-S81-SVC-R9)

### 1.1 What the failed placements contain (V, final `3_3_place_gp.odb`)

| | rest (unit 3854018) | att_fit (unit 3862334) |
|---|---|---|
| Outline, macros | 570.24 x 2747.52, 27 macros, x 43.2..553.1, y 69.1..1648.1 | 872.64 x 2747.52, 98 macros, x 13.0..857.6, y 86.4..2725.4 |
| Movable std cell area | 26,092 um2 = 2.7 % of the core | 29,135 um2 |
| HPWL at the stop / gate limit | 19.605M / 19.33M um (over by 0.28M) | 41.883M / about 41.4M um (over by about 0.5M) |
| HPWL at overflow 0.275 -> 0.197 | 14.87M -> 19.61M in 25 iterations | 31.83M -> 41.88M in 45 iterations |
| HPWL in nets of 405 um or more | 7.47M (38 %), 10,420 nets; 74 % of it vertical | 30.3M (72 %), 26,918 nets; 13,499 nets over 1 mm |
| HPWL forced by pins, macros and fixed cells alone | 0.98M (5 %) | 9.80M (23 %), 9.54M of it in nets of 405 um or more |
| GPL virtual worst slack | -1,479 ps | -1,799 ps |

- Cut-port registers: on every cut bus of both pieces the pin partner is a flop 5.2 to 5.9 um from the pin (rest east face: 13,422 pins, total pin-to-partner length 0.43M um = 2.2 % of HPWL). The exception is `o_u_rsv_09_Q_p`, driven by logic 53 um away.
- East strip of rest (x > 553): 1,509 um2 of movable cells, 5.8 % of the total, along 2,100 um.
- East channel width by y (macro edge to core edge): 90.6 um for y 0..535, **12.9 um only for y 536..795** (one macro, `g_l_1_u_sml`), 38.8 um for y 804..1063, 64.7 um for y 1071..1331, 341 um above, no macro above y 1648.
- The 1.306 density bin is at (565.1, 829), where the channel is 38.8 um wide. All eight worst bins are in the x 560..570 column, of which only 5.9 um is core; 107 of 7,957 bins exceed 0.7. It is a pin-column reading, not a channel squeeze.
- It is coincidence that 1.306 (density) and 1.32 (HPWL ratio) look alike.

### 1.2 Where the wire is (V)

Rest piece, cut buses on the east face:

| Cut bus | Bits | Pin window y | Other end in this piece (y p10 / p50 / p90) | Length |
|---|---|---|---|---|
| `i_u_rsv_09_Y_p_2` (in) | 1,196 | 1934..2100 | flops at 36 / 308 / 1640 | q nets avg 1,127 um; q + buffer nets 1.97M um |
| `i_u_rsv_09_Q_p_2` (in) | 1,204 | 1763..1931 | logic at 1177 / 1464 / 1685 | 0.62M um |
| `o_attn_o0_p` (out) | 1,592 | 406..712 | launch flops at 291 / 503 / 1175 | 46 % of sampled sources over 405 um |
| `o_u_rsv_09_Q_p` (out) | 5,740 | 900..1720 | logic at 823 / 1310 / 1643 | mean 125 um |

Att piece, same buses on the west face:

| Cut bus | Bits | Pin window y | Other end in this piece | Length |
|---|---|---|---|---|
| `o_u_rsv_09_Y_p_2` (out) | 1,196 | 1934..2100 | `u_lpad_attn_i*.q` flops at y 1175 / 1357 / 2072, x 478 | mean 1,043 um; 90 % over 405 |
| `i_attn_o0_p` (in) | 1,592 | 406..712 | flops at y 751 / 1217 / 2594 | 2.3M um; buffer nets avg 1,209 um |
| `i_u_rsv_09_Q_p` (in) | 5,740 | 900..1720 | 1,077 bits reach flops at y 5 (south face); **4,663 bits have no load** | 1.46M um on the live bits |
| `o_attn_i0_p` (out) | 1,078 | 254..404 | launch flops at y 286 / 900 / 1611 | mean 816 um; 77 % over 405 |

- `u_rsv_09_Y_p_2` is the worst case: sources at y about 1,357 in att, sinks at y about 308 in rest, window at y 2,017, above both. Its three hops today are 1,043 um / abutment / 1,127 um in one cycle each.
- Att has its own class, independent of the cut: `w_u_rsv_u_att_u_a_u_eng_*_Y` 5,233 nets at 1.40 mm average (7.30M um), `..._u_load_s` 2,555 nets (3.29M), `g_stage*.rd_data` 2,120 nets at 1.55 mm (3.28M). These are macro-pin to macro-pin: the 9.5M um fixed bound.
- Rest also carries one flop with fanout 9,736 over a 2,639 um box (`g_u_rsv_u_src_aa4db9e7..._q[0]`), and `cland_start` with fanout 136 over 1,859 um: the event 2 class inside this piece.
- Why GPL "diverges after converging": I did not isolate it. The composition above is measured on the final ODB; the last-25-iteration rise is consistent with spreading cells that are tied to nets of this length, but that step is I, not V.

### 1.3 Ranking

| Rank | Lever | Measured effect | Verdict |
|---|---|---|---|
| 1 | **Order the cut windows by endpoint position** (the window y is free; it only has to match on both pieces). `Y_p_2` to between y 310 and 1,350; `Q_p_2` to y 1,450..1,690; the live part of `Q_p` to the south end | Rest: `Y_p_2` alone is 1.97M um against an excess of 0.28M; about 1.2M um shorter gives 18.4M = 1.24x. Att: about 0.8M um on `Y_p_2`, up to 1.46M on `Q_p`, against an excess of about 0.5M | **Do first.** Pin track use on the cut face is 0.24 at worst (V), so windows can be packed |
| 2 | **Drop the dead cut bits** | 4,663 of 5,740 `Q_p` bits have no load in att_fit; 247 `attnh_o0_p`, 119 `Y_p_2` and 79 `Q_p_2` bits have none on their load side. Frees about 670 um of cut edge for rank 1 | Do with rank 1. First confirm in the att_fit netlist: the 98-site memory fit may have removed the loads, and then rest still builds their drivers |
| 3 | **Stations on the cut buses that stay long** | `Y_p_2` endpoints are about 1.86 mm apart (1,050 um in y plus about 810 um in x) even with an ideal window: 5 hops at 405 um, so +2 stages on 1,196 bits. `attn_o0` and `attn_i0` need the same read after rank 1 | Needed for timing whatever the HPWL gate says (+cycles pre-approved) |
| 4 | **Att macro order by connectivity** (core moves, no reshape) for the eng `_Y`, `load_s`, `rd_data` groups | 9.5M um is forced by macro positions; 1.3 to 1.5 mm unregistered | Att cannot sign without it or stations at those macro pins. Largest item; not in any posted plan |
| 5 | (b) Shift the macro block west | Only y 536..795 is narrow, and 1,900 pin flops there need about 0.6k um2 of the 3.3k um2 channel. The west margin is 39 um and carries 4,619 pins with their landings. HPWL effect: none measurable (east-face pin wiring is 2.2 % of HPWL) | **No gain.** Do not spend a layout on it |
| 6 | (a) Cut ports above the macro top | The ports already above y 1,650 are the longest nets in the piece. Moving `o_attn_o0_p` (sources at y 503) above y 1,610 adds about 1.1 mm x 1,592 = 1.75M um. No logic lives above y 1,700 in rest | **Negative.** Withdraw |

### 1.4 Entry registers on hi rs t1 / t6 ft3 (V, `j8/ft_resite/plan_ftresite.json`)

- All 13 north-entry svc feed-through slots have stage 0 at y = H - 129.6 (hi H 2877.12 -> 2747.5; lo H 2980.8 -> 2851.2). The macros are not at the face.
- t1 ft3 (1 bit): centre (251.22, 2746.52) is inside `g_m[3]...g_h4[1].u_h4`, x 207.36..311.04, y 2540.16..2799.36, 77.76 um below the face. Above the macro the window column x 244.6..257.8 is free to the face.
  - Fix: centre to (251.22, 2808.00). Hops: pin 69 um, stage 1 site 312 um.
- t6 ft3 (53 bits): centre (44.24, 2747.52) is inside `pmem_capture.b[1].s[1].ram`, x 17.28..109.94, y 2715.13..2756.48. The column x 37.4..51.0 has three free gaps: y 2756.48..2769.13, 2789.94..2810.17 and 2851.52..2877.12.
  - Fix: centre to (44.24, 2859.84), in the gap at the face. Hops: pin 17 um, stage 1 sites at most 238 um over two SRAMs with obs_max M4.
- Neither needs a window shift, a macro nudge or a cycle.

## 2. START and reset relay reach (V: `reach_rules.py check --rules 1,5,6` on the sealed J7eL6 plan, plan-site Manhattan hops)

- slice_station: 36 of the 45 types with a START fan carry rows, depth up to 11, worst stage 386.0 um. Raw reset hops over reach: 0 on every slice type (t29 clc7772371 81 hops, t6 cl0755c26e 95, all re-pointed to same-edge taps).
- **Missed:** `slice_station__t46` has no writer relay; `ft1_o` FSTART is 1,957 um from the origin.
- **Serdes: no new rows in J7eL6.** All seven STROBE ops are open: t3 reader and writer 3,327 um; t16 reader `ft1_i` 3,088 um, writer `ft0_o` 3,319 um; t4, t13, t15 cla2127225 writer 569 um.

| Family | Reader START over 405 (types / worst um) | Writer START | Raw reset over reach (rule 5) |
|---|---|---|---|
| svc | 15 / 4,049 | 16 / 4,087 | 0 (ring reset fan on 16, residual to 4,372) |
| serdes | 2 / 3,327 | 5 / 3,328 | 0 |
| c1x_C | 9 / 1,673 | 9 / 1,915 | 9 / 1,514 |
| lepe, lepw | 7 / 1,645 | 7 / 1,915 | 6 / 1,771 |
| col_h9_r0 | 0 | 48 / 1,100 | 2 / 689 |
| col_h10 | 0 | 11 / 1,100 | 0 |
| leaf | 0 | 0 | 50 / 2,003 |
| slice_station | 0 | 1 / 1,957 | 0 |
| kv_leaf, bk_sel t2, iqf, kv512_C, c3x_C, iq_C, eng, seqhost | 5 / 1,593 | 6 / 1,793 | 5 / 1,304 |

- Totals: reader 38 types, writer 104, raw reset 73, raw reset net missing 29.
- Leaf: the 50 are `fstart_k <- rst_rl_*`, a falling-edge relay into a posedge stage with a 180 um limit. This is the slice t29 class, unfixed on leaf.
- Placed proof: none on the J7eL6 form. t36 signed (+49.35) and t37 (+10.22 post-place, routed -50.1) are on J6r1 (R). The t18 kit never built (BIND-GEN-TOOLSKEW, R). No serdes kit with rows has been placed.

## 3. c1x_C strip/body split: core_move geometry (V on the J7eL6 plan; counts from the t9 WREG kit)

- "slice t9 486k" and "c1x_C t9 512k" are one type, `dsdv_slice_c1x_C__t9` (361,508 cells at floorplan, 499,775 placed, 512,092 after CTS). All nine c1x_C types are 1442.88 x 1226.88 with 47 macros.
- The 86k cells are the landing bands (S-face and ft-entry about 64.5k mapped, about 89k placed). Area is not the limit; band depth is. A band wants y 17.28..56.16 under its pin window, and at the 25.92 cut only 8.64 um is usable.
- Proposal: `strip_S` cut at **y 60.48**, macros kept at 69.12 or more from the S face, moves north on the 8.64 lattice, absorbed by interior channels. The opposite-face gap is unchanged on every type.

| Type | Limiting macros (gap now) | Moves north | Macros |
|---|---|---|---|
| t1 | cap, xr (34.56) | cap, xr +34.56; 3 sram64 +25.92; 3 sram256 +8.64 | 8 |
| t3 | cap, xr (34.56) | cap, xr +34.56; 6 sram64 +25.92; 3 rom +8.64 | 11 |
| t5 | cap, xr (34.56) | cap, xr +34.56; 2 rom, 3 sram64 +8.64 | 7 |
| t7 | cap, xr (34.56) | cap, xr +34.56; 8 +25.92; 2 +17.28; 3 +8.64 | 15 |
| t9 | cap (34.56), xr, sram64 (43.2) | cap +34.56; xr, 6 rom, 1 sram64 +25.92; 1 sram256 +8.64 | 10 |
| t6 | 3 sram256 (43.21) | 3 +25.92; 2 +17.28; 2 +8.64 | 7 |
| t10 | rom, sram256 (51.85) | 4 rom, 1 sram256 +17.28; 1 sram256 +8.64 | 6 |
| t4 (as a y cut) | sram64, rom (43.2) | 5 sram64, 1 rom +25.92; sram256 +17.28, +8.64 | 8 |
| t8 (as a y cut) | cap (34.56), xr (60.5) | cap +34.56; xr, 1 sram256 +8.64 | 3 |

- Strip: 1442.88 x 60.48 = 87.3k um2; the bands reserve 8k to 21k um2, so they sit at 0.5 use.
- Side effects: 0 to 14 clock taps per type end up under a moved macro and need re-siting (t1 13, t3 14, t5 13, t9 11); 2 internal-station registers on t10; 0 feed-through register centres. Each affected hop grows by at most 34.56 um.
- **t9 body:** with the S strip only it is about 302k mapped, about 417k placed: over the cap. With the xring landing out as a second strip on its face it is about 378k to 382k placed. That second strip is cheap on t3, t7, t6, t4, t8, t5, t9 (0 to 5 macros) and large on t1 (29) and t10 (20).
- Rejected: a cut at an interior channel (the only wide one, t3 y 459.59..552.96, puts the `xgt_xo` SRAMs in the strip); a rigid shift of all macros (N gap 34.56 to 53.96 on t3, t7, t9).

## 4. Repeat failures since 13:00 (V, autopilot/log.txt)

| Class | Attempts | Evidence | Lever |
|---|---|---|---|
| svc hi4 pieces | 3 (units 3500509, 3854018, 3862334) | PLACE-HPWL 1.32x each | Section 1; no fourth run on this cut list |
| col_h9 r1 / r2, routed and not signed | r2 clce45cab5: TT -272.69 -> -228.78 after 3 ECO rounds, 19.6 h. r1 cl49d7a23e: OOM 15:15, then TT -291.52, FF -11.09 | Same reset and ROM-pin classes as strategy levers 2 and 5 | No new lever. ECO cannot close -230 |
| col_h9_r0 route | p2 cl9f71e63d DRT-0255 no path (attempt 2); p1 pva2e3974f GRT-0116 (attempt 3) | Strategy lever 4 (xo NOFIT) | Held with col |
| slice_station place stop | t6 cl0755c26e and t29 clc7772371 at attempt 8; t18 at 6 | START and reset class; rows are in J7eL6 | Wait for the J7 apply; no J6-event relaunch |
| Post-CTS stop | leaf t11 setup est -381.24, hold est -153.13; slice t51 -173.87 / -107.37 | leaf: rule 5 class of section 2 (I, path not read) | Section 2 |
| serdes geom | t16 attempt 3 and t14 attempt 5 AUTO-GEOM FAIL; t16 exit 78 | START rows missing | Section 2 |

## 5. Ranked levers and owners

| # | Lever | Owner |
|---|---|---|
| 1 | hi4: re-order the cut windows by endpoint y, drop the dead cut bits, then re-split. One place-only pair to confirm before anything else | OPUS-FIX-S81-SVC-R9 |
| 2 | Rule 1 and rule 5 as J8 GEN steps for serdes (7 ops), svc (16), c1x_C (9), lepe (7), leaf rule 5 (50), col writer (59), slice t46 | FAM-S81-SERDES-R6, OPUS-FIX-S81-SVC-R9, FAM-S81-SLICE-R5, FAM-S81-LEPE-4, FABLE-FIX-S81-LEAF-R7, FAM-S81-COL-H9R0-R4, FAM-S81-COL-H10-R4; rows to S81-J6-ASSEMBLY-R5 |
| 3 | c1x_C core_moves of section 3 as J8 rows, with the tap re-sites; second strip for the xring landing on t9 | FAM-S81-SLICE-R5 (geometry), FLOW-STRIPBODY-R2 (bind and gen path), S81-J6-ASSEMBLY-R5 |
| 4 | hi4 att: stations or macro order for the eng `_Y`, `load_s`, `rd_data` groups; +2 stages on `Y_p_2` | OPUS-FIX-S81-SVC-R9 |
| 5 | hi rs t1 / t6 ft3 stage-0 centres to (251.22, 2808.00) and (44.24, 2859.84) | OPUS-FIX-S81-SVC-R9 |
| 6 | One J7eL6-form slice proof (t18) once the tree is rebound on the gen rt | FAM-S81-SLICE-R5, S81-J6-ASSEMBLY-R5 |

## 6. Stop list

1. No hi4 layout for "cut ports above the macros" or "macro block west".
2. No fourth hi4 place run on the present cut list, and no GPL overflow or HPWL-ratio setting change as the answer.
3. No reading of the 1.306 bin as a channel width problem.
4. No window shift or macro nudge for the t1 / t6 ft3 entry registers.
5. No serdes volume or proof kit without START rows; no relaunch of slice t6, t29, t18 on the J6 event.
6. No c1x_C strip split at the present 17 to 43 um depths, and no t9 body build with only the S strip out.
7. No further ECO rounds on col_h9 r1 / r2 at -230 to -290.

## 7. Not checked

- The step that makes GPL HPWL rise between overflow 0.275 and 0.197 (only the final ODB exists).
- Whether the 4,663 unloaded `Q_p` bits are intended in att_fit; whether rest and att_fit agree on the cut list (bind, LEC).
- Whether the att macro-to-macro nets are registered inside the macros (then they are a length cost, not a timing one).
- Cut-window re-order feasibility against FT slot ends and the `L*` cut ports of type_split.
- Reach numbers are plan sites, not placed paths; rule 5 `--reset-tree` not run; the "72 keys / 25 types" count is R.
- c1x_C: `core_conns` and abutment pins of cap and xr after the move; a second split of a body piece in type_split; per-piece counts are extrapolated from t9.
- Cause of the leaf t11 and col_h9_r1 paths (class assigned from earlier reads, not from these runs).
