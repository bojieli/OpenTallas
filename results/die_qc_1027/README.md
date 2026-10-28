# DIE-QC 2026-10-27: count-aligned crossing estimate, tree-cell fix, die GRT with the clock routed, measured margins, die STA

Branch: claude/die-qc-1027 (from claude/qc-sliceclk3-1027@e898bf05ab, merged origin/main 3ff5225390).
Plan: physical/die_plan/qwen_compute/die_plan_sliceclk.json (QC-SLICECLK-1, sha256 5545cbfca017..., untracked in the WT, same file the predecessors used).
Regions: intel2 /srv/opentallas-scratch2/claude/qc-sliceclk-1027/fs/regions.json. R35 rows: qc-sliceclk3-1027/qc_slice_rows.json (= claude/qc-infra-r35-1027@c2b1eb75be).
Data: intel2 /srv/opentallas-scratch2/claude/die-qc-1027 (rep 405), die-qc-1027-r250 (rep 250), die-qc-1027-r250l300 (rep 250, leaf 300).
Labels: every number is OWN / UNCHECKED unless marked otherwise. No independent NUMBER-CHECK has been run.

## 1. One-page estimate (before build): COUNT-ALIGNED vs the current ring, as-built buffered 1-D top spine

Input: the QC-SLICECLK-3 landed_phase_ocv rows (placement-estimate arrivals, g021 AOCV + droop 'regions', core latency 250 TT / 202.5 FF), with the TT/FF union.
Tool: main MESO-COUNT-1 `count_align_plan.plan` (claude/meso-count-1027@258bc16208), unchanged. Partition endpoints are remapped to the 13 clock regions (`scripts/ca_qc.py`), since count origins are per region.
Window: [(0.5T+ap), (DEPTH-0.5)T-ap], with T = 833 and ap = T/8 = 104.1. Margin_lo = L_lo - 0.5T and margin_hi = (DEPTH-0.5)T - L_hi, both including ap. Per-crossing K/DEPTH/latency are in `estimate/*.tsv`.

| form (placement estimate) | current ring worst / <100 | CA FAIL | CA worst lo / hi | DEPTH 4 / 8 | latency hist (K+1) | clean tree edges |
|---|---|---|---|---|---|---|
| buffered 1-D top spine (as built) | -626.7 / 200 of 264 | 0 | 104.1 / 186.0 | 94 / 170 | 1:1 2:10 3:166 4:87 | 3/12 |
| shorted M8 spine (reference) | -643.5 / 49 | 0 | 104.1 / 148.5 | 238 / 26 | 1:1 2:11 3:237 4:15 | 10/12 |

- Count-aligned removes the fixed nominal offsets: HUB<->W5 d = 752 ps becomes K = 0..3 at DEPTH 4/8, and E0<->W0 passes as well. **So the ruling's default holds: no HUB delay-match feed and no shorted spine.**
- The cost of the buffered spine is DEPTH 8 instead of 4. On slice<->slice it hits 144 of 215 crossings (43,313 of 63,170 bits; +4 slots × 43k bits ≈ +173k flops, about 0.05 mm²). In addition, 32 of the 91 wide (≥256 b) ports go to latency 4 instead of 3.
- Why: 9 of 12 start-tree edges have a derated spread of 562-913 ps. Adding 2ap pushes that over T, so the sync is ambiguous; each ambiguous edge adds one cycle of path ambiguity.
- Price (UNCHECKED, linear scaling of the CHECKED K=1 price -0.65 % = +54 cyc/layer): if all 11 serial slice hops took +1, that is +11 cyc/layer ≈ -0.13 %. MESO-INTEG-1 owns the schedule numbers.

## 2. Three tree cells on cores: fixed (`tools/die_plan/die_trial.py`, slice-spine opt-in only)
- Cause: `balanced_site` walked in 2.16-um steps to 10620.720000000001, which is exactly a core-halo edge (strict-inside test), and **rounded** the candidate to 10620.72, which lies inside by 1e-12. Affected cells: b3485, b5553, b8655 at y 11,080.8.
- Fix: candidates stay unrounded, and the new `round_legal(site, q)` rounds to the 1-nm output grid while staying legal. Two tests were added (slice_spine tests 11/11 PASS). The default kit path is unchanged.
- Result: the kit reports `illegal {}` (0 of 18,164 cells at rep 405, 0 of 21,812 at rep 250, 0 of 36,377 at leaf 300). The render check counts 0 cells inside a forbidden rect.

