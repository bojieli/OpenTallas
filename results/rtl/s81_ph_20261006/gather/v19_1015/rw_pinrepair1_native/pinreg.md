# Pin-register audit: ds_rom_s81_layer1 (contract vNone, 0c47ef1c3)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 1: audited 1 (1 instances); VIOLATING 0 {}; reach-limited only 1; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 260.7 (dsfd_gth_rw) .. 260.7 (dsfd_gth_rw) ps at TT = 0.0 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 260.7 ps a side = 26.1 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.822..0.822 = 0.0 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 393.5 ps (dsfd_gth_rw -> dsfd_gth_rw, wire left 289.8); COMMON-phase entry 393.5 ps (dsfd_gth_rw -> dsfd_gth_rw, wire left 289.8). Hold (need 100): compensated 167.7 ps (dsfd_gth_rw -> dsfd_gth_rw); common phase 167.7 ps (dsfd_gth_rw -> dsfd_gth_rw).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| dsfd_gth_rw | 1 | tt | 260.7 (ins.json) | -260.7 | 0.0 | 71.1 | 233.5 (co) | 160.0 (li) | 393.5 | 381.4 | 214.0 | 108.4 | 167.7 | - | reach_limited |

## Violating tiles and the fix each needs


Export-SDC: 1 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
