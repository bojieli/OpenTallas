# FABLE-PD-KV-2300: KV D25e2 / D25f structural review, hg routing, die hold form, pc and hub_Wi (2026-11-19 23:20 PST)

Reviewer: FABLE-PD-KV-2300 (Fable). Technical PD, read-only: no job launched, stopped or patched; no plan edit.
Marking: **M** = I computed it this round from the named file. **R** = a lane post. **I** = inferred. **P** = proposal, not proven.
Gate used: route DRC 0, TT >= -42, hold >= 0, bind + LATCHECK, hops <= 405 um. Nothing below is a new gate or a hold.
`tools/failure_breakdown.py` (22:40 run on intel2): KV types 6 / 56 signed, cores 68 / 69; rows are running 35, lint advisory 13,
other flow error 1 (kv3_hub_Wi), waits on child core 1. It names no technical class, so the classes below come from kit files.

## 0. Headline

1. **D25e2 did not bind (R, KV-D23-COMPOSE 22:48).** One error: PARAM_REGEN ECTL round trip 25 vs 26, caused by the fall K rows.
   KV-CROSSING posted 4 corrected rows at 22:50. D25e3 = D25e2 + those rows; D25f rebases on D25e3. So the D25f window is open.
2. **hg k10: 54 % of the 21,073 overflow lies inside hard-core outlines, 62 % on gcells with capacity 0 (M).** The hot spot is not
   mainly the 16-um gap (535 inside the gap). It is one hop with a hard core between its two stations (8,504 over head2_e6) and
   one trunk leg through the partition clock entry cluster (3,431). **k11 (M2) round 5, read at 23:10 (M): total 19,249.** It
   clears the e6 zone (9,463 -> 602) and moves the load into the middle column gap (1,076 -> 7,911), which carries the clock
   and reset entry structure. M2 is not ready as rows.
3. **Die hold -165 / -156 is an all-pairs number (M).** The die STA times 1,529,668 tap pairs. On the 466 regular tap pairs of
   pv_N_0 that carry real zero-logic hops (from the v8b kit), the clock damage is p95 48 ps, max 115 ps, and 4 pairs exceed the
   75 ps kit window. Leaf balancing does not move it (am300 measured). The form is: related pairs only, lockup or a per-pair
   window in the kit, and a tree that keeps related taps within about 5 unshared stages.
4. **kv3_pc has an unreported floorplan stop (M).** The pilot kit on the E2 core views died on PDN-0006 at 13:42 PST. D25e and
   D25f reference the same LEFs on all 6 pc types (32 partitions).
5. **Five items named in the D25f scope are not in the staged plan ba57226730de (M):** `r_dly_spread_station_um`, `r_dly_lockup`,
   the pc core-tap v2 rows, any depth-16 sidecar row, and M2. Details in section A.

## A. D25e2 / D25e3 / D25f before bind

Read: epyc8 `/srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg13_ba572267_t99007dc_d25f/physical/die_plan/qwen_kvsys/plan_of_record/`
(`plan_c.json` sha ba57226730de, `eW_sidecar.json`), the D25e2 plan d96baf37b98c and the D25e plan a5a8c6b96e5f beside it.

