# Pin-register audit: None (contract vNone, 9ce89db3e)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 3: audited 3 (3 instances); VIOLATING 0 {}; reach-limited only 3; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 139.1 (ot_hgi_qdq_fr) .. 299.2 (ot_hgi_qdq_fr_capture_retire) ps at TT = 160.1 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 299.2 ps a side = 29.9 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.783..0.806 = 3.7 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 403.7 ps (ot_hgi_qdq_fr -> ot_hgi_qdq_fr_capture_retire, wire left 279.6); COMMON-phase entry 538.6 ps (ot_hgi_qdq_fr_capture_retire -> ot_hgi_qdq_fr, wire left 144.7). Hold (need 100): compensated 167.7 ps (ot_hgi_qdq_fr_one_payload_face -> ot_hgi_qdq_fr_capture_retire); common phase 46.1 ps (ot_hgi_qdq_fr -> ot_hgi_qdq_fr_capture_retire).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| ot_hgi_qdq_fr_one_payload_face | 1 | tt | 198.1 (ins.json) | -198.1 | 101.1 | 28.8 | 223.5 (payload) | 171.7 (rec) | 395.2 | 379.1 | 216.5 | 149.9 | 192.9 | - | reach_limited |
| ot_hgi_qdq_fr | 1 | tt | 139.1 (ins.json) | -139.1 | 160.1 | 20.0 | 226.9 (s3) | 165.1 (rec) | 392.0 | 383.3 | 217.6 | 154.4 | 192.9 | - | reach_limited |
| ot_hgi_qdq_fr_capture_retire | 1 | tt | 299.2 (ins.json) | -299.2 | 0.0 | 28.2 | 213.4 (overflow) | 176.8 (fast_payload) | 390.2 | 385.7 | 208.7 | 153.3 | 180.7 | - | reach_limited |

## Violating tiles and the fix each needs


Export-SDC: 3 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
