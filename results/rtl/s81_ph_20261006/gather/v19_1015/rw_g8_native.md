# Pin-register audit: None (contract vNone, 926e6d518)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 1: audited 1 (1 instances); VIOLATING 1 {'out_unreg': 1}; reach-limited only 1; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 259.9 (dsfd_gth_rw) .. 259.9 (dsfd_gth_rw) ps at TT = 0.0 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 259.9 ps a side = 26.0 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.821..0.821 = 0.0 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 399.7 ps (dsfd_gth_rw -> dsfd_gth_rw, wire left 283.6); COMMON-phase entry 399.7 ps (dsfd_gth_rw -> dsfd_gth_rw, wire left 283.6). Hold (need 100): compensated 185.6 ps (dsfd_gth_rw -> dsfd_gth_rw); common phase 185.6 ps (dsfd_gth_rw -> dsfd_gth_rw).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| dsfd_gth_rw | 1 | tt | 259.9 (ins.json) | -259.9 | 0.0 | 43.7 | 241.1 (co) | 158.6 (li) | 399.7 | 373.2 | 221.0 | 135.0 | 185.6 | out_unreg | reach_limited |

## Violating tiles and the fix each needs

1. **dsfd_gth_rw** x1 [out_unreg] (explicit): output pin register missing or far: 1 bits (co), worst co leaves 221 ps after the latest boundary clock = 41 ps over a pin flop (logic, or ~54 um of wire, after the flop): add / move the output register to the pin

Export-SDC: 1 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