| item | state in the staged D25f | check | verdict |
|---|---|---|---|
| rls rows, 15 types + hgi_v1 x2 (M) | present on 17 types | 0 copy sites inside a hard core. Trunk legs: see A1 | 7 hg types have a pinch (I); 3 hgi types marginal |
| HST3FB polyline on hgi_v1 x2 (M) | `u_hst3_g` [[200,950],[650,950],[650,618]] | leg x 650 crosses the clock entry cluster | measured 3,431 (k10) and 3,828 (k11) there, see B |
| M2 (k11) | not staged | adds eN +2, tN +2 cycles: lanes move, LATCHECK and token sim apply | k11 round 5 is 19,249: not ready, see B |
| pc offsets v3 + pv DME + snake | clock config only, not a plan row | plan pcc / pcf core taps are still 318 / 196 (M) | pairing open, see A2 |
| `r_dly_spread_station_um`, `r_dly_lockup` (form C) | both absent (M); tree tools are 99007dc, rows need main >= 29d0a6105e4c | 0 cycles, gen-only (R) | re-tool, then rows_C; see A3 |
| pv tail_clear rows | in D25e2 (R, 19:53) | not re-checked | - |
| kv3_hub_Wi SRAM leaf (M) | `kvs_emb.physical_parts`, origin (1058.4, 1566.0), 171.288 x 77.784, R0 | see A4 | PASS |
| fall rows at depth 16 | none: sidecar depths are 1..10, L516_0 is K -50 / depth 4 (M) | see A5 | not staged; bind-time if taken |
| ECTL RT fix, 4 rows (R, 22:50) | for D25e3 | margins lo +389..+1167 on the pcsink_fix tree; the v3 tree moves pc sinks by <= 38 ps | cannot break them (I) |

### A1. rls rows: reach and pins

Capacity basis (M, k10 `congestion-5.rpt`): gcells in the landing gap carry 25 vertical tracks per 0.57 um, so a channel gives
about 43.7 usable tracks per um of width. 807 bits need 18.5 um, 1,063 need 24.3 um, 1,560 need 35.7 um.
Check (M, geometry from the plan): the straight leg between copies a, b and c of each leaf, free width between hard cores.

- kv3_hg_v1, v1p2..v1p6: `u_hst0_t2` leg a-b passes `cl_i_slg_Q_N_krsp` (x 8.64-51.84, y 371-590). Free width 8.64 um east of it
  (to head0_e2 at x 60.48) and 8.64 um west of it. 807 bits against about 377 tracks per side. kv3_hg_v3: both legs, 8.64 um.
- kv3_hgi_v5, v7, v8: `u_hst2_t2` legs at 16.8 um, 807 bits against about 735 tracks. Marginal.
- kv3_hgi_v3, v6 (`u_hst2_t2`) and kv3_hgi_v5 (`u_hst3_t2`): copies a and b sit at different x and a `cl_ft*_i` core lies on the
  straight line between them. The leg needs a jog; my straight-leg model cannot size it.
- The other legs (51 of 68) are clear, 77 to 104 um.

This agrees with the 14 `narrow_sites_lt_20um` flags in the rows file; the rows file treats them as "check in the first kit".
No hg-family kit has a GRT result to confirm it: KV-D25d kv3_hg_v1p4 (epyc10) stopped at place. So this is a prediction (I):
the same demand-to-capacity ratio as the hgi_v1 landing gap (1,560 / 720 = 2.2) appears on 7 types (807 / 377 = 2.1).
Also (I): `cl_i_slg_Q_N_krsp` is an east-west landing of 1,063 bits whose east face is 8.64 um from the head0_e2 wall. If its
outputs leave on the east face, that is the hgi_v1 class before any rls row. Not opened.

### A2. Clock: pairing and tap set

- Pairing (M): kv3_pc_v1 core taps in D25e, D25e2 and D25f are pcc 318 (FF 257.58) and pcf 196 (FF 158.76). That is the
  pcsink_fix pair (earliness 68). The v3 tree delivers pcc +30. Core-tap v2 rows (pcc 68 -> 30, 22 pins) are not in the plan.
  One without the other puts 38 ps of false pcc skew into declared-insertion die STA.
- Tap set (M): every DIE-CORETAP tree, v3_pvsnake included, is built on the D25c plan 4a40f1db. kv3_pv_v8 in D25c, D25d4 and D25e
  has 23 core taps and density taps (pv_N_0 has 271 die taps). D25e2 and D25f declare 24 core + 131 explicit taps. The v8b kit
  names 343 taps, 127 of which are not in the D25c die tree. So -165 / -156 and CA 3,915 / 3,915 describe a tap set that
  D25f does not have.
