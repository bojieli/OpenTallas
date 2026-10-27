# QC-CORES-1: A0 NK/NL hard-core split plan (2026-10-27)

Scope: qfd_tile_nk_a0c (720 copies) and qfd_tile_nl_a0c (48 copies). This is a plan only: no P&R was run. The plan waits on a GEOM REQ verdict.

Labels: CHECKED = recomputed here from the data. UNCHECKED = taken from another lane's file and not recomputed.

## 1. FF-pruning review (Codex raw_leaf_kit, 11646 vs 12030 FF)

- **Where the FFs were lost (CHECKED).** ORFS `1_synth` runs OpenROAD `eliminate_dead_logic`. In run_pgfix it reported "Removed 576 unused instances and 576 unused nets":
  - 1_2_yosys.v holds 12030 DFF (11085 DFFHQN + 945 DFFASRHQN).
  - 1_synth.odb holds 11646.
  - The loss is not GPL/DPL "physical optimization", as the Codex README states.
- **Which FFs (CHECKED; name diff in intel2 qccores1-1027/a0/ff_removed.txt).** All 384 removed FFs have no path to any leaf output:
  - 192 = `u_ls.g_grp[0..3].g_lane[*].g_candidate_mul.u_mul.g_inreg.{a_r,b_r}[0..15]`. These are the low 16 bits of 12 of the 32-bit operand registers.
  - 128 = `u_ls.s3_w[*]`, half of 256.
  - 64 = `u_ls.s3_x[*]`, half of 128.
- **Verdict.** The pruning preserved the function at the leaf ports: removing unobservable state cannot change any output.
  - The claim "192 required input captures lost" is wrong as a functional claim. Those registers capture input bits whose values never reach an output.
  - The ffpg successor force-keeps all 12030 (A0GATE ff 12030, pg_bad 0, in_port_flops 390; CHECKED from a0_gate_cts.txt). That keeps 384 dead FFs as clock sinks, costing area and clock load. It does not fix a bug.
  - The correct structure: remove the dead operand bits in the RTL (candidate_mul low halves, unused s3_w/s3_x halves), or accept dead-logic elimination and gate on the post-elimination FF count plus a leaf LEC.
  - UNCHECKED: whether these bits are also dead in the uncut native LSL. If they are live there, the raw-fault cut dropped an observation path, and that would be a real bug.
- **ffpg leaf after route (CHECKED, signoff.log 10-26 01:47).** NOT SIGNED:
  - TT setup -90.89, FF hold -17.53, DRV fail.
  - sdc_lint FAIL: split_d min input delay of 40 ps.
  - ff_ref_missing.
  - Its clk pin is on the E edge (pins.json x=115.248 y=62.988), which violates 12.8a.

## 2. Structural split (hardened once, each run <= 400k cells)

| sub-core | cells | per NK / NL | copies on die | state |
|---|---|---|---|---|
| ot_qwen_tile_lsl_rawfault_m3 (LSL rawleaf) | 58,386 mapped / 76,731 raw (CHECKED size_gate.json, source.json) | 8 / 8 | 6,144 | unsigned (above); re-kit with centre clk |
| ot_qwen_tile_romleaf | view on main, gate PASS 10-16 (UNCHECKED cells) | 10 / 10 | 7,680 | pre-12.3 view, clk on W edge (LEF 0,21.756) -> re-kit |
| ot_qwen_tile_node | PROVISIONAL_NOT_A_VIEW on main | 1 / 0 | 720 | no real view; clk on E edge |
| NK parent (soft + islands) | 64,205 cells / 16,592 FF (mapped sha 3423d4c0 matches parent_actual_synth.json, CHECKED) | 1 | 720 | LEC running (below) |
| NL parent | 61,550 / 15,561 (UNCHECKED, Codex json) | 1 | 48 | - |

- Consistency (CHECKED arithmetic): flat NK 677,672 = 64,205 + 8 x 76,731 + 381 (0.06%). The split covers the whole flat count.
- NK and NL share the rawleaf and romleaf masters (same type names in both parent synth jsons, CHECKED). Whether the netlists are identical is UNCHECKED.
- The parent RTL still carries the 42/41 external clock taps (-DOT_A0_CK_TAPS42). The plan replaces them with one centre entry.

## 3. Outline and clock plan (a0_split_plan.py; renders a0_split_plan_{nk,nl}.png, viewed)

- The outline (457.92 x 1157.76) and all child placements are taken unchanged from the Codex parent packet. Every child already passed the halo audit.
- **E0, one centre entry:** (228.96, 578.88), in the 67-um ROM channel. It has an M9->M5 island (12.8a) and replaces the 42/41 taps.
- **Balanced in-core H-tree (12.8b, pushdown islands 12.2a1):**
  - L1: +-245 um vertical, ending at (228.96, 333.88) in the channel and (228.96, 823.88) in the 20-um LSL row gap.
  - L2: from S, +-130 um vertical, ending at (228.96, 203.88) and (228.96, 463.88).
  - L2: from N, +-130 um horizontal in the row gap, ending at (98.96, 823.88) and (358.96, 823.88).
  - 0 islands fall inside a child or its 5.4 um halo (CHECKED script).
