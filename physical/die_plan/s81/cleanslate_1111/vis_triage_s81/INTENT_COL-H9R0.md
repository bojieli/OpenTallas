# INTENT SHEET: COL-H9R0 (S81, 10 types: col_h9_r0_p1..p6, all __t1 classes)
Lane VIS-TRIAGE-S81. Base plan 99f40d35071d (v5 grow); 39eae55ea90a carries the same R0 positions.

## 1. Dataflow chain
Measured on the kw43 cl9f71 (p2) attempt_18 3_place ODB: direct macro nets, multi-hop flows through glue, and IO BFS.

    E face xo_i0 (y 740-980, 1104 b in)
      -> cf (xl0..xl3, S face of cf, 1104 b)                                         p2p pipelined face
      -> cf N face: x2 536 / xa 283 / xb 266 -> t0 + t0__payload                    p2p
      -> t1 / t1__payload (1049 / 1067 b)                                            p2p pipeline stage
      -> t2 / t2__payload (1046 b)                                                   p2p pipeline stage
      -> e4 (x0/x1 1000 b from t2, xb_data 1026 b from t2p)                          p2p
      -> e4w.c / e4e.c (754 b each) -> ha/hb halves                                  p2p fan-out
    cf -> W face xo_o0 (1104 b, pass-through, 14-22 hops)
    t2 540 + t2p 335 + e4 210 -> N face frame_int_o0 [6,260] (29-37 hops)
    N face frame_int_i0 -> n11 / n10 / rg1 (node tree)
    side links: bs_k <-> e_k.u_w/u_e 588-1120 (bank-select broadcast), bs <-> t1/t2 ~1100
    ft0 feedthrough 1104 b E->W at y 981-1221 (p1/p2/p3): 5 station bit-site columns (fixed points)

## 2. Timing-critical pairs
- ret_o0 plan station and the ft0 bit-site columns: fixed points, untouched.
- t2 <-> e4 and t2 <-> bs2/N face are already at the 405-um direct-link limit in the base; e4 and t2 are kept in place.
- e* -> cf links (bank results back to cf) are near the limit; cf stays in place.

## 3. Hand layout (intent.svg)
- The e4w group (ha, hb, c) moves W by 17.28 um. This opens the e4w.c | e4 slot from ~25 um to ~42 um. That slot carries the S4 station's 667 regs and the 754-b e4->e4w.c link; it was the N-strip jam together with the ft0 columns.
- t0__payload moves under cf at (1123.2, 475.2) and t1__payload to (1075.68, 522.72): the payload stage now follows cf -> t0 -> t1 instead of crossing the E street.
- Tried and dropped: cf moved up (it broke the e*->cf and bs1->t0 limits); e4 moved E (it broke t2->e4).

## 4. Search
core_place.py with --seed seed_hand4.json. Fixed: e4w.*, t0__payload, t1__payload, plus all plan fixed points (ft bit sites, taps, halo 4.32). The search only legalises and fine-tunes the c-row, bs, n and s cores.

## 5. Rationale
H9R0 is congested in the N strip because the ft0 1104-b station columns are squeezed into the slivers between the top-row macros, and the e4w.c | e4 slot is too narrow for S4's registers plus the e4 fan-out. The arrangement keeps the chain cf -> t0 -> t1 -> t2 -> e4 -> e4w/e4e, widens the S4 slot by shifting the e4w group W, and pulls the payload stations onto the chain. Search then only legalises the rest. The intrinsic min-cut is 0.20, so no REDESIGN.

## 6. Explorer (before/after, --delta --supply): physical/die_plan/s81/cleanslate_1111/vis_triage_s81/ (+ scratchpad PNGs) explorer/
All 10 types: 0 new over-reach links. The first pass gave bs1>e1.u_e 1421 b at 407 um on cl9f71 and p6; I fixed it by holding the e1 pair at x 578.88/846.72, as in p1.
On cl9f71: route_supply max 2.23 -> 1.64, street_H p99 1.546 -> 1.241, hop>reach 8 -> 6.
Accepted over-reach links. All are POR links, unchanged or shorter:
- cf>e0..e3 cfg 13 b (quasi-static);
- the 2-b status links t0.so>cf.st and s1.st>t0.c1;
- e*.u_w>bn* 64 b;
- the base-limit links cf>t0 564 b at 443.5 um and xo_i0>cf 1104 b at 433.6 um.
On p4 the 8-b cf.lk>e4w.c/e4e.c r_t_a links grow +17/+48 um. That is the price of the e4w shift; they were already ~3x over reach and need a station either way.

## 7. S2 reason (worst cut 0.842, band 0.8-1.0). Where: the V cut along y=604.8 um, which is the bottom edge of the e2/e3 ROM-element row plus cf. Together e2.u_w/u_e, e3.u_w/u_e and cf span x 17-1413 of the 1443-um outline; the only free columns are 553-586 and 1123-1132. 14,635 bits cross against 17,381 usable tracks; the no-macro intrinsic minimum at this height is 4,991 bits on 51,911 tracks. Why the intent layout cannot go lower: the crossing traffic is the chain itself. cf (E face) feeds t0/t1 south of the row, and t2/e4 and the N face sit north of it. The bank-select broadcasts bs2/bs3 -> e2/e3 (588-1120 b each) and the e* -> cf results must cross this row by design. Moving bs2/bs3 or cf above the row breaks the 405-um base-limit links (e*->cf, bs->t1, t2->bs2), already at the limit in the POR. The row's macro widths are fixed and fill 97% of the width, so every cut at this height sees the same blockage. The hand layout lowered it from 0.851 to 0.842 by shortening t0p/t1p, which no longer run along the row. Why GRT should close it: no cut is over 1.0 (cuts_over_1 = 0). The V direction is not the routing problem: RUDY overflow V is 301k against H 5.6M, the stock attempts' overflow is in H streets, and the explorer flag is street_H (p99 1.546 -> 1.241). The same 0.85 V cut is in the stock POR, whose GRT the r0_stock probe is measuring now.
