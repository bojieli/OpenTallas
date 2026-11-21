# FABLE-PD-S81-0440 (2026-11-21 04:55 PST): structural review of the S81 J7 plan event as one whole-die event

Reviewer: FABLE-PD-S81-0440 (Fable). Read-only. Nothing cancelled, signalled, patched or launched; no ot-run job used.
Marking: **V** = I read the file or computed the number this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Thresholds: the brief says hops 405 um, `rules.txt` says 300 um. Both counts are given.
Scripts and raw outputs: localhost scratchpad `pd0440/` (`an1.py`, `an2.py`, `an44.py`, `an5.py`, `an1.out`, `an2.out`).
Base for every V number: J6 plan = `epyc10 s81-j6/candC1n` plan 44be6051 (395 types, 398 partitions, 873 lanes, die 32,693.76 x 25,980.48).

## 0. Headline

1. **J6 is already applied (C1n, 04:15, event dc92652f0d5), and its post-apply strict bind FAILED (V).** `postbind-s81-1121041234`: ELAB_RC=2, BIND_RC=2, LATCHECK_RC=1, 04:17. A fresh C1n elaboration is refused on a stale svc PORTFIX overlay (`dsdv_svc_rs_pvso_entry.sv`; V in `s81-j6/logs/tokc_c1n.log`, I for the postbind log, which prints only the rc). So the live tree cannot be re-elaborated, and no token program exists for it. J7 must not be gated on this base as it stands.
2. **J7 is not one row set yet. It is at least 30 delta files on at least four different bases (V):** C1n (RDX, FT v3, t40 straps, kv_leaf t5), C3g / H8 (svc split `plan_c`, t45 straps), J5 (leaf lever 2, leaf local resets, col relay rows, col_h10 bn rows), a private tree (bk_sel). The 16 C3g deltas that J6 dropped (svc H8, vp_sr, CFX, FSTART, leaf keys, reach1, ROM pval, lepe / f0_q) are J7 inputs too and are not in the brief's list.
3. **The first composed J7 candidate failed: `candJ7RDX` (C3g + RDX) strict bind errors 360, BIND_RC=1, 04:45 (V).** Two line classes in `gates/candJ7RDX/bind.log`: 30 types (col_h10_r1 12, col_h10_r2 12, col_h9_r0_p3 6) where 139 RDX rows match no internal sink, and 565 `RESET_ANCHOR ... moved` lines. I did not break the 360 down further. `candJ7RDX_C1n` and `_FT` were still in bind at 04:46.
4. **Six hard conflicts between row sets (section 2).** The two that lose work silently: the RDX donor replaces the whole `relay_depth` and `relay_sites` key on 216 col types and drops all 2,573 ROM-pval rows; and `vp_sr` / `reach1` rows put 100 + 7 register sites inside the lane cores that leaf lever 2 moves.
5. **J7 as listed fixes one type in four of its families:** leaf regrid 1 of 75 types (t44, bind only, kit stopped at gen), svc split 1 of 16, col relay rows 6 of 216, c1x_C split 0 of 9 (no rows). TAP-GRID contributes no rows (t39 FAIL).
6. **Safe by construction is not met on col (V):** 385 plan `relay_depth` rows have a segment over 405 um (col_h9_r0 300 rows on all 60 types, max 594; col_h10 85 rows on 24 types, max 566). The RDX donor leaves all 385 unchanged.

## 1. Safe-by-construction census of the J6 plan (V, plan level; `an1.py`)

| Family (types) | station hops > 300 / > 405 | relay_depth segments > 405 (types) | tap_max_sinks | Cells (R) |
|---|---|---|---|---|
| col_h9_r0 (60) | 504 / 0 | 300 (60), max 594 | 3,000 | under cap |
| col_h10 (36) | 306 / 0 | 85 (24), max 566 | 3,000 | under cap |
| col_h9_r1 (60) | 416 / 0 | 0, max 280 | 3,000 | under cap |
| col_h9_r2 (60) | 180 / 0 | 0, max 262 | 3,000 | under cap |
| leaf (75) | 3,883 / 0 | 0 (t44 has 4 rows 206 to 218) | 1,000 | t5-class band 335k |
| kv_leaf (5) | 33 / 0 | 0 | 1,000 / 1,500 | t2 never synthesised |
| slice_station (46) | 0 / 0 | 0 | 1,500 | t36 287k |
| c1x_C (9) | 0 / 0 | 0 | 1,000 / 1,500 | 477k to 503k: OVER |
| svc (16) | 0 / 0 | 0 | 1,500 | 3.3M to 5.1M: OVER |
| serdes (11) | 30 / 0 | 0 | 1,700 | t4 407,738: OVER |
| lepe (8) | 135 / 0 | 0 | 1,000 / 1,500 | - |
| iq_C t1 | 1 / 1 (416) | 0 | 1,000 | - |