- Max distance from E0 to a child clk pin today: 652 um. Leaf legs run 0..271 um, because the child pins are on edges.
- PASS-COND items for review:
  - (i) Children re-kit with centre clk pins, so the leaf legs equalise.
  - (ii) The N0/N1 leaf legs cross over the LSL children. The child OBS must leave M6 free, or the legs must run in the row gaps.
  - (iii) The L1/L2 islands sit inside the Codex bus corridor x 200.66-257.26. They take sites, not tracks; capacity must be re-deducted.
  - (iv) Latency against 250 TT is not estimated (UNCHECKED). Early taps from the children's real views are allowed (12.3 v5.0).

## 4. LEC plan for the composed core vs the original RTL

1. Parent: cut-RTL (children black-boxed) vs the mapped parent, run with tools/die_plan/lec.py@262d07038. Running at intel2 /srv/opentallas-scratch2/claude/qccores1-1027/a0/lec_nk_parent/lec.
2. Each child: routed netlist vs its RTL (rawleaf: rawleaf_keep.v; romleaf/node: on re-kit).
3. The cut identity, original LSL == wrapper(u_lh) o rawleaf. Codex has this only at netlist level (whole-graph identity + 2^50 cone SAT). It still needs an RTL-level LEC of the original ot_qwen_tile_lsl against the cut-RTL composition.

## Clock R2 (QC-CORES-1, answers GEOM-REVIEW-18 FAIL-IN-PLAN) — PLAN ONLY, no P&R
Script `a0_clk_r2.py LIBDIR OUT` -> `clk_r2/a0_clk_r2_plan.json`, `clk_r2/a0_clk_r2_{nk,nl}.png` (both viewed).
All numbers PLAN MODEL, UNCHECKED-model (NLDM RVT TT/FF + Elmore, M5/M6 setRC x0.8/0.9 for M6/M7 legs); predictor family reads ~15 ps HIGH on TT.
- Single in-core E0 tree (R1 form, re-modelled) = P ~200 TT -> child budget ~50 ps: infeasible; also 12.2a forbids core-owned M8/M9.
  Restructured per 12.8b/12.2a1: die mesh (M8/M9, die-owned) drops into 26 in-core PUSHDOWN islands (identical coords all 720/48 instances),
  each island = one plan-sized driver + short M6/M7 leg (<= 80.6 um) to child CENTRE entries / parent-FF local roots.
- (a) unequal legs: ROM = vertical pairs from row-gap islands (legs 65.1/65.5), LSL = column pairs (80.3/80.6), node 79.8 -> child-entry window TT 0.63 / FF 0.96 ps.
- (b) parent FFs: 18 parent local roots (channel x5, E face x9, c1r0 slot, row-gap x3), P 30.7 TT -> local trees built to composed 250 (B_par 219 TT / 178 FF).
- (c) composed: P_child TT 43.8 / FF 36.2 -> common child budget B = 206 TT / 166 FF (all three masters, same value).
- (i) re-kit clk pins (child frame, centre): romleaf (86.4,55.08), rawleaf (57.672,70.2), node (23.76,216.0); child OBS <= M5 (romleaf LEF CHECKED M1-M5; rawleaf/node UNCHECKED).
- (ii) no legs in row gaps (islands only, stub); legs over children on M6/M7; 0 legs / 0 islands in pin-face columns; 0 islands in child halo.
- (iii) islands R0-R4 in bus corridor (channel cross, 12.2a site) -> capacity re-deduction for 5 x 8.64 um island footprint + M1-M5 drop vias.

