# DIE-HEAD-3 12.14b one-page estimate: HEAD re-cut at in-region skew <= ~150 ps (2026-10-27 21:50 PDT, UNCHECKED unless marked)

Base: claude/die-head-1027 (DIE-HEAD-2 0a3f82ed5b + origin/main 61e18c35b0). Clock = the routed sfb250c spine_fishbone feed
(die GRT0 incl clock TT+FF, unchanged: a re-cut moves only which plan ports are rings, not the feed).
Pipeline per map (all scripts in this dir): feed_map(_x).py -> box_fix.py -> mk_proof.py -> MAIN die_sta_related.py
(--clock-ocv table g021, --clock-droop shared by region, data droop class, declared-budget views, HB4 plan + abutted
sensitivity) -> fallback_land plan/compose --monitor region -> ca3.py (count-aligned margins, arrivals x1.05 spice scale,
K from derated lag, window [0.5T+ap,(D-0.5)T-ap], PROVISIONAL until MESO-COUNT-2).
Reproduction check: feed40 (dmax 300) -> 40 regions/94 crossings, FF hold -430.7, HB4 TT -232.19, CA worst low 203.1
(DIE-HEAD-2: -429.2 / -232.2 / 203.0).

## Why the re-cut is coarse: rib hops are 255-300 ps, nothing sits between 150 and 300
| dmax | regions (box-clean) | crossings | bits inside | in-region pairs | TT setup / FF hold zero-logic | HB4 plan: TT / FF | HB4 abutted: TT / FF | HB4 cells |
|---|---|---|---|---|---|---|---|---|
| 300 (feed40) | 40 | 94 | 84.1 % | 294 | +149.4 / -430.7 | **-232.2** / 0.0 (72 <0) | - | 716 k |
| 200 = 150 = 120 | 304 | 358 | 10.9 % | 30 | +392.4 / -234.6 | **+8.29 / +9.25** | +35.0 / +3.4 | 54 k |
| 100 | 304 | ~360 | 12.8 % | 30 | +392.4 / -234.6 | +8.29 / +9.25 | | 57 k |
| hybrid hyb2 (dmax 300 + forced cuts) | 118 | 172 | 63.3 % | ~220 | +149.4 / -351.7 | **+8.29 / 0.0** | +2.6 / 0.0 | 356 k |
The worst in-region pair after HB4 is the SAME in every map: spine sp5->sp4 (d <= 109 nominal, but 2.43 ns unshared at the
spine DME split, CPPR only to the region root): 6 HB4, setup 556 -> +8.29. It is the d150 limiter, not the rib.

## The "data with the rib clock" question (answered by the numbers)
With-clock links (launch upstream, capture downstream: chX_o rib hops, o9->o10, o10->turn) are the HOLD-bound ones:
capture late by d, FF zero-logic hold -351..-431, setup +680..+709. HB4 fixes hold at FF 44.6 ps/cell but costs TT 91.3
ps/cell (x2.05), so k=10 eats 913 ps setup -> -204..-232. Counter-flow links (b rows, launch downstream) are fine in
region: hold >= 0, TT setup >= +149.4. So making data flow WITH the clock is the expensive direction here; the cheap form
is the hybrid: only the 78 with-clock hops whose HB4 setup goes negative become crossings, counter-flow links stay in
region (hyb2: 172 crossings vs 358, 63 % bits inside vs 11 %), at the price of 356 k HB4 cells (k up to 8/bit) and a
+2.6 ps abutted-model margin.

## Crossings, types, TOK
| map | crossings | CA (x1.05, provisional) | K sigs | types (landed mask / + per-instance K) | head pass | HEAD cyc/token vs 10,357 | ring FF |
|---|---|---|---|---|---|---|---|
| feed40 | 94 | 94/94 D4, low 203.1 | K1/K2 | 21 / 23 | +42 | 9,324 | 0.061 mm2 |
| **d150** | **358** | **358/358 D4, low 104.1, high 1255** | K1 195, K2 163 | **22 / 26** | **+108** | **9,390 (slack 967)** | 0.287 mm2 |
| hyb2 | 172 | 172/172 D4, low 104.1 | K1 129, K2 43 | 22 / 25 (hyb) | +63 | 9,345 | 0.128 mm2 |
| part | 427 | 427/427 D4 | | | +171 | 9,453 | 0.323 mm2 |
TOK = 9,282 (tok16-head) + head-pass added cycles (fallback_land plan, 3 cyc/crossing; CA latency is K+1 = 2-3 <= 3).
Types: 16 -> 22 is +37.5 % (> 25 %: MESO-INTEG-1 ruling says COORD batches 'K as strap' to OWNER); compose landed-mask
split = 6 types (d150: hd_serdes/hd_spn/hd_st_turn/hd_tile/hd_turn_a/hd_turn_b).

## Verdict
d150 PASSES the estimate: in-region TT setup +8.29 / FF hold +9.25 after HB4 (plan model; +35.0/+3.4 abutted), all
358 crossings fit count-aligned D4, TOK 9,390 < 10,357. Thin (+8 ps) and set by one spine pair, not the rib; real views
(task 3) decide. hyb2 also passes with half the rings and +45 fewer cycles but 6.6x the HB4 cells and +2.6 ps abutted.
Build d150 (COORD default) now; hybrid kept as the ASK alternative.