- **Hops.** Plan stations hold 405 everywhere except iq_C t1. The 300 cap of `rules.txt` is exceeded on 5,519 station hops. The col relay segments are the only plan rows over 405. Placed hops are worse than the plan on leaf, c1x_C, lepe, bk_sel (R FABLE-VISUAL-0030: 11,132 / 22,587 / 6,111 / 1,375 hops over 300).
- **Taps.** All 216 col types allow 3,000 sinks per tap (V). Measured col_h9_r1: t25 3,000, t1 2,998, t2 2,866, median 324 (R FABLE-VISUAL-0030). J7 has no col tap row. Leaf t44: 220 of 3,034 free 20-um bins (7 %) are over 300 um from any tap, worst 449 um at the NE corner, before and after lever 2 (V).
- **Cap.** 26 types over 400k have no bound split: c1x_C 9, svc 15 (hi4 is the 16th), serdes t4, kv_leaf t2 (unmeasured).
- **Reset.** RESET_LEG 522 rows / 82 types, equal to J5 (R S81-J6-ASSEMBLY-R2). J7 rows: leaf local resets 52 types, bk_sel RSD, gunit reader start. No col reset row (`g_rsreg` class, -58 to -284 at CTS in FABLE-PD-S81-2340).
- **Shape and outline (V).** Lever 2 t44: 15 cores moved, 0 re-shaped, 0 orient changes, outline equal. kv_leaf t5: 16 moved, 0 re-shaped, none outside. svc `plan_c`: die outline equal, 872.64 + 570.24 = 1,442.88, 0 cores re-shaped, 0 outside their piece. No growth anywhere.

## 2. Conflicts between the family row sets

| # | Conflict | Evidence | Root cause | Fix (P), ranked | Owner |
|---|---|---|---|---|---|
| C1 | RDX donor against ROM pval, on 215 col types | V: `rdx_c1n_donor_1121.json` has 216 whole-key `replace` ops on `relay_depth` and 216 on `relay_sites`. `j6_delta_rom_pval.json` adds 2,573 rows (bn `e_r0` / `e_r1` / `e_st`, sink, D 1). Kept in the donor: 0 | Both deltas replace the whole key; each was built on a base without the other | 1. Rebuild the donor on a base that already holds ROM pval, as per-row adds. 2. Fixed order: ROM pval, RDX, R3 relay rows, q-pair, south strip. | S81-J6-ASSEMBLY-R2 |
| C2 | FAM-S81-COL-H10 is deriving the bn sink rows again | R (04:45 post): "neither J5 nor J6 carries bn sink rows", 24 rows on two types. V: the same rows exist for 215 types in ROM pval | ROM pval sat in C3g, which J6 dropped | Stop the re-derivation. Run proof A with `j6_delta_rom_pval.json` filtered to the two types | FAM-S81-COL-H10 |
| C3 | Leaf lever 2 against vp_sr, reach1, taps (t44) | V (`an44.py`): `vp_sr` replaces all 316 `internal_stations`; 100 of its 892 register sites lie inside the moved lane cores (0 before). `reach1`: 5 reader-start and 2 writer-start stages inside `g_ln[7]` / `g_ln[2]`. 3 non-core C1n taps (t21, t37, t49) inside moved cores; lever 2 moved 21 taps. Local-reset sites: clear | Row sets solved on the old core positions; `vp_sr` and lever 2 both replace the station table | 1. Apply the regrid first, then re-solve vp_sr stations, start stages and taps on the moved cores, per type. 2. Until then keep regridded types out of the vp_sr / reach1 deltas. | OPUS-FIX-S81-LEAF-R3 |
| C4 | kv_leaf t5 regrid against vp_sr, reach1 | V (`an5.py`): 53 of 117 vp_sr sites and 6 of 12 reader-start stages inside the moved cores. Six facing gaps are still under 20 um (8.6, 15.1, 17.3 x 4); target was 40 | Same as C3 | Same as C3. Open the six gaps or declare them station-free | FAM-S81-MISC-R2 |
| C5 | kv_leaf t2 cut at x = 1693 | V: ft2 window is 1,691.904 to 1,931.868 (1,104 bits): the cut is 1.1 um inside it. 1693 is off the 8.64 grid (195.95). Tap `clk_t120` within 20 um. Both leaf bus windows (x 2,265 to 2,541) fall in part B, the leaf band in part A. The leaf local-reset delta also edits t2 | Cut chosen from the macro bbox only | 1. Cut at x = 1,684.80 (grid 195): 7.1 um west of ft2, 55 um east of ft1, west of all 183 macros. 2. Station the leaf buses across the seam, both sides registered, cycles declared. 3. Re-derive t2 local resets per piece. | FAM-S81-MISC-R2 |
| C6 | Lane table edited by four sets | V: `r1_frame_rompval` replaces all of `/lanes` and `/latency` (rt_W1 / rt_W2 lanes change). svc `plan_c` adds 11 lanes named `L1`..`L11`, 13 ports, and differs from C1n on `fi_W0_*` lanes. bk_sel R5 changes 12 lanes (R). `j6_delta_svc` replaces all of `/ports`; FT v3 edits `/ports/1535`, `/2199`, `/1567` by index | Whole-table replaces mixed with per-lane and by-index edits | Whole-table replaces first, per-lane edits after, index edits last with their sha check. One lanefix and one token compile at the end. Rename `L1`..`L11` to semantic ids (tool f6bc63dbbb65 is merged) | S81-J6-ASSEMBLY-R2; OPUS-FIX-S81-SVC-R5 |

