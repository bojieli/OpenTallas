# LAND-HEAD-2 (2026-10-27): s81_head landed-form phase margin WITH clock OCV on the unshared tree

Input: LAND-HEAD-1 run intel2:/srv/opentallas-scratch2/claude/land-head-1/sl300 (FB1 one entry/partition, sl300 die tree,
combined die GRT 50 it, native OpenSTA GRT-RC arrivals out_{TT,FF}/arr_*.txt incl. every tree cell), plan fb1_lat.json
(7af81995 + compose dataflow + latency regen, sha256 d472fcc1beda5ea9).

Tool: `tools/s81_head/landed_phase_ocv.py` (+ 2 tests). It applies the shared model of main `die_sta_related.clock_ocv_fn` /
`clk_aocv.py` with the APPROVED table `clk_aocv_table_g021.json` (g 0.21 %/mm, random A/B classes, nets flat +-3 %).
Branch = entry arrival minus the output arrival of the LAST COMMON tree cell, plus the 12.3 partition-internal latency
(250 TT / 202.5 FF) as class B. Distance = bounding-box diagonal of the two entries + the common cell.
Droop on the clock (12.4a b1 shared rule): the two entries are in DIFFERENT clock regions, so the full one-sided +5.1 % late
is charged on the late branch (GATE reading). 0 ("same") is reported as info.
Derated |d| = max(|d + p_up|, |d - p_dn|); margin = 416.5 - derated |d|.
Labels: CHECKED = this lane's tool output; nothing is NUMBER-CHECKed.

| corner / droop | nominal max abs d | derated worst margin | crossings < 100 | < 0 | margin bound at d = 0 |
|---|---|---|---|---|---|
| TT, regions (gate) | 201.2 | **-208.7** (sp2-sp3, common cell = root) | 60 | 17 | **-60.7** (8 fail, 33 < 100) |
| FF, regions (gate) | 182.9 | **-121.1** | 34 | 9 | +13.3 |
| TT, same (info) | 201.2 | -31.1 | 12 | 8 | |
| FF, same (info) | 182.9 | +11.8 | 9 | 0 | |

All 60 TT crossings under 100 ps have their last common cell in tree levels 0-4 (8 at the root, 25 at L1, 16 at L2,
5 at L3, 6 at L4). Their unshared branches are 4-6.1 ns of the 5.8-6.2 ns insertion (44 stages from the root).
Pessimism is about 7.8 % of the unshared delay at TT and 7.6 % at FF (droop 5.1 % on the cell half, nets +-3 %, random,
0.21 %/mm), or 4.9 % without droop.

## Conclusion (CHECKED by tool run)
The derated margin is negative, and the equal-length fix CANNOT close it. Even with d = 0 at every crossing, 8 TT crossings
fail (bound -60.7) and 33 stay under 100 ps. The cause is the unshared depth of the crossings that straddle the top tree
cuts, not the leaf-to-entry leg length.
For margin >= 100 ps at |d| <= ~50 ps, every crossing needs unshared delay <= ~3.4 ns TT (droop regions) or <= ~5.4 ns (droop 0).

Structural options (ASK COORD):
- (A) A crossing-aware clock topology in which every landed pair diverges late: a dataflow-following trunk / fishbone along
  the spine, or neighbour-forwarded region clocks across the top cuts (10-16 neighbour-relative clocking).
- (B) PDNSim region droop to replace the one-sided 5.1 %. Alone it is not enough: TT stays at -31.
- (C) A per-crossing ring OFFSET centred on the nominal d. This needs p_up + p_dn < P minus the guard; TT regions is
  ~950 ps > 833, so it is not enough alone.
