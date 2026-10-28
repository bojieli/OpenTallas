# DIE-HEAD 12.14b one-page estimate: HEAD locality region map + spine_fishbone feed (2026-10-27, UNCHECKED unless marked)

Plan: LAND-HEAD-1 compose/fb1_lat.json (326 partitions, 427 ports, 211,813 bits). Feed: LAND-HEAD-3 routed spine_fishbone
(sfbR; die GRT0 incl clock TT+FF, 932 cells; numbers CHECKED by NUMBER-CHECK 20:26). Readings per the COORD 20:26 rule:
CURRENT ring = 416.5 - derated |d|; COUNT-ALIGNED = window 403.4 TT / 407.0 FF, ONE design-time count K for TT and FF,
residual counts; whole-cycle step (P) or half-cycle placement (P/2). Script: scripts/ca_reading.py (reproduces the
NUMBER-CHECK: whole -89.4 vs -91.3, half +133.0 vs +129.2 on all 427 ports).

## (1) Maps on the routed sfb feed (crossing ports only; intra-region ports become die STA related pairs)

| map | regions | bits inside | crossings | current TT/FF | CA whole TT/FF | CA half TT/FF |
|---|---|---|---|---|---|---|
| region = partition | 326 | 0 % | 427 | -270.4 / -170.7 | -89.4 / -87.4 | +133.0 / +133.0 |
| LAND-HEAD-3 27-region (link_forward, <=1.3 ns DME) | 27 | 82.8 % | 93 | -270.4 / -170.7 (56/22 <100) | -22.3 / -72.2 | +133.0 / +158.5 |
| **feed36 (refined, this lane)** | 36 | **84.1 %** | **78** | -270.4 / -170.7 (78/78 <100) | -89.4 / -87.4 | **+133.0 / +236.4** |

Current ring: FAIL on every map. The fails are the nominal d of the travelling feed (rib heads 579-616 ps, 255 ps per
708-um channel hop); no region map changes them. A balanced (d~0) feed carries >= ~3.9 ns unshared at the top split
(LAND-HEAD-3 bound <= ~+70 TT; locality.py top feed on the 27 map -140 / -47). => current ring cannot close HEAD.
Count-aligned whole-cycle: FAIL (one K cannot hold TT and FF for d ~600 ps). Count-aligned + half-cycle placement:
PASS on every map, worst +133 TT (chE2_r/chE5_r rib heads, d -616/-532).

## (2) Separate shallow balanced local trees below the feed cost margin (estimate)
Each side of a crossing gains the local insertion I as unshared clock (derate scaled linearly, scripts/local_tree_est.py):

| I per region tree (ps) | 0 | 400 | 600 | 900 | 1200 | 1900 (27-map bbox) |
|---|---|---|---|---|---|---|
| CA half worst (27 map) | +133 | +84 (8 <100) | +59 (11) | +23 (41) | -14 (63) | -83 (72) |
| current TT | -270 | -320 | -344 | -381 | -418 | -503 |

locality.py (bbox H-tree regions + forwarded feed) on the same maps agrees: 27 map FOLD -487/-268, PAD +117/-302;
feed36 FOLD -545/-31, PAD +4/-337. => A balanced local tree on top of the feed fails once I > ~350 ps.
The region clock must be the feed itself: each region's local clock = its own fishbone rib half (a spine form, 12.13b
"own local tree/spine"), fed from the spine at the rib root.

## (3) Refined map feed36 (crossings on the feed tree by construction)
Rule: two partitions share a region iff their port's routed nominal offset |d_TT| <= 300 ps (scripts/feed_map.py).
Result: 12 rib halves (24 partitions each, one per channel-row half), the spine column (sp0..sp5 + ctl/host, spine DME,
d <= 109 ps inside), station-row pieces. All 78 crossings are rib-head (rib root <-> first column) or station-row
crossings: each joins a feed parent and child (0 off-feed). Max span is large (rib half 8.1 x 2.1 mm) but the clock is
a travelling rib, not a deep tree; insertion is set by the feed (2.47-6.01 ns TT).

