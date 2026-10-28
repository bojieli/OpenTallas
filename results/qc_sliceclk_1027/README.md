# QC-SLICECLK-1 — QC per-slice clock variant (METHODOLOGY 12.10b), 2026-10-27

The OWNER asked for this variant at 10-27 ~18:4x. It runs in parallel with INFRA-FIRST-QC (R34, the continuous-mesh export), and the first of the two to pass the freeze gate wins.

Basis: main 133d979e4c `physical/die_plan/qwen_compute/die_plan.json` (canonical68: 377 parts, 3,005 ports). Labels: CHECKED = recomputed by an independent NUMBER-CHECK agent with its own classifier and its own requirements file. OWN = my own run, reproduced or cross-checked in this lane, but not independently checked.

## 1. Domains and crossings
- There are 13 clock domains: 12 slices (W0..W5, E0..E5), each = c_S_* (16) + sl_S_* (14) = 30 partitions in a 2,471 x 26,266 um column, plus HUB, the west IO strip (16 parts).
- The hard PHY io_serdes_2 cannot host a ring. `fallback_regions.merge_hard` therefore keeps it synchronous with W5, so W5 = 31 parts.
- Inter-slice crossings (CHECKED): 269 ports / 64,367 bits on 264 lanes. All of them sit at sl_S_fe <-> sl_S'_fw between neighbouring slices, on the line W5-W4-..-W0-E0-..-E5 (10-12 ports per direction per pair), plus HUB<->W5 (coll_f4, coll_s, io_serdes_2). With the PHY merge: 264 ports / 63,170 bits (OWN).
- Related pairs stay synchronous: 2,541 intra-slice ports / 1,184,174 bits (CHECKED, = 93 % of the die's bits) and 195 HUB-internal ports.
- Inventory: `plan/slice_crossings.json` (rows with port, lane, src/dst part+bus, width), `plan/landed_crossings.json`, `plan/regions.json`, `plan/slice_groups.json`.

## 2. Price (nativev7 composer, the same harness as FALLBACK-LAND; intel2 qc-sliceclk-1027/price)
| case | cycles/token | tok/s | delta |
|---|---|---|---|
| base (no landing) | 296,341 | 4,051.0 | — CHECKED |
| slice K=2 | 297,637 | 4,033.4 | -0.43 % CHECKED |
| **slice K=3 (as-built ot_dp_clk_landing DEPTH4/OFFSET2/RDREG1)** | **298,285** | **4,024.6** | **-0.65 % CHECKED** |
| slice + PHY merge K=3 | 298,285 | 4,024.6 | identical (OWN) |
| slice pairs (6+HUB) K=3 | 297,529 | 4,034.8 | -0.40 % (OWN) |
| halves W/E (2+HUB) K=3 | 297,097 | 4,040.7 | -0.25 % (OWN) |
| control: all-seam K=2 (FALLBACK-LAND) | 324,277 | 3,702.0 | -8.6 % reproduced (OWN) |

- Mechanism: CB16 does not change (cb_add 0, CB16 path 16 -> 16). All the cost is the 11 serial slice hops: hop_add = 11 x K = 33 at K=3, plus l9_add 3. That is +54 cycles per layer (chained 8,129 -> 8,183).
- The 85 % "serial slice chain" cost in FALLBACK-LAND came from the intra-slice partition seams. Per-slice domains remove those seams.
- The latency table (`gen.py latency`) adds +3 on exactly the 264 landed lanes and 0 on the other 1,669 (OWN, 0 mismatches).
- The cost is far below 5 %, so no cheaper cut is needed. Pairs or halves would save only 0.25-0.4 % but make each domain 2-6x larger.
- Ledger: proposed row QC.SLICECLK_LAND (qwen_rom), e2e 0.652 %.

## 3. Plan delta (`plan/die_plan_sliceclk.json.gz`) + gates
- `clock_landing_plan.compose` (main tool, observer glue, reset-mode collector) ran in 110 s, OWN. Types went from 68 to 81: 11 base types split into 24 landing/monitor cohorts. 144 ring storage bands, all "PROPOSED legal macro-free band", 0 placement FAILs.
- G0 PASS 0 errors / 167 warnings (base 0 / 111). G0C PASS 0 errors / 142 warnings (base 0 / 111). This uses `g0/cohort_cells.json`: each cohort type gets its base type's cell estimate. Without it, G0C shows 24 "no cell estimate" errors, the same tool artefact the KV fallback probe hit.
- Every new warning is a renamed copy of a base warning on a cohort type: near-duplicate types +11, core_faces +14, existing slot-reach geometry +6. There are 0 new rule classes (OWN).
- Clock: `die_trial.py kit --region-trees --htree-full-depth --tree-site-legal --tree-site-slide --rep-um 405` gives 13 region trees, 22 levels, 7,121 taps, 18,194 tree cells, 0 illegal sites, 4.93 m of tree wire. Abutted pin check PASS (3,005 ports).
- Render viewed (`render/clock_tree.png`, `render/die_plan_sliceclk.png`): the reference tree reaches the 13 region roots at the slice centres (y ~13.1 mm), and each slice has one full-height spine with equal-depth local H-trees.
  - GEOM notes: (a) the HUB tree in the west strip is irregular, with long L legs. (b) The W5 region root moves west because the region box includes io_serdes_2.

## 4a. Clock tree build result: STRUCTURAL FAIL of the stock region tree (OWN, from trial/clock/arr_{TT,FF}.txt)
- The ctree ran TT and FF, exit 0, 10 s each. Insertion is 7.8-10.2 ns TT for 19,305 taps.
- The arrival spread inside one slice is 1,634 ps TT / 1,380 ps FF, the same in all 12 slices. HUB spreads 100 ps; W5+serdes 975 ps.
- Root cause (E2 per-partition table): the far c rows (bf at y 0-5 mm, tf at y 21-26 mm) arrive ~1.4 ns later than the centre rows (bn/tn and sl_*).
  - Spread inside one partition reaches 1.48 ns (c_E2_bn_01 8,288-9,768).
  - `die_trial --region-trees` bisects a 2.47 x 26.3 mm (10.6:1) region from its centre, and the leg lengths to the taps are not equal. It was built for S81/KV regions of <= 2.2 mm.
- So the stock region tree cannot carry intra-slice related pairs; 80 ps is the target and 1.6 ns is ~2x the 833 ps period.
- No die STA is worth running on it.
- Structural fix: a balanced per-slice distribution, i.e. an equal-length slice spine/H-tree or a per-slice mesh (12.8e regional mesh).
  - This is the same M8/M9 export class as R34. The COORD 19:0x ruling applies: use the ONE shared QC M8 clock-row reservation (INFRA-FIRST-QC-R35), no separate fix.

## 4/5. Die clock + GRT, die STA
- Chain `tools/chain.sh` on intel2 (ot-run localhost = intel2, priority die), submitted 19:00 PDT: run_clock.sh (TT+FF ctree, 32 G / 4 threads), then run_grt.sh (256 G / 16 threads, 50 congestion iterations).
- In this die_trial recipe the clock enters GRT as 30,143 reserved clock rects (clock_reserve_rects), not as routed nets. This is the same as S81-2/HEAD.
- Collect from: `/srv/opentallas-scratch2/claude/qc-sliceclk-1027/{chain.log,clock_run.log,grt_run.log,trial/clock/ctree_{TT,FF}.log,trial/grt/grt.log}`. Then run `die_trial.py report trial --plan <plan>`.
- Die STA is NOT run. It needs real views of the QC cores and partitions. It runs on main `die_sta_related.py` with the shared model (`--clock-aocv-table`, `--cppr-lca`, per-slice `--droop-regions`, `--landing-window-ps` for the 264 crossings, `--hold-buffers`).

## Risks (UNCHECKED)
- Each slice is a 26.3-mm tall tree domain. A vertically adjacent pair that straddles a slice's region root diverges at the root, so it has ~13 mm of unshared tree on each side. The AOCV charge (0.21 %/mm) on that path is the main setup and hold risk.
- If that fails, the structural fix is a per-slice mesh or a split of each slice into a top and bottom domain. The landed cost of that split is not priced yet; the 11-slice chain is not affected because the vertical seams are not on it.
- The A0 core island feeds (R3B) and the core sign-offs are shared with top-down and stay on the critical path in both forms.