## 3. Die GRT with the clock ROUTED (`scripts/mk_combo_qc.py`, LAND-HEAD recipe + QC kit layers)
- Setup: one global_route over the kit signals plus all die-clock nets. Signals use M4-M9 as in the QC kit (12.1c), the clock uses M8-M9, and the kit layer adjustments apply. The run uses `-congestion_iterations 50 -critical_nets_percentage 0`, and the 29,875 clock-reservation obstructions are dropped (13,304 PG obstructions kept).
- rep 405: `Found 18165 clock nets`. Overflow **0** on every layer at TT and FF, usage 2.92 % (M7 7.34 %, M8 0.62 %, M9 1.12 %), 4:46 wall, 20 GB.
- rep 250: 21,813 clock nets, overflow 0 at TT and FF.
- Render `clock_routed_TT.png`, viewed. It shows the top spine row at y ≈ 13,130, the per-slice M9 columns, the strip legs and the local trees in the channels. The PHY/HUB column is at the left. No cell sits on a halo.
- Caveat: the router draws clock wire at default 1x width (no 16w NDR in the combo, as LAND-HEAD/KV). The R35 plan's 16w trunk would have about 1/16 of that R. This is a conservative routed RC for the trunk.

## 4. Measured crossing margins (GRT-RC arrivals, main landed_phase_ocv + count_align_plan)
| run | insertion TT | current ring TT / FF worst (<100) | CA FAIL | CA worst lo / hi | D4 / D8 | latency hist | slew viol (>320) |
|---|---|---|---|---|---|---|---|
| rep 405 | 9.2-10.6 ns | -1058.8 / -840.3 (264/264) | 0 | 104.1 / 449.3 | 12 / 252 | 1:1 2:17 3:107 4:124 5:15 | 413 (max 569) |
| rep 250 | 9.1-10.4 ns | -874.4 / -662.3 (264/264) | 0 | 104.1 / 470.1 | 12 / 252 | 1:1 2:16 3:108 4:124 5:15 | 44 (max 348) |
| rep 250 + leaf 300 | 9.1-10.5 ns | -855.6 / -647.4 (264/264) | 0 | 104.1 / 462.3 | 12 / 252 | 1:1 2:5 3:119 4:139 | 170 internal (tap slew max 95) |
- Count-aligned passes all 264 crossings at ≥100 ps on both sides on the routed clock. The current ring fails every crossing.
- Routed insertion is about 1.6x the placement estimate. The derated spread is up to 1,346 ps (E0|W0), so 0 of 12 start-tree edges are clean, path ambiguity is 2 cycles, and 252 crossings need DEPTH 8. A few need latency 5.

## 5. Die STA related pairs (main die_sta_related.py: --clock-ocv table, --clock-droop shared, droop region = clock region, data droop class (default), declared budget)
| run | TT intra setup / skew | TT seam setup | FF intra hold / skew | FF seam hold | HB4 (TT setup after) |
|---|---|---|---|---|---|
| rep 405 | -406.4 / 738 | -409.8 | -917.3 / 663 | -921.1 | -1048 (163k pairs <0) |
| rep 250 | -293.6 / 650 | -296.9 | -799.2 / 567 | -803.1 | fails |
| rep 250 + leaf 300 | -264.2 / 646 | -266.1 | -798.9 / 560 | -801.1 | -889.6 (163k <0) |
- **FAIL.** The worst pair is intra c_W5_tf_01 (W5/PHY region): nominal in-partition spread 549 ps TT, CPPR credit 114, OCV 310.
- Std slices (330 partitions) have a worst nominal in-partition spread of 303 ps TT (c_W0_tn_11), median 180. Tap slew reaches 475 ps: the leaf->tap last mile (600-um local bisection) is unrepeated 1x wire.
- So the local tree and the W5 tree are the structural problem. The top spine and the crossings are not.
- The STA 'landed' class (window T/2) is the old-ring reading and is INFO under count-aligned.

- Leaf 300 (tap slew 475 -> 95) does NOT fix it: the std in-partition nominal spread becomes 372 (c_W0_bf_11) and W5 stays at 544. So the last mile is not the cause.
- The cause is the routed 1x RC on a ~10-ns single-source tree. The placement-balanced tree (177 ps predicted) loses balance once GRT detours and 1x-width R are applied: one partition's taps sit on branches whose last common node is high up, and OCV then acts on ~9 ns of unshared clock.

## 6. Next (DIE-QC follow-up)
- (a) Run the combo GRT with the R35 16w NDR on the trunk, so the measured RC is the planned one, not 1x. This is a cheap re-measure; expected insertion is about the 6.5-ns placement value.
- (b) If the intra spread is still >~150 ps: per-slice common point (12.8e MSCTS: slice spine column -> per-slice mesh/strip mesh, local trees). Taps of one partition then share a mesh, CPPR applies at the mesh, and the ~9-ns unshared path becomes ~local only. Balance W5/PHY the same way.
- Count-aligned DEPTH 8 shrinks back toward the estimate once the derated spread drops (as-built estimate: 94 D4 / 170 D8).