Other interactions checked (V):
- **Reset anchors.** `j6_delta_fstart` adds `reset_tree_anchor` to 182 types. Any later row that adds flops moves the solve: 565 `RESET_ANCHOR moved` lines in `candJ7RDX`; lever 2 kit A stopped at gen on the same identity check (R). Regenerate anchors last, with bind tools equal to gen tools.
- **svc split base.** `plan_c` is on the H8 form: 32 C1n core instances missing, 26 new. It needs `j6_delta_svc` (27 new G0 findings, undecided) and the land SRAM (3,215,315 gates as flops; benches 2295988 / 2412579 not finished, R). The att piece has ft max hop 337.8, 64 taps, cap 800 (V).
- **FT v3** touches slice_station t28 / t38 / t51 and lepe_mu_LP t2, lepe_nh_mus_LP t1, lepw_mus_LP t2. No col type, no c1x_C type. The lepe proof8 kit was built without it: re-read proof8 on the FT base before taking lepe rows.
- **Leaf local resets against FSTART:** 52 identical paths; the J7 file supersedes. Apply it after FSTART.
- **c1x_C split B.** The strip is four perimeter bands plus interior rows. A partition type is one rectangle (`outline_um`), so the strip is not one type. No rows, no bind. Relay-row delta is empty at plan level (R).
- **TAP-GRID t39:** post-hook setup -187.56 / hold -94.50 against -73.73 / -75.14, 30 taps off target (R, 04:38). No rows. Tap rows solved on old placements would also land in moved cores (the t5 `clk_t29` failure).

## 3. Per family: root cause, fix, owner

| Family | Root cause (measured) | Ranked fix (P) | Owner |
|---|---|---|---|
| J6 base | Post-apply ELAB 2 / BIND 2 (V) | 1. Put the exact PORTFIX entry file used by `candJ7RDX_C1n` (ELAB rc 0) into the live tree and rerun postbind. 2. Token compile on that out | S81-J6-ASSEMBLY-R2 |
| col_h10_r0_p1 (6) | relay_mid: 15 of 121 groups over 405; 7 false-fit chains to 522.7 um (R) | R3 rows (+15 cycles) plus FIT_CHAIN; proof C to sign-off | FAM-S81-COL-R3 |
| col_h10 r0_p4 / r1 / r2 (30) | ROM pval half cycle: GRT TT -56.5 to -137.9 (R). r1 pv1a6ec9c2 GRT overflow 4,263 (R) | ROM pval rows from C3g; south-strip 6 ops | FAM-S81-COL-H10 |
| col_h9_r0 (60) | 5 to 6 relay rows per type at 415 to 594 um (V); pv697f40c9 placed: 26 groups over 405 (R). Rep p2 pva4376595: post-hook CTS -245.5 / -89.5, GRT TT -15.6, congestion-10 report 48 lines, in DRT (V) | 1. Finish the four DRT reps. 2. D + 1 on `t1.xai`, `t1.xbi`, `bs0.i_x0`, `bs0.i_x1`, `y_cc_1_0`, `y_x2_2_0` for all 60 | FAM-S81-COL-H9R0 |
| col_h9_r1 / r2 (120) | Core to core on different taps, -47 (R); taps at 3,000 | RDX + ROM pval; bank taps of 1,000 with cascade (17960d767b) | FAM-S81-COL-R3; TAP-GRID-R2 |
| leaf (75) | vp lane block congestion: t39 p3 congestion-5 over 49,932 (R); t44 60.2k (R) | Lever 2 kit on t44 to GRT first; then the per-type solve for the other 74, with C3 | OPUS-FIX-S81-LEAF-R3 |
| svc (16) | Land store in flops; one type of 3.3M to 5.1M | Land SRAM proof, H8 rows, hi4 split kit, then the same cut on 15 types | OPUS-FIX-S81-SVC-R5 |
| c1x_C (9) | 477k to 503k; soft flop to core pin 1,434 um (R) | 1. WREG stage (bench died rc 1 at 04:33: fix first). 2. Rectangular two-piece cut. 3. R-SL1 station move | FAM-S81-SLICE-R2 |
| slice_station (46) | t36 on C1n: post-hook setup +141.35, hold -78.3 pre-GRT (R) | Release the held siblings now; FSTART for t37 / t51 | S81-J6-ASSEMBLY-R2 |
| kv_leaf t2 / t5 | t2 never finishes synthesis; t5 slits | C5; C4 | FAM-S81-MISC-R2 |
| serdes (11) | t4 407,738 cells; DPL fixed in J6 | No-growth split rows for t4; RX donors re-derived on J7 kits | FAM-S81-SERDES |
| lepe (8) | proof8 form: post-CTS TT -245.46, FF -227.50 (R); no GRT read | Rows only after the proof8 GRT read on the FT v3 base | FAM-S81-LEPE |
| bk_sel (1) | R4c placed: 304 captures over 300, 2 over 405; `rq -> rs1` 705 um (R) | RSD relay rows (090fa6664c) and u_dsp rows after the R5 place read | S81-BKSEL-R5 |
| taps | Pair / grid forms regress on leaf | No J7 tap rows; col bank taps as a private proof | TAP-GRID-R2 |

