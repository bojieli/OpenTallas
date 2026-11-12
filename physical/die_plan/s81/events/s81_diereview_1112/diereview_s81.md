# S81 whole-die review (S81-DIEREVIEW-1), plan ready12f ed5185a41503 (BEFORE = ready11r db1da17a93ab)

Renders (host:path, all epyc4 /srv/opentallas-scratch2/claude/s87bind/dierender_1112/): before/die_before.png (+_q0..q3 with per-tile labels: name, WxH, fill%, aspect, ft band N/S|E/W um, taps, hops>405), after12f/die_after12f*.png, after12f/leaf_*.png (leaf close-ups: cores, ft bands blue, stations, taps), proposed/die_pertile_content_vs_slot.png (content-sized tile inside each lattice slot), proposed/dataflow_block.png (family-level data flow, bits / cycles), proposed/sizing_r12f.json (per-type slot table), proposed/sizing.txt. Local copies: scratchpad/dr/img/.

## What the die is
31950.7 x 25436.2 um = 812.7 mm2 (partitions 783.3 mm2, 96% util). It is a rigid LATTICE of 22 columns x 20 rows of 1442.88 x 1226.88 um tiles (1.77 mm2), set by the col_h9/h10 frame-bank tiles (6 columns each side). Everything else was dropped into the same lattice or into multiples of it: svc tiles 1442x2747-2851, lk serdes 2885x1226, phy_hbm 8657x1226.

## Families (core fill = hard-core area / tile; cell fill = glue cells x 0.26 um2 / tile; cells_est.json glue numbers)
| family | types/tiles | mm2 | core fill | cell fill | problem |
|---|---|---|---|---|---|
| ot_s81sl_leaf | 75/75 | 132.8 | 34% | 0.2% | CHANNEL by design: 8 landed leaf bands, cores bbox 66% of tile, ft bands 530 um of 1443 (N/S); not empty, not oversized by more than ~24% (content tile median 76% of slot). 25 taps/tile, hops>405 0 |
| slice_station | 46/46 | 81.4 | 2.1% | 0.1% | the only truly empty family: lane carriers only; 38 of 46 need <15% of their slot (need_w 173-1201 med 536, need_h 173-795 med 190). 10% of die area for 1.9k taps worth of stations |
| col_h9/h10 r0/r1/r2 | 38/216 | 106x3 + 21x3 | 46-58% | <1% | macro columns, fine; they set the lattice |
| serdes (lk) | 11/14 | 49.6 | 1.1% | n/a | cells_est has no glue for serdes: content UNMEASURED in this table; clk_pma_rx single tap 22k sinks (GEOM-VIS-1 corpus, serdes t4/t12/t14); plan taps list is 0 for serdes |
| svc rs hi/lo/pvso | 15/16 | 64.6 | 68-71% | 0.4% | aspect 2.0; 13 internal hops >405 (svc_hi 9, lo 3, w 1; svc_15 has 7) |
| c1x_C / lepe / lepw / iq / kv512 / c3x slices | 21/21 | 35.4 | 24-38% | 1-6% | hops>405: c1x 5, lepe_mu_LP 4, iq 2, kv512 2, lepe_mu_C 2, c3x 1 |
| kv_leaf | 5/5 | 12.4 | 16% | 0.2% | street rule: base 24/24/25 violations on t3/t4/t5 |
| phy_hbm | 1 | 10.6 | 0 | 0 | PHY macro tile (hard) |
Taps in the plan: 8168 (leaf 1875, slice_station 1913, svc 1024, col_h ~2700). Sinks per tap are NOT in the plan file (kit measure); only the GEOM-VIS-1 corpus has them (clk_pma_rx 22k, q_b0xx 10-29k).
Landed hops: 780 TT / 568 FF hops over the 416.5 ps window (REACH-FIX-1 list reach_hops_ready11r.tsv; worst phy_hbm<->eng 1616 ps). Street rule: STREET-RULE-1 reports 2599 S81 violations remaining after pass 1 (their number).

