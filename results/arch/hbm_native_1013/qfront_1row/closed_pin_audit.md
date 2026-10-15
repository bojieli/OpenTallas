# Pin-register audit: None (contract vNone, 0dc36888a)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 3: audited 3 (3 instances); VIOLATING 2 {'out_unreg': 2, 'in_unreg': 1, 'abut': 1}; reach-limited only 2; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 139.1 (ot_hgi_qdq_fr) .. 279.8 (ot_hgi_qdq_fr_retire) ps at TT = 140.7 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 279.8 ps a side = 28.0 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.786..0.806 = 2.8 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 721.6 ps (ot_hgi_qdq_fr_one_s2 -> ot_hgi_qdq_fr_retire, wire left -38.3); COMMON-phase entry 712.1 ps (ot_hgi_qdq_fr_retire -> ot_hgi_qdq_fr_retire, wire left -28.8). Hold (need 100): compensated 174.2 ps (ot_hgi_qdq_fr_retire -> ot_hgi_qdq_fr_retire); common phase 65.5 ps (ot_hgi_qdq_fr -> ot_hgi_qdq_fr_retire).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| ot_hgi_qdq_fr_retire | 1 | tt | 279.8 (ins.json) | -279.8 | 0.0 | 31.6 | 229.0 (s3) | 483.1 (fast_v) | 712.1 | -37.9 | 220.2 | 460.3 | 174.2 | out_unreg in_unreg abut | - |
| ot_hgi_qdq_fr_one_s2 | 1 | tt | 204.0 (ins.json) | -204.0 | 75.8 | 29.3 | 238.5 (s2) | 178.4 (rec) | 416.9 | 350.6 | 232.5 | 155.1 | 201.3 | out_unreg | reach_limited |
| ot_hgi_qdq_fr | 1 | tt | 139.1 (ins.json) | -139.1 | 140.7 | 20.0 | 226.9 (s3) | 165.1 (rec) | 392.0 | 383.3 | 217.6 | 154.4 | 192.9 | - | reach_limited |

## Violating tiles and the fix each needs

1. **ot_hgi_qdq_fr_retire** x1 [out_unreg in_unreg abut] (explicit): output pin register missing or far: 1 bits (s3), worst s3 leaves 220 ps after the latest boundary clock = 40 ps over a pin flop (logic, or ~53 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 437 bits (fast_v, fast_one, general_v, fast_s2), worst fast_v needs 460 ps before the earliest boundary clock = 310 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
2. **ot_hgi_qdq_fr_one_s2** x1 [out_unreg] (explicit): output pin register missing or far: 38 bits (s2), worst s2 leaves 232 ps after the latest boundary clock = 52 ps over a pin flop (logic, or ~69 um of wire, after the flop): add / move the output register to the pin

Export-SDC: 3 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