## 4. Gaps: unsigned S81 that J7 does not fix

S81 types signed: 44 of 394 (R SIGN-RATE 04:15). Holds: 391 of 395 items, 389 of them "J6 representatives first" (V `kit_wave.json`).
- col_h9_r0: 60 types, no J7 row.
- col taps at 3,000: 216 types, no row.
- leaf: 74 types without regrid rows; 495 reset rows on 75 types (R 2340) beyond the 52-type local-reset file.
- svc: 15 types without split rows.
- c1x_C 9, iq_C, kv512_C, c3x_C: no bound rows.
- serdes: 11 types, no plan rows; t4 over the cap.
- kv_leaf t2 (no rows), t3 / t4 (no fix listed).
- phy, gunit, seqhost, iqf, eng: gunit delta staged, phy needs a fresh gen; the rest have no J7 item.
- Die level: 27 C3g G0 findings undecided; no token compile on any J6 or J7 tree; no whole-die render of J7 exists. I looked at `reviews_codex_1121/overview.jpg` (C1n / C3g / C3i cores and lane density): it shows the svc block change and the two N-S lane trunks, at a resolution that supports no finer verdict.

## 5. Recommended J7 assembly order

1. Repair the J6 base (PORTFIX), postbind green, token compile.
2. Layer A, whole-key deltas, fixed order: ROM pval and r1_frame rompval (replaces `/lanes`), vp_sr, CFX, leaf keys, FSTART without anchors, reach1, lepe / f0_q, then RDX rebuilt as row adds.
3. Layer B, col rows: R3 relay rows, col_h9_r0 rows, q-pair, south strip.
4. Layer C, core moves: lever 2 (proven types only), kv_leaf t5; then re-solve stations, start stages and taps on those types.
5. Layer D, re-partitions, only those with a private strict bind: svc hi4 (after H8 + land SRAM), kv_leaf t2 at 1,684.80. Others go to J8 by name.
6. Layer E, single-type rows: bk_sel R5, gunit, straps t40 / t45, FT v3 (index ops last), lepe after proof8.
7. Close: one lanefix, anchors regenerated, strict bind + LATCHECK, G0 with absolute values, token / vmux compile, whole-die render review, then apply and launch one representative per family.
Earliest apply by the 24-h rule: 11-22 04:15 PST.

## 6. Stop list

- No J7 gate or token compile on the live J6 tree before its postbind passes.
- No merge of the RDX donor with ROM pval in either order as they are.
- No second derivation of bn sink rows.
- No vp_sr, reach1 or tap rows on a regridded type without a re-solve.
- No kv_leaf t2 cut at 1693.
- No c1x_C strip as one ring type; no c1x_C split in J7 without bound rows.
- No svc split on the C1n base, and none before the land SRAM benches pass.
- No TAP-GRID rows from t39.
- No whole `/lanes` or `/ports` replace after any per-lane or index edit.
- No relaunch of col_h9_r0 on J7 expecting a relay fix.
- No rep-first hold on slice_station siblings.

## 7. Not checked

- The cause line of the postbind ELAB failure (log prints the rc only); the error classes behind the 360 `candJ7RDX` errors.
- `candJ7RDX_C1n` / `_FT` bind results (running).
- bk_sel R5 rows, col R3 `mkplan3.py`, H10 `mkplan_h10.py`: not diffed against the plan; lane numbers taken as R.
- No kit report opened except the col_h9_r0_p2 rep on intel1; no FABLE-VISUAL-0030 PNG re-opened.
- Placed tap loads and reset depth after J7: no J7 kit exists.