## Re-derived slot sizes (sizing.py; rule: cores keep shape -> leaf = cores bbox + 43.2 street margin each axis, ft bands must fit; station = lane bands + 2 streets, min 172.8; others unchanged)
Per type: sizing_r12f.json. Totals if every tile took its own size: leaf 132.8 -> 101.7 mm2 (-31), slice_station 81.4 -> 10.6 mm2 (-70.8), kv_leaf -6.9: -109 mm2 (-13%).
LATTICE LOCK: when the column/row constraint is applied (tile faces abut: a column's tiles share a width), the die shrinks only -2.8% (31743 x 24883 mm), and that gain is channel gaps at the svc rows, not tiles. Reason: columns 6 and 15 hold 15/17 slice_station tiles but also 4 LP slice tiles (lepw/lepe mu/mus LP) that need the full 1443; every other column holds leaf/macro/phy/serdes tiles that need it too; every row holds col_h tiles. So NO column or row can shrink without moving specific tiles (LP slices, lk serdes, svc) = a hand re-grid of the centre block plus regeneration of every port window on every shifted face.

## Why does the plan have so many problems "when done in the first place" (evidence)
1. Slots came from the old frame-bank grid, not from content: the whole die is one 1442.88 x 1226.88 lattice; slice_station got 10% of the die for ~10% of that area worth of lanes; leaf and serdes sit in tiles whose size nobody derived from cores + lane bands (leaf cores already span 70-97% per axis).
2. No pass-through lane budget at plan time: ft bands (530 um of 1443 in a leaf) were sized per lane, but channel capacity vs bits was not a plan check; reach (405 um), landed-hop windows (780 over), street rule (2599) and tap loading (22k-sink tap) were not G0 checks, they showed up later in kit placement and die STA.
3. Each type was closed in isolation (kit per type, G0 per type) with no die-level view of reach/clock/street: the 12 stages of this event are 12 patches of that gap (window, CTAP fold-in, gear, split, R3-SPREAD, kvrevert, reach regs, OTC, street pass 2...).
4. Measurement gaps persist (serdes content, sinks per tap), so some of these numbers are still estimates.

## Decision table (ready12b, one event; ready12 bind unaffected)
| region/family | current | decision | reason | neighbours moved | cycles | risk | owner stage |
|---|---|---|---|---|---|---|---|
| leaf slots (75) | 1443x1227 | KEEP the slot; no shrink | channel by design; cores 70-97% span; shrink needs lattice re-grid; closure problem is taps/reach/street not area | none | 0 | low | R3-SPREAD (in ready12), kvrevert, street pass 2 |
| slice_station (46) | 1443x1227 | KEEP; tell GEOM-VIS-1 the empty-slot verdict is a class mislabel (pass-through carrier); optional later die re-grid -70 mm2 | content tile 10% of slot but column locked by LP slices/serdes; die is not area limited (812.7 of ~858 mm2 reticle) | would move cols 6/15 + 4 LP slices + lk tiles | 0 (hops shorten) | HIGH (all windows) | none in ready12b; separate die-level event only if owner wants area |
| serdes clk_pma_rx 22k tap (14 inst, 11 types) | 1 tap | split into region taps <= ~2000 sinks each (about 11 taps per serdes tile, ~one per 260 um over 2885 um) | tap loading class (91 overloaded-tap types) | none | 0 | med (clock landing windows) | REACH-FIX-1 |
| landed hops (780 TT) | over 416.5 | +1 register per over-reach hop | owner-approved lever | lane re-timing | + up to 1 per hop | med | REACH-FIX-1 |
| internal hops >405 in svc (13) and slices (16) | over | bridges/stations (SEAM-HOP-1 ready10b chains, collector reach <=405) | reach | none | + per bridge (approved) | med | SEAM-HOP-1 / ready12b |
| X-TIER-OTC leaf t1/t8/t12/t55/t58/t72/t75 | form(d) | M8/M9 lanes | slot cannot hold 8 cores + lanes | none | 0-2 | med | X-TIER-OTC |
| street violations (leaf, kv_leaf, slices) | 2599 left | pass 2 legalize; kv_leaf t3/t4/t5 stay on gear form | STREET-RULE-1 | within type | 0 | low | STREET-RULE-1 + kvrevert |
| serdes content (cells) | unmeasured | measure glue/macros per serdes type before any sizing | cells_est gap | - | - | - | DIE-S81 (me) |
ASK to COORD/owner (default = A): (A) keep the lattice in ready12b, fix reach/tap/street/hop classes (above); (B) die-level hand re-grid of the centre block (stations + LP slices + serdes rows) for up to -70 mm2 (-9% area): a separate event, needs a pin/window re-plan generator and all kits re-run; I do not recommend it before ready12 closure data.
