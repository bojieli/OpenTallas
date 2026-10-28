# QC-SLICECLK-3 (2026-10-27): spine-column slice clock opt-in, built on the R35 rows

Basis: claude/qc-sliceclk2-1027@d2a6b2d12b (main abbbffac9b), plan `die_plan_sliceclk.json` (QC-SLICECLK-1), regions `fs/regions.json` (13 regions: 12 slices; W5 = hard_io_serdes_2 with the PHY; HUB = hard_ucie_kv).
R35 reservation: claude/qc-infra-r35-1027@c2b1eb75be `results/qc_infra_r35/qc_slice_rows.json` (COORD accepted 20:13).
Data: intel2 /srv/opentallas-scratch2/claude/qc-sliceclk3-1027 (trial/ = kit+clock+GRT, lpo/ = crossing margins, probe/ = the pre-R35 tool probe, locality/).
Labels: every number here is OWN / UNCHECKED (no independent NUMBER-CHECK yet).

## 1. Tool: `die_trial.py kit --region-trees R --slice-spine [--slice-rows R35.json] [--spine-top-leaf-um 50]` (opt-in, default off)
- Top: ONE horizontal spine row y_s (R35 T3_tap row 13,132.8), with an equal-length 1-D bisection to every region's column x (full depth to 50 um).
- Region: an equal vertical feed on the column, then every y-bisection level ON the column (R35 spine_x, e.g. E0 18,303.84), until strip height <= region width (16 strips of 1.64 mm). Then one equal leg to the strip centre (678 um), then a stock full-depth local bisection to 600 um.
- Site pass `balanced_site`: an illegal node goes to the legal candidate (4 axis rays + nearest) that changes root->kid lengths least. The blind `site.slide` along a split axis (the QC-SLICECLK-2 root cause) is gone. Without --slice-rows, the column/row are found from SiteMap (`find_spine_column/row`).
- tree.json meta.slice_spine: per region column x, strip leg, feed leg, root->tap Manhattan range, move/imbalance stats.
- Tests: `tools/die_plan/test_die_trial_slice_spine.py` (8). Existing die_trial tests: same pass/fail set as main in a sparse copy (9 data-file-missing failures identical with main die_trial); s81_head/test_fallback_land 4/4 in the full WT.

## 2. Clock build (R35 geometry) - trial/clock, render build_tree.png (viewed)
- 12,351 nodes, 5,813 repeaters, 18,164 cells, 7,121 taps, 4.89 m tree wire, 22 levels; 3 node cells illegal (core, y 11,080.8: to fix).
- Viewed render: columns sit on the R35 spine_x columns in the channel, the top spine on row 13,132.8, strip legs to slice centres, local H-trees in the inter-core channels.
- In-slice arrival spread (ctree STA, placement parasitics): **176-177 ps TT / 149 FF** on every std slice (QC-SLICECLK-1 stock: 1,634 / 1,380). W5+PHY 378/331, HUB 100/87.
- Slice medians: 6,473-6,498 ps TT (25 ps across 11 slices). W5 6,525. **HUB 5,795 (-730 ps vs W5)**.

## 3. Die GRT (trial/grt, 50 congestion iterations): overflow 0, usage 2.89 % (M7 7.35 %, M8 0.58 %), WL 598 m, 3:38
- Clock enters as reserved rects ("Found 0 clock nets"), the same recipe as QC-SLICECLK-1/S81-2. It shows routability only; it is NOT the 12.4a GRT0 with the routed clock.

## 4. landed_phase_ocv (main tools/s81_head/landed_phase_ocv.py, g021, droop 'regions', core lat 250/202.5), 264 crossings / 63,170 bits
Arrivals = ctree placement estimate, NOT GRT-RC, so these are PREDICTIONS and do not count as adoption evidence.
| top form | slice<->slice (215) worst TT / FF | W5<->W4 (22) | HUB<->W5 (27) |
|---|---|---|---|
| buffered 1-D top tree (as built) | **-40.1 / +41.7** (E0<->W0, LCA = spine root, unshared 6.33 ns), 151 TT <100 | +78.7 / +143.4 (d 51) | -627 / -447 (d 752) |
| top spine shorted = one common point (shortspine.py model) | **+109.9 / +172.3**, 0 <100 | +61.8 / +133.5 | -644 / -458 |
- Finding A: an equal-length *tree* along the spine is not enough. Neighbours that split at the spine root (E0|W0) carry the whole top tree as unshared clock. The R35 top is also a 1-D tree (nets_1d, depth 4), so it has the same problem. The spine must be ONE electrical common point: a shorted M8 spine (a 1-D mesh row driven by the balanced tree, as in the 12.x MSCTS mesh form). Then every slice pair clears 100 ps in this prediction.
- Finding B: HUB (1.56 x 14 mm) and W5+PHY (4.03 mm wide) have different insertion from the 2.47 x 26.3-mm slices. HUB<->W5 nominal d = 752 ps TT, which no OCV margin can absorb. Options: a plan-computed delay-matching HUB feed (~3.5 mm, a ledgered meander under v5.1) or re-cut HUB/W5 to slice geometry. Needs a ruling.

## 5. Locality (main tools/die_plan/locality.py score, v 199 ps/mm)
- Inside regions: 95.1 % of bits, 97.7 % of bit-mm. Across: 264 ports / 63,170 bits on 24 region pairs, all neighbour pairs (far ports 0, 1 hop each). Track ratio is at most 0.055.
- Heavy crossing links: sl_fe<->sl_fw between neighbour slices = 58,007 bits (5,507 or 4,993 per boundary, 11 slice boundaries). HUB<->W5 5,163 bits (coll_f4<->fw 3,966 + c_W5_bf_00<->coll_s 1,197). Nothing crosses a non-neighbour slice.

## 6. Not done
- Die STA related pairs (needs a die_clock_mesh / die_sta_related setup on this tree). Measured landed_phase_ocv after a GRT that routes the clock. Shorted-spine netlist + the HUB match first, or the gate cannot pass (Findings A/B).