- Form C adds 54,196 latches (R) on 159,831 delay-line flops. They are clock sinks, with `OT_TAP_CAP_RECHECK=0`.

### A3. Form C rows (pv same-tap / lockup): latency and reach

- 0 cycles and no lane change (R). Kit LEC is latch_to_wire against the unchanged die RTL.
- Setup through a lockup hop is a half cycle: 416.5 ps minus latch delay, capture setup and the pair skew. With the connected
  pair damage of section C (p95 48, max 115 ps FF) the second half hop keeps about 240 ps at the worst connected pair (I). A full 405-um hop does not fit a
  half cycle; the form relies on the latch sitting mid-hop (R). `r_dly_spread_station_um` = 405 leaves no margin for that.
- Die STA today has no half-cycle class for intra pairs. After form C the pv cross-tap pairs must be timed against T / 2:
  setup +547 / +602 becomes about +131 / +186 (I), hold gains T / 2.
- Nothing is proven yet (R): v8h and v8j were admitted at 06:47Z.

### A4. kv3_hub_Wi SRAM leaf

M: 32.4 um to the N face, 49.0 um to the E face; no hard core, reserved clock site, reset local tap, ft register or internal
station within 10 um; nearest taps clk_t58 at 11.6 um and clk_t23 at 19.9 um. LEF: 1,587 pins, all M4, on the west and east
edges (x 0 and 171.264); obstructions M1-M4 only, so M5 and above are free over it. About 790 M4 pins escape into the 49-um
east strip, where the N-face emb_tx_payload pins (x 1197-1262) also land: read that strip in the first hub_Wi GRT.

### A5. Fall rows at depth 16

- M (epyc10 `kv-crossing-1119/F2/ca/count_align_bind.json`): 30 crossings at depth 16, 26 of them pc_WN_2 <-> pc_WN_3 plus
  phy_WN_3 -> phy_WN_2 (K -9 or +17, L_hi 5.9 to 6.6 ns). R: on the pcsink_fix tree the same 26 sat on the WS side.
- M: the shipped sidecar is another form (L516_0 = K -50, depth 4, sched_lat 2). The F2 rows cannot be folded onto it.
- M: pc_WN_2/3 and pc_WS_2/3 are one type, kv3_pc_v1__cl7f648944 (12 instances), with 0 hard landing cores: the rings are soft
  logic, so depth 16 is an RTL parameter, a bind input and a LATCHECK item. phy_WN_2/3 is kv3_phy_v1, which has no live wave row (probably signed, not confirmed): a re-sign.
- The set moves between WS and WN when the tree changes. It is a property of the tree, so the rows are only valid with the tree
  they were planned on.
- The D25e2 failure is the cost model: K rows that split one regen group cost a bind of about 3 h (03:53Z to 06:48Z).

### A ranked fixes

| rank | fix | evidence | owner |
|---|---|---|---|
| 1 | D25e3 with the 4 ECTL rows; before any further K or depth row, run the `kv_regen` frame check alone on the rows (P; I did not time it) | D25e2 bind lost on one PARAM_REGEN class (R) | KV-D23-COMPOSE, KV-CROSSING-1119 |
| 2 | D25f: core-tap v2 rows in the same event as the v3 clock config, or neither | plan 318 / 196 (M) | KV-D23-COMPOSE, DIE-CORETAP-1119 |
| 3 | Re-run the v3_pvsnake chain on the D25f plan (ot-run, epyc10; the last chain took 52 min) | tap sets differ (M) | DIE-CORETAP-1119 |
| 4 | Re-tool D25f to main >= 29d0a6105e4c, apply rows_C; station 380 instead of 405 (P) | keys absent (M) | KV-D23-COMPOSE, FABLE-FIX-KV-PV-2140 |
| 5 | Re-time the shipped D25e3 sidecar in fall form on the D25f v3 tree; take depth-16 rows only for crossings that fail there | forms differ (M) | KV-CROSSING-1119 |
| 6 | hg_v1 family: read the krsp gap bin in the first D25e kv3_hg_v1 GRT (placing since 20:54). If it repeats: P, shift head0 column e0/e2/e4/e6 east by 17.28 um (gap 25.9 um, 1,130 tracks; mid-column gap 60.5 -> 43.2) | geometry (M), no GRT yet | FABLE-FIX-KV-HG |
| 7 | HST3FB: see B ranks 2 and 3 | k10, k11 (M) | FABLE-FIX-KV-HG |

