# INTENT SHEET: COL-H9R2 (S81, 5 types: col_h9_r2__t1__cl{774acf45,87f3ff59,b8d86cd5,c9ad8f7e,ce45cab5})
Lane VIS-TRIAGE-S81. Base plan 99f40d35071d (v5 grow); the 39eae55ea90a positions are identical.

## 1. Dataflow chain
The connectivity is measured from the kw27 cl87f 3_place ODB: direct macro nets, 2- to 10-hop flows through glue logic, and IO BFS. The sidecar core_conns.json lists only resets for the payload stations.

    S face frame_int_i0 [6,260] (1167 b in)
      -> t6 (sstn_base566: xai/xbi 549 b)  + t6__payload (sstn_payload536: i 536 b)      p2p, pipelined face flops (16-24 cells)
      -> t7 / t7__payload   (t6->t7 974 b, t6p->t7p 1024 b)                                p2p pipeline stage
      -> t8 / t8__payload   (t7->t8 1053 b, t7p->t8p 1048 b)                               p2p pipeline stage
      -> e13 (bf_front_roots: x0/x1 2134 b from t8, xb_data 1028 b from t8p)            p2p
      -> e13w.c / e13e.c (754 b each, c0/c1)  -> ha/hb halves (288 b each)               p2p fan-out
    side links: bs10<->t6 1098, bs10<->t7 1098, bs11<->t7 704, bs12<->t7/t8 ~1090, bs14<->t7/t8 ~1100 (p2p)
                bs1x <-> e1x.u_w/u_e 588-1120 (bank-select broadcast to both halves of each rom_elem pair)
                s1x <-> c1x_* 48-170 (cfg/st serialisable), n23..n28 node tree 66-111 (frame_int_o0 <- n23 66, bn10 51, bn11 25, s11 17)
    reset: frame_int_i0 rs -> one relay station (4 regs) to bn10/bn11/bn12.rs (1 bit, broadcast)
    S face frame_int_o0 [261,329] 321 b out (n23, bn10, bn11, s11)

## 2. Timing-critical pairs
- The plan station frame_int_i0 relay (4 FIRM regs, 1720 um) is held: its capture cores bn10/bn11/bn12 and its end core n28 are fixed.
- The payload chain t6p -> t7p -> t8p: in the base the t6p hop runs 1000 um along the S edge to x 1123, and t7p sits at x 1123 too (t7p -> t8p = 864 um).
- The kw27 stock GRT (cl87f attempt_2) reports 66,467 overflow, all of it H (M6 48,672 / M4 10,900). It sits in the bottom street at x 1090-1115 under e11.u_e, around n23 / t6p / bs11. That spot is the payload bus running from the S window (x 6-260) east to t6__payload at (1123, 43), then north to t7__payload.

## 3. Hand layout (intent.svg)
- t6__payload moves next to the chain start, between e10 and the c12 row at (406.08, 362.88). This drops the 536-b run along the S edge past c10/c11/n23.
- t7__payload sits directly above it, beside t7, at (397.44, 432.0): t6p -> t7p becomes a 70-um p2p hop.
- t8p, t8 and e13 are unchanged (already adjacent to e13).
- I tried moving bs11 under the e11 junction. It was dropped: the e11.u_e -> bs11 links would exceed 405 um, and the street (40 um) cannot hold bs11's pin channel.

## 4. Search
core_place.py with --seed, with these cores fixed: t6__payload, t7__payload, t6, t7, t8, bn10-14 and n28 (the hand structure and the station ends). The search only legalises and fine-tunes the other cores (c rows, bs, s, n nodes).

## 5. Rationale
The S-window payload stage was placed at the far E corner, so 536 b crossed the whole bottom street twice (S->E, then up the E edge). That is the GRT hot spot of every H9R2 attempt. With the payload stations next to their base stations, the chain runs S-window -> t6/t6p -> t7/t7p -> t8/t8p -> e13 up the W half, and the E corner keeps only the node tree.

## 6. Explorer (before/after, --delta --supply): physical/die_plan/s81/cleanslate_1111/vis_triage_s81/ (+ scratchpad PNGs) explorer/
- Over-reach: 12 links / 5843 b both before and after, 0 new. The frame_int_i0>e1x 604-b links and bs11>e11.u_w 1421 b at 463 um are POR, unchanged, and accepted as before.
- street_H p99 1.084 -> 1.093 (slightly worse), unrelated-block crossings 57 -> 60. This agrees with the KEEP verdict.
