# Qwen compute die: orientation, tile tree-face and pair-mirror search (GEO-Q, 2026-10-15)

Input: `qwen-native-controller-geometry-1015.json` (source f6842ce4a, sha256 c6bb77d8e1a3b111...), 1637 instances,
3331 resolved data buses (1 missing: clk_d2d). Metric: per-bit pin-centre HPWL (bit-um), longest per-bit pin pair,
relay stages at the 500-um per-hop reach, bits crossing >50% of a tile body (M8/M9 over-tile demand, tile obs_top=7).
Baseline: 1742.154 M bit-um, worst leg 21281 um, 2,841,990 relay bit-stages, max 42 stages/bus, critical tree leaf->spine 58 relays.
Assignment-pin geometry only; no route, cut, clock phi-R, halo/PDN, TT/FF or static-cycle qualification.

| Candidate | bit-um | relay bit-stages | stage increases | critical paths | other cost |
|---|---:|---:|---|---|---|
| Band2 F1 MX (historical "3.84%") | -1.51 M (-0.087%) | +1,542 | bword_39/43/47 +1 | — | REJECT |
| Band2 coherent MX | +41.75 M (+2.40%) | +84,776 | 10 | — | REJECT |
| x3_mux R0->MY | -66.2 k | -512 | 0 | x3m 549.7->420.3 um (1->0 relay); x3 -25 um | rst_spine entry +29.5 um |
| xs_tap R0->MX | -135.8 k | -1,566 | xfault_e (1 b) +1 | head_23 3568->3352 um, 7->6 relays | xs_aw +216 um, head_24 +150 um (no stage) |
| tile tree words W->E faces (best: n_b,n_y E) | -98.6 M (-5.66%) | -292,980 | 117 incl. bword_46 42->43 | tree crit 58 (no change) | intra-tile up to 410 M bit-um unbounded: weak |
| PM pair-mirrored columns | -194.1 M (-11.14%) | -358,687 | 48 (24 head hops, 24 xfault) | tree 58->56; head chain W 7->19, E 9->20 | clock trunk +15.7 mm HPWL; 0 rect errors |
| PM-H (head rows 7/8 kept) | -163.5 M (-9.39%) | -320,640 | 48 corridor cor_even_6/9 2->3 | tree 58; head 0; corridor +1 on even cols | clock trunk +15.7 mm; 0 rect errors |
| PM + interleaved word pairs | -242.1 M (-13.90%) | -380,789 | 121 | tree 57 | worst leg +115 um |

PM: each column pair of each 24-column half becomes [64.776 col | even tile MY | 16.464 inner | odd tile R0 | 64.776 col];
station/DVM column of the even tile moves to its W side with MY (tap_d still abuts the tap face). Same pitch, area, masters, rows.
Over-tile crossings 1.867 M -> 1.374 M (PM) / 1.396 M (PM-H).

Reproduce: `cd tools/qwen_split && python3 {orientation_search,tile_tree_faces,pair_mirror}.py <geometry.json> <out>`.