## Clock R3 (QC-CORES-2, answers GEOM-REVIEW-19 PASS-COND (2)-(5) + COORD ruling A0-CLK-R2) — PLAN ONLY, no P&R
Scripts: `a0_clk_r3.py LIBDIR OUT` (plan + renders `clk_r3/a0_clk_r3_{nk,nl}.png`, both viewed), `a0_lattice_snap.py`, `a0_gap_capacity.py`.
Lattice source: **R22 `strap_lattice_d43.json` = PROVISIONAL** (INFRA-FIRST-QC-R24 51.84-um lattice not yet published). Cross-check on the
Codex R23 guard51 candidate (`inputs/d51`, plan sha 37937a86…) gives identical results (`clk_r3/a0_lattice_snap_r23_d51.json`).
Die plan inputs (not committed, intel2 codex-qwen-1027/pkg/inputs): d43 plan f2c91d03…/r2 40cbbf8c…; d51 plan 37937a86…/r2 42d1c717….
- **(2) Snap to the R22 strap crossings is IMPOSSIBLE (CHECKED, all 768 instances).**
  - The lattice is incommensurate with the A0 type: 5 distinct M9 phase sets and 8 distinct M8 phase sets in the core frame
    (A0 columns alternate 604.8/622.08 um, M9 pitch 207.36/198.72/216; A0 rows 1296-1313 um, M8 pitch 146.88/138.24).
  - Crossings per core: 16 (658 cores), 8 (94), **0 (16 cores, W column x0 1650.24 lies W of the first strap 2177.28)**; 110 cores
    stick out of the strap span. A core needs 22 islands.
  - **0 of the 105 distinct core-frame crossing points is a legal island site**: every one lies inside a hard child + 5.4 halo.
  - Distance island -> nearest R22 crossing (R3 sites, 658 interior cores): median 94.9, max 126.4 um (dx<=108, dy<=66.7); all
    768: max 641.6 um. R2 sites: median 98.7, max 665.1. 0 sites coincide (<=0.5 um).
  - So per 12.2a1 ("the die tree/mesh lattice is chosen to coincide with the per-type island lattice") and 12.2c, R3 fixes a
    **type drop lattice** and asks the die clock owner for the plan delta: M9 drop straps at x0 + {108.864, 228.96, 349.056, 452.0}
    and M8 drop straps at y0 + {11.088, 142.344, 272.52, 402.696, 532.872, 663.48, 824.376, 984.888} (MX rows: y0 + 1157.76 - v).
    That is 192 M9 + 128 M8 drop straps (`plan_delta_drop_straps` in the snap json, full lists); M9 gaps 102.9-278.9 um; the die owner
    keeps/adds its own straps in the inter-row bands (M8 gap 339 um between A0 rows) and outside A0 for mesh density.
- **R3 islands: 22 per core, all on lattice crossings at legal parent sites** (0 in child halo, 0 in pin-face columns, 0 legs in
  pin-face columns; NK and NL identical, NL has no node leg). R2 26 -> 22: L00/L20 merged into MW4/ME4, A into R4, EN0 into EF5;
  R0-R4 moved from ROM row centres to the gap above; EF to x 452; G0-G2 to the lattice columns. Leaves keep R2 positions.
  Model (UNCHECKED-model, same stage model as R2, reads ~15 ps high TT): child-entry P TT 48.93 (window 12.05) / FF 40.93 (11.27);
  max leg 115.8 um (R2 80.6); slew <= 46.2. Window 12 ps < 20 ps design target; the ROM branches already sit at BUFx8 (smallest).
- **(5) B reconciled: B_child = 206.2 TT / 166.3 FF was right in R2 (child-only mean); 212.56 averaged child AND parent taps (wrong
  field, removed).** R3 numbers: **B_child = 201.07 TT / 161.57 FF (NK), 201.32 / 161.87 (NL)** -> one value 201 TT / 161.5 FF into
  the child re-kits (NK/NL differ 0.25 ps). Parent roots each get their own B_par (TT 196.5-219.3). Renders now draw the 18 parent
  roots (labelled triangles). Per-root FF counts need the parent placement (16,592 NK / 15,561 NL FF, avg ~920/root UNCHECKED).
- **(3) Layers.** romleaf LEF OBS M1-M5 (CHECKED, main). node LEF OBS M1-M5 (CHECKED, but PROVISIONAL view). **rawleaf FAILS
  today**: Codex leaf_kit `MAX_ROUTING_LAYER = M6` and 224 of 506 pins on M6 (CHECKED, b7da9afaa leaf_kit/config.mk, io.tcl).
  Re-kit rule: rawleaf ceiling M5, the 224 M6 E-face pins to M4/M5; face_guard/LEF check OBS <= M5 on all three masters.
  The A0 parent's own M6/M7 signals must keep out of the 22 leg corridors (clock NDR pre-route), to be checked at parent GRT.
- **(4) Capacity re-deducted** (`clk_r3/a0_gap_capacity.json`; island blocks M1-M5 8.64 um, 1.0-um via column on M6/M7, 3 tracks NDR
  per leg; assumptions labelled): ROM/LSL row gaps keep M2 315/556, M4 236/416, M6 294/312 at an island. Bus corridor at R0-R3:
  M3 1332/1572, M5 998/1179, M7 865/884; Codex 1024-bit budget (UNCHECKED, historical) -> use 0.55 on M5+M7 (0.32 incl. M3) <= 0.6.
  LSL gap 1-2 fault flags <= 250 (UNCHECKED bound) -> 0.29. E strip (8 islands, A0 wide E pin face) keeps M5 175/355: the A0 E-face
  pin positions are not checked against EF0-5/EN1-2 yet (open).