## B. hg / hgi: what closes routing and timing

Source (M): epyc9 `/srv/opentallas-scratch/claude/opus-kv-hg/k10/gen/kv3_hgi_v1__cl141fc26e/run/reports/asap7/dp_kv3_hgi_v1__cl141fc26e/base/congestion-5.rpt`,
9,675 gcell records, total 21,073 (V 13,512, H 7,561), binned against the hard cores of the plan.

| where | overflow | on capacity-0 gcells | reading |
|---|---|---|---|
| inside hard-core outlines, all | 11,284 | - | 54 % of the total |
| head2_e6 (x 77.76-293.76, y 1002-1218) | 8,504 = H 5,165 + V 3,339 | H 4,884 | H sits 0-60 um inside the west face at y 1075-1175; V sits at the north edge (y 1200+: 2,270) and the south edge (476) |
| the 16.4-um gap, landing core to e6 | 535 (V) | - | 720 usable V tracks per row |
| head2 / head3 channel, x 600-700, y 500-1000 | 3,561 (V) | 2,315 | 3,431 of it at y 750-800, x 610-670 |
| middle column gap x 294-389 | 1,076 (V) | - | - |
| whole die, capacity-0 gcells | 13,051 | - | 62 % of the total |

### Root causes

1. **A hop with a hard core between its stations (8,504).** In k9 / k10 the tN path is r0 (133, 1270.08) -> s1 (200, 950). Both
   x values lie inside the e6 x-range, so every route crosses e6. Around e6 the hop is 515 um (west) or 575 um (east). The
   router goes over e6 on the vertical tracks that exist there, and has no horizontal layer to get on and off: 4,884 overflow
   on capacity-0 gcells in the first 60 um of e6. The Manhattan hop check (387 um, mine at 19:50) cannot see this.
2. **The trunk leg through the clock entry cluster (3,431).** The fallback polyline I proposed at 19:50 descends at x 650 from
   y 950 to 618. The plan puts the partition clock and reset entry there: `tap_um` (639.36, 760.32), reserved die_clock_tree
   rects (M1-M7) at x 607-697, y 692-791, the largest [639.09, 759.78, 671.544, 765.18], taps clk_t23 and clk_t41, the reset
   spine pin at (630.72, 760.32). That was my error: I checked the polyline against hard cores only.
3. **Landing pins that face a wall (I).** The landing core spans y 1097-1415; e6 covers y 1097-1218. About 595 of 1,560 east-face
   pins (38 %) face the e6 wall and must turn in a 720-track gap. Measured overflow in the gap itself is only 535.

### k11 (M2) round 5 (M, `k11/k11_edit.py` and `k11/.../congestion-5.rpt`, written 07:08Z)

M2 keeps r0 at (133, 1270.08) and puts r1 (340, 1110) and q (340, 950) in the middle column gap; the hst3 leg is unchanged.

| zone | k10 | k11 |
|---|---|---|
| total | 21,073 | 19,249 |
| on capacity-0 gcells | 13,051 | 10,174 |
| inside hard-core outlines | 11,284 | 3,271 |
| x 0-200, y 1000-1300 (landing core and e6 west side) | 9,463 | 602 |
| head2_e6 outline | 8,504 | about 1,600 (H 1,556 on capacity 0, now 120-200 um from the west face, beside r1) |
| head2 / head3 channel, y 700-800 | 3,431 | 3,828 |
| middle column gap x 294-389, all y | 1,076 | 8,135 (V 7,911) |
| of it y 900-1000 / y 1002-1218 | 154 / 620 | 4,006 / 3,595 |

