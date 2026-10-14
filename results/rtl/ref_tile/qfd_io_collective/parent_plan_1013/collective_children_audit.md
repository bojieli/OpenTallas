# Pin-register audit: qwen_collective_children (contract vNone, 6bea60422)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 3: audited 3 (3 instances); VIOLATING 2 {'out_unreg': 2, 'in_unreg': 2, 'spread': 1, 'abut': 1}; reach-limited only 1; clean 1; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 200.4 (ot_coll_fold_slice) .. 311.2 (ot_coll_tp8_col_tile) ps at TT = 110.8 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 311.2 ps a side = 31.1 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.815..0.832 = 1.9 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 786.6 ps (ot_coll_tp8_col_tile -> ot_coll_tp8_col_tile, wire left -103.3); COMMON-phase entry 786.6 ps (ot_coll_tp8_col_tile -> ot_coll_tp8_col_tile, wire left -103.3). Hold (need 100): compensated 91.2 ps (ot_coll_tp8_col_tile -> ot_coll_col_tile); common phase 39.2 ps (ot_coll_fold_slice -> ot_coll_tp8_col_tile).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| ot_coll_tp8_col_tile | 1 | tt | 311.2 (ins.json) | -311.2 | 0.0 | 101.9 | 333.1 (lq_hd) | 453.5 (c_pop) | 786.6 | -135.9 | 276.4 | 408.3 | 109.9 | out_unreg in_unreg spread abut | - |
| ot_coll_col_tile | 1 | tt | 205.3 (ins.json) | -205.3 | 105.9 | 79.9 | 280.8 (tx) | 221.1 (c_l1) | 501.9 | 238.7 | 226.1 | 195.9 | 127.9 | out_unreg in_unreg | reach_limited |
| ot_coll_fold_slice | 1 | tt | 200.4 (ins.json) | -200.4 | 110.8 | 24.7 | 152.9 (v_out) | 116.6 (src) | 269.5 | 544.5 | 146.2 | 98.6 | 116.2 | - | - |

## Violating tiles and the fix each needs

1. **ot_coll_tp8_col_tile** x1 [out_unreg in_unreg spread abut] (contract kit coll_tp8_col_cx): output pin register missing or far: 40 bits (lq_hd, hv, rq_hd, eq_hd), worst lq_hd leaves 276 ps after the latest boundary clock = 96 ps over a pin flop (logic, or ~127 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 289 bits (c_pop, c_push, c_hold, lq_wd), worst c_pop needs 408 ps before the earliest boundary clock = 258 ps over a pin flop: first flop ~340 um (or logic) behind the pin: register at the pin; boundary clock spread 102 ps > 80: put the boundary registers on one balanced sub-root (or split the root); every ps is inside o + s (1.3 um of reach per ps)
2. **ot_coll_col_tile** x1 [out_unreg in_unreg] (contract kit coll_col_tile_rt): output pin register missing or far: 1 bits (tx), worst tx leaves 226 ps after the latest boundary clock = 46 ps over a pin flop (logic, or ~61 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (c_l1), worst c_l1 needs 196 ps before the earliest boundary clock = 46 ps over a pin flop: first flop ~60 um (or logic) behind the pin: register at the pin

Export-SDC: 3 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