## (4) Intra-region die STA (related pairs, estimate)
Neighbour hops inside a rib carry the travelling clock offset (<= 255-300 ps per 708-um hop, clock flowing with the
rib). Setup TT: 833 - 60 unc - ~300 skew - ~250 hop (clk->q + repeated wire + setup) ~ +220 ps when the skew is against
the data. Hold FF: skew with the data ~220 ps + 25 unc needs ~150-250 ps of data hold buffering on with-clock hops
(allowed, 12.8 v4.6+). Spine region: d <= 109 ps nominal but unshared up to 2.43 ns at the spine DME top split
(sp2<->sp3): ~190 ps OCV pessimism in die STA (CPPR to the split only). Estimate: feasible, needs die STA on real views.

## Tracks
Not binding: locality.py worst boundary demand/supply 0.28 (feed36), 0.23 (27 map).

## (5) Built and routed (DIE-HEAD, CHECKED-own, not NUMBER-CHECKed)
Feed rebuilt with rib-head repeater spacing 250 um (COORD 20:26 slew item): `die_trial kit --tree-form spine_fishbone
--tree-site-slide --rep-um 250` on fb1_lat.json; 997 repeaters, 1,493 cells, 0 illegal sites; combined die GRT incl clock,
50 congestion iterations, -critical_nets_percentage 0: overflow 0 on all layers TT and FF, 0 GRT-0113/4; max tree-cell
input slew 252 ps TT (was 398.9; 0 max-slew violators), entry slew max 56 ps. Run intel2:/srv/opentallas-scratch2/claude/die-head-1/sfb250c.
landed_phase_ocv on these arrivals, crossings of each map:

| map | crossings | current ring TT / FF | count-aligned (MESO-COUNT-1 count_align_plan.py @258bc16208) | 20:26 half-cycle reading TT / FF |
|---|---|---|---|---|
| part | 427 | -251.7 / -145.8 (228/78 <100) | 427/427 D4, 0 FAIL, 325/325 tree edges clean, latency 2:380 3:47 | +135.2 / +131.1 |
| 27-region | 93 | -251.7 / -145.8 (46/22 <100) | 93/93 D4, 0 FAIL, 26/26 clean, high-guard slack 890 ps | +144.9 / +150.2 |
| **feed40 (feed36 box-clean)** | **94** | -251.7 / -145.8 (78/72 <100) | **94/94 D4, 0 FAIL, 39/39 clean, high-guard slack 1,182 ps, latency 2:51 3:43** | +149.1 / +131.1 |

Count-aligned low-guard margin = the T/8 aperture (104.1 ps) by construction of that tool version; the 20:48 ruling
(K from the derated lag) is pending in count_align_plan.py, so no count-aligned ps margin is quoted as a gate number.
Head pass (fallback_land plan, map:feed40): 4 serial crossings + 2x5 gather = +42 cycles per head pass vs +171 for
region = partition (UNCHECKED composition). Ring storage 39,648 bits (0.185 mm2 logical, 0.06 % die) vs 211,813.

## (6) Plan event status
fallback_land.py compose on map:feed40: requirements OK (94 crossings, 376 scalar pins) but types 16 -> 21 (hd_serdes,
hd_spn, hd_st_turn, hd_tile split: replicas with/without a ring) and the dataflow monitor FAILS (315 parts cannot reach
the observer: clock_landing_plan._dataflow_tree walks landed ports only; with regions it must walk intra-region links
too). The reset monitor run timed out (>15 min). => The event needs a shared-tool change (region-level monitor) and a
choice on the 5 split types. G0/G0C on the event not run (no composed plan); base plan G0C PASS 0E unchanged.

## Verdict
Current ring: no HEAD map/feed passes (structural, -252 TT best routed). Count-aligned ring (MESO-COUNT-1, adopted
conditionally 20:38): feed40 fits 94/94 D4 with every start-tree edge clean. Recommended HEAD form = sfb feed (rep 250)
+ feed40 map (region clock = its fishbone rib half), 94 rings, +42 cyc/head pass. Ring count follows the map: 94.