My three predictions from before the report: the clock-cluster bin stays (3,828: held), the e6 outline falls below 2,000 (held),
the (340, 950) junction was only flagged to watch, and it is the new worst bin (4,041 at x 300, y 900).
Middle column history: k6 +21,000, k7 15,490, k9 11,100 (R), k11 7,911 (M). Four kits, same channel.
What the plan puts in that gap between y 880 and 1230 (M): the reset local tap at (336.96, 1105.92), 5 um from r1; taps
clk_t17, t21, t24, t33; reserved die_clock_tree strips, all M1-M7, one 43 um wide at y 1187.5 (x 302.6-345.5) and one 98 um
long at y 977 (x 213.8-311.5); and the ft2 station, 1,056 bits, at (354.9, 941.1), 17 um from q. The k11 overflow peaks at
y 1175-1200 (2,259, the 43-um strip) and y 925-950 (2,960: q, hst2_g, hst3_g and ft2 in one bin). 3,197 of the 7,601
vertical overflow there is on capacity-0 gcells outside any core.

### Root cause, restated after k11

hgi_v1 has no corridor for a 1,560-bit trunk from the north-west landing core to the two head columns that avoids all of:
a hard core (e6), the 16.4-um gap, and the clock / reset entry structure. Every vertical channel carries that structure at some
y, and its reserved rects block M1 to M7 although a clock route uses one or two layers. The rows so far moved the trunk from
one of these to the next.

### Ranked fixes

| rank | fix | measured evidence | owner |
|---|---|---|---|
| 1 | Keep the M2 tN route (it removes the hop over e6) and re-site its stations: no station of 1,000 bits or more within 40 um of a tap, a reset local tap, a reserved strip or another such station. P, as a starting point: r1 off the reset tap and east of the 43-um strip, q near (330, 1020), hst2_g and hst3_g polylines starting about 90 um west and east of the column, away from the ft2 station | k11: 2,960 at y 925-950 and 2,259 at y 1175-1200 | FABLE-FIX-KV-HG |
| 2 | Reserved die_clock_tree rects carry only the layers the clock route uses, not M1-M7 (P). Class-wide: it applies to every KV type with interior taps | capacity-0 overflow outside cores: k10 2,315 in the head2 / head3 channel, k11 3,197 in the middle column | DIE-CORETAP-1119 (clock tool), gen_phys owner |
| 3 | Take the hst3 leg off the clock entry cluster at (639, 760), or apply rank 2 there first and re-read the bin | k10 3,431, k11 3,828 | FABLE-FIX-KV-HG |
| 4 | If ranks 1 to 3 leave more than a few thousand: a floorplan move, P: shift the head2 west column (e0, e2, e4, e6) east by 43.2 um. The landing-to-e6 gap becomes 59.6 um (about 2,600 tracks), tN and hst2 run down the west margin, and the middle column (95 -> 52 um) carries no trunk. Cores move, no re-shape | gap capacity (M); the move itself is unproven | FABLE-FIX-KV-HG, KV-D23-COMPOSE |
| 5 | Read overflow on capacity-0 gcells, not the total, as the kit's routing number. Capacity-0 overflow cannot be detail-routed; overflow on real capacity often can. Take a kit to DRT once the capacity-0 share is gone | k10 13,051 of 21,073; k11 10,174 of 19,249 | FABLE-FIX-KV-HG |
| 6 | Timing: no further lever. k10 -187.4 and k11 -198.6 are the 4 to 5 NORAWB FSTART ends (R); station paths >= +289 in k10 (R). Kit hold: cross_tap 510 / 463 ends closed with 717 / 662 cells (M). The proof is the first kv3_hgi_v1 kit on the D25e bind at post-CTS | private kits are on the d25d4 bind | FABLE-FIX-KV-HG |
| 7 | PRECHECK estimator: hop, polyline and station sites against hard cores, reserved clock sites, taps and other stations, with the around-core length | causes 1 and 2 passed a Manhattan check | PRECHECK-1119 |

