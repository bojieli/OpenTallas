# LAND-HBM-1 (2026-10-27): HBM landed region partition, price, landing table; OCV pre-check

METHODOLOGY 12.11 / 12.10c. Tool: `tools/die_plan/hbm_land_regions.py` (plan + form -> regions.json, landed_crossings.json,
lane_added.json, summary.json; `--emit-plan` writes a PRICING-ONLY plan copy with lanes[*].fixed_cycles += landed cycles).
Price chain = R13 chain (hbm-mu-quad-3 price3.sh: b1_lane_traversal + cc_price + combine, S2 schedule), copied to
`price_tools/`. Data: epyc2:/srv/opentallas-scratch2/claude/land-hbm-1027 (C16r copy, forms, forms2, price).

## Control
- planU3f reproduced: ds_ar 2.388 / 2.926 / 8.402 %, upper 1905.97 tok/s (CHECKED: equals the HBM-MU-QUAD-3 numbers).
- C16r base (sha 732240f89458): ds_ar 2.388 / 2.603 / 7.751 %, upper 1919.52 tok/s; qwen_ar upper 1.219 %.

## Forms on C16r (K = 3 unless stated; ds_ar loss % vs t_banks; lower / mid / upper; upper tok/s)
| form | regions | landed ports / bits | ring mm2 (4.66 um2/bit, UNMAPPED) | face | fwd | hard-sink rings |
|---|---|---|---|---|---|---|
| part (every partition) | 78 | 601 / 527,734 | 2.46 (0.47 %) | 10.82 / 14.93 / 19.25 (1680) | 4.93 / 7.10 / 12.23 (1826) | (not checked) |
| func (hub/bank/nrow/srow/smN/smS per quad + ROOT + TOP) | 14 | 305 / 255,606 | 1.19 | 4.73 / 8.46 / 13.45 (1801) | 4.41 / 6.20 / 11.42 (1843) | SM hard: yes |
| func4 | 22 | 315 / 260,220 | 1.21 | 4.73 / 8.85 / 13.80 (1794) | 4.41 / 6.60 / 11.79 (1836) | SM hard: yes |
| core (hub+bank+rows / smN / smS) | 8 | 132 / 103,759 | 0.48 | 3.12 / 4.49 / 9.90 (1875) | 2.82 / 4.21 / 9.65 (1880) | 22 ports into hard q_sm* = ILLEGAL |
| **quad (NW / NE / ROOT=root+vsN0-5 / TOP=PHY_N+mca/mcb+vsN6)** | 4 | **60 / 53,841** | **0.25 (0.05 %)** | **3.12 / 3.32 / 8.37 (1906.6)** | 2.82 / 3.01 / 8.12 (1911.9) | 0 |
| quad K=2 | 4 | same | same | 2.88 / 3.07 / 8.17 (1910.9) | 2.67 / 2.88 / 7.99 (1914.5) | 0 |
All form prices UNCHECKED (model, R13 chain). quad K=3 face = +0.62 pp upper vs C16r, at the owner-accepted 1906.
Structural: q_sm0..3 are HARD partitions, so any form that separates an SM from its soft row puts the landing ring in a
hard macro (core/func/func4) -> illegal without SM rebuilds. quad is the only coarse form with 0 hard-sink rings
(vsN6 joins TOP so the PHY-bound L9 lands in soft vsN6, not in PHY_N).

## quad on C18 (HBM-STREETS-2 base, die_plan 6a711a87b7e7): c18_quad/
Identical crossings (60 ports / 53,841 bits, 0 hard sinks). Crossing sites (bits): centre seams x=13357 / 15042 at
y 5288 / 8225 / 11172 (NW<->ROOT 24.1 k, NE<->ROOT 13.9 k); TOP seam (6679,16468) / (21721,16468) 7.1 k each side;
ROOT->TOP at vsN5/vsN6 (14200,14964) 5.6 k. regions.json carries `part_region` for die_trial --region-trees.

## OCV pre-check (COORD 19:14 ruling, landed_phase_ocv) -- ANALYTIC, no arrivals yet, UNCHECKED
Rule: every landed pair <= ~3.4 ns unshared clock at TT. HEAD measured ~0.34 ns per mm of root->leaf tree path
(6.1 ns / ~17 mm; derived, UNCHECKED). An equal-depth region tree puts every leaf, including the crossing leaves,
at the full region insertion. quad NW/NE from a seam-sited root: ~21.6 mm path -> ~7 ns per side -> FAIL by
construction. Even func regions (13.4 x 4.5 mm, centre root, ~9 mm) are ~3 ns per side (~6 ns per pair) -> FAIL, and
they cost -6..-7 % (and are illegal on the hard SMs). Regions small enough to pass (~5 mm root->leaf per side)
are the part form or finer, at -12..-19 %. So on HBM the crossing-aware feed is the deciding item, not the cut.
Candidate feeds for quad (all crossings sit on 3 seams, which makes this possible):
 (a) seam-rooted region trees + a short shared seam trunk. Each region's crossing-side leaves are fed from a trunk node shared
     with the neighbour (LCA at the seam). This needs a non-equal-depth (fishbone/spine) region tree, and the intra-region
     related pairs then see the trunk gradient (~0.34 ns/mm x 405-um hop ~ 140 ps nominal; hold buffers under 12.4a a1).
 (b) neighbour-forwarded region clocks across the seams, as LAND-HEAD-3 is building. Reuse its tool, not a fork.
Needs a COORD ruling. Next steps: region trees on C18, then die GRT incl clock, then landed_phase_ocv on the arrivals.