## C. Die hold after the clock fix: the structural form

Sources (M): epyc10 `/srv/opentallas-scratch2/claude/die-coretap-1119/runs/qwen_kvsys/c1119_v3_pvsnake/proof/tap_arrivals_FF.json`
(12,419 taps, tree paths, CPPR ranges), the same file of `c1119_lb_am300`, `sta_droop.log`, and epyc8
`/srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/diaghold_v8b/hold_rows.tsv` (47,549 cross-tap ends with launch and capture tap).
"Damage" below = capture late - launch early - CPPR range at the last common node, FF, regular taps only (core taps carry
planned offsets). It is a clock-only number for comparing pair sets. It is not the tool's slack.

### Root cause

1. **The number is taken over all tap pairs of a partition.** `sta_droop.log`: intra pairs 1,529,668, seam 43,792. The 47,549
   failing cross-tap ends of the v8b kit sit on 1,577 directed tap pairs out of 343 taps.
2. **Most of the damage is derate on unshared depth, not imbalance.** A tap arrives at about 5,598 late / 4,847 early (hg_EN_0
   clk_t20, 156 stages, 13.4 % apart), so about 6 ps per unshared stage (I). pv, the 251,463 regular pairs more than 405 um
   apart (85 % of 295,243): nominal skew p95 62, max 133; damage p95 150, max 218.

   | pv pairs by unshared stages | pairs | nominal skew p50 / p95 / max |
   |---|---|---|
   | <= 4 | 9,879 | 5 / 19 / 35 |
   | 5-8 | 29,550 | 11 / 34 / 67 |
   | 9-12 | 50,598 | 16 / 47 / 107 |
   | > 12 | 205,216 | 21 / 66 / 133 |

3. **Leaf balancing does not reach it.** am300 against v3_pvsnake, pv pairs within 405 um: damage p95 125 vs 134, max 212 vs 194;
   hg 106 / 175 vs 109 / 195; hgi 109 / 182 vs 114 / 168. Neighbour taps (<= 150 um) in pv still have p95 18 unshared stages:
   a planar tree always splits some neighbours at a high node.
4. **On the pairs that carry real hops the tree is close.** pv_N_0 (type kv3_pv_v8), 466 regular tap pairs matched by name from
   the v8b list, v3_pvsnake tree:

   | pair set | pairs | damage p50 / p95 / max | over 75 ps | over 100 ps |
   |---|---|---|---|---|
   | connected (v8b), v3_pvsnake | 466 | 11 / 48 / 115 | 4 pairs, 110 ends | 1 pair, 22 ends |
   | connected (v8b), pcsink_fix | 466 | 1 / 105 / 150 | 66 pairs, 889 ends | 28 pairs, 381 ends |
   | all directed regular pairs, v3_pvsnake | 61,256 | 59 / 120 / 160 | - | - |

   The connected pairs are neighbours (distance p50 43 um, p95 190 um). The pairs over the window are the ones with more than
   8 unshared stages (34 pairs at 9-12: p95 76; 3 pairs above 12: 115). The pv DME did its work on real pairs: 66 -> 4.
   Limits: one partition; names matched across plan versions (127 of 343 kit names are missing in the D25c tree; the 43-um
   median distance says the matched ones are the same taps); the list holds only ends that fail at the kit window; core-tap
   pairs are left out.
5. hg / hgi cross-tap hold is small in the kit: k10 510 ends at -43.7, k11 463 at -64.9, closed with 717 / 662 hold cells (M).
   Both logs say "cross-tap guard not applied (no tap window lines in the kit SDC)".
6. Seam -122.3 / -123.9 is the same construction on 43,792 pairs. The real plain-seam ends are the kit port_in class: hgi_v1
   166 ends at -107.2 (k11), pv_v8 4,448 at -98.2 (R), against a contract in_min of -75.

### Ranked form

| rank | form | measured evidence | owner |
|---|---|---|---|
| 1 | Time related pairs only: the kit exports its tap-pair list (launch tap, capture tap, min data delay, lockup yes / no) at CTS; `die_sta_related` reads it and keeps all-pairs as INFO. Same change as "pair core views only on connected pins" from the hub_Wi -95 trace | 466 connected pairs: max 115, 4 over the window, against 160 on all pairs | DIE-LEVEL-CHECK-1119 (tool), kit side with FABLE-FIX-KV-PV-2140 |
| 2 | pv: form C. Every tap-group boundary of a delay line is a lockup hop, so those pairs have T / 2 of hold by construction | 90 % of 47,549 ends are stage k -> k+1 (R); buffers are not affordable at 539k cells | FABLE-FIX-KV-PV-2140 |
| 3 | hg, hgi, pc: per-pair kit window from the die tree for the cross-tap pairs, closed by the pre-GRT hold build | about 500 ends per hgi_v1 kit, 700 cells at the 71.2 ps window | KV-CROSSING-1119 (window rows), FABLE-FIX-KV-HG |
| 4 | Tree: for the related pairs left with more than 8 unshared stages, merge related taps first (tap-pair weights into the DME order, the cw8 cluster form). Target <= 5 unshared stages: nominal p95 19 + about 30 of derate, inside the 71-75 ps window | pv_N_0: <= 4 stages max 40; 5-8 max 60 | DIE-CORETAP-1119 |
| 5 | pc core -> core (pcc -> pcf, -99.6 to -145.7 kit-contract, R): one composite sink per pcc / pcf pair, the 94 ps offset built as a fixed plan-computed stub at the shared tap | pair gap 85..125 delivered against 94 signed (R) | DIE-CORETAP-1119, patch from S81-CLOCK-WINDOW-1119 |
| 6 | Seam: per-port views for the port_in ends; plain seam bits that stay take the lockup form used on kv3_io_ft_v1 | port_in counts above | DIE-LEVEL-CHECK-1119, KV-CROSSING-1119 |

Not recommended: a regional mesh (no measured need once 1 to 3 are in), DME on hg / hgi (R: -251 / -234), further snake or
`actual_max` rounds.

## D. kv3_pc and kv3_hub_Wi failure classes

### kv3_pc (6 types, 32 partitions)

| rank | class | root cause, measured | fix | owner |
|---|---|---|---|---|
| 1 | PDN-0006 at floorplan | epyc10 `/srv/opentallas-scratch2/claude/kv-pc-hgi-1119-pilot/kit/kv3_pc_v1__cl4ea58a5c/gen/kv3_pc_v1__cl4ea58a5c/run_grt.log` line 2349: "VSS on M5 is blocked by obstructions on M6, M7 for u_bound.u_kvpc0" (21:42Z, no post). The kit PDN (PG-CORECONN-1) lays tile M6 straps over macros with M5 PG pins. `kv_pcsplit_views_1119/qkd_kvs_pcc.lef`: VDD / VSS are 66 M5 stripes each; the core's own routing covers 17.1 % of M6 and 30.0 % of M7; it has no M6 / M7 PG stripe. kv3_pv_pair, which passes: M6 1.5 %, M7 1.2 %. D25e and D25f point every pc type at these LEFs (22 pcc, 22 pcf and 4 h_head_p hard-core rows). The same error text is on the pc rows of events kv102sem_ftgrid and kvN2 | (a) re-harden pcc, pcf and the two h_head_p variants with their own M6 / M7 PG stripes on the tile pitch, exported as PG pins (a core that routes to M7 must carry PG to M7); (b) interim, only if pdngen accepts it: M6 straps cut at the core's M6 shapes, then check IR on the 259-um M5 stripes. Not tried | KV-PC-HGI-1119 |
| 2 | LEC baseline NOT EQUIVALENT, 134 points (R, KIT-SYNTH-TARGET 20:49) | merged-replica `es` flops, not a netlist error | OT_KEEP_WIRES proof running, about 4.7 h | KIT-SYNTH-TARGET-1119 |
| 3 | die hold pc core -> core | section C rank 5 | composite sink | DIE-CORETAP-1119 |
| 4 | core-tap pairing 318 / 196 against the v3 tree | section A2 | same event | KV-D23-COMPOSE |
| - | zero-wire WNS -403 (R) | reset relay fan-out 325 before buffering | none | - |

No pc kit has passed floorplan on the macro views, so nothing is known about pc placement, CTS or routing with them.

### kv3_hub_Wi

| rank | class | root cause, measured | fix | owner |
|---|---|---|---|---|
| 1 | ORD-2013 at place (D25d attempt 10, D25e 22:19) | undeclared `ot_sram_1r1w_64x512_m1_r2c2` (R) | D25f HUBWI row; site checked in A4 | KV-D23-COMPOSE |
| 2 | core-tap insertion not measured | plan: `core_taps` = "internal"; 18 of 21 core taps carry the declared 250.0 with no FF value; the 3 measured ones are 273.7, 253.6 and 406.0 (qkd_hr_core_prompt, 156 ps over the target, not early-tapped) | fill the 18 from the core records; early-tap or restructure core_prompt | DIE-CORETAP-1119 |
| 3 | TT intra setup -95.28 | not a path: unconnected core pins (R, DIE-LEVEL 20:23) | section C rank 1 | DIE-LEVEL-CHECK-1119 |

hub_Wi has never passed place in the wave, so later classes are unknown.

## Stop list

- Quoting -165 / -156 or -122 as KV die hold, or sizing kit windows from all-pairs port needs (`kitwin.json`).
- More tree rounds for hold: snake on more regions, `actual_max`, DME on hg / hgi, leaf balancing.
- Launching or retrying kv3_pc kits on the E2 macro views before the PG form is fixed.
- Binding K or depth rows without a `kv_regen` dry run; folding F1 / F2 generic rows onto the hub_C sidecar.
- Citing CA or hold from a D25c-plan tree for D25e2 / D25f.
- The v3 clock config without the core-tap v2 rows, or the reverse.
- Checking a hop or a polyline by Manhattan length only; any trunk polyline through x 607-697, y 692-791 of an hgi type.
- Calling the k10 hot spot a 16-um gap squeeze, or judging hg kits by total GRT overflow.
- Posting M2 as rows in its k11 form; siting a trunk station on a tap, a reset local tap or next to the ft2 station; a fifth kit
  with a 1,560-bit trunk in the middle column gap as it is reserved today.
- Porting the rls rows to the 7 hg_v1-family types as proven: hgi_v1 has no krsp core in its west margin.
- Hold buffers on pv cross-tap ends; form C on core-launched ends.
- Retrying kv3_hub_Wi on D25e (ORD-2013 is a plan class).

## Not checked

- k11 past GRT round 5. v8h / v8j (form C) at any stage. The D25e3 bind.
- Any hg-family (non-hgi_v1) GRT. Where the `u_hst0` trunk source sits on hg types, and the pin faces of the head eighth cores.
- Which net groups make up the overflow over e6 and in the middle column (the reports have anonymous net names; it needs the
  ODB). How the kit turns a reserved rect into blockage, layer by layer (`reserved_sites.tcl` not opened).
- Connected-pair damage on hg, hgi, pc and on the other 15 pv partitions; core-tap pairs.
- Whether pdngen can cut M6 straps over the pc cores; whether kv3_phy_v1 is signed; the real insertion of the 18 hub_Wi cores.
- The ECTL fix rows on the v3 tree (margins taken from the 22:50 post).
