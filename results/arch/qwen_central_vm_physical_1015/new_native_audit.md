# Pin-register audit: None (contract vNone, 9e48dd5ff)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 3: audited 3 (3 instances); VIOLATING 0 {}; reach-limited only 1; clean 2; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 54.8 (qvm_bank_ctrl_native) .. 69.3 (qvm_data256_native) ps at TT = 14.5 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 69.3 ps a side = 6.9 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.748..0.789 = 0.6 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 321.6 ps (qvm_data256_native -> qvm_data256_native, wire left 361.7); COMMON-phase entry 325.2 ps (qvm_data256_native -> qvm_bank_ctrl_native, wire left 358.1). Hold (need 100): compensated 165.9 ps (qvm_su_bank_ctrl_native -> qvm_data256_native); common phase 152.3 ps (qvm_bank_ctrl_native -> qvm_data256_native).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| qvm_data256_native | 1 | tt | 69.3 (ins.json) | -69.3 | 0.0 | 4.7 | 201.6 (q) | 120.0 (d) | 321.6 | 476.0 | 199.0 | 117.9 | 167.5 | - | reach_limited |
| qvm_bank_ctrl_native | 1 | tt | 54.8 (ins.json) | -54.8 | 14.5 | 0.9 | 173.3 (p_ra) | 109.1 (rst_n) | 282.4 | 527.5 | 172.9 | 108.6 | 169.2 | - | - |
| qvm_su_bank_ctrl_native | 1 | tt | 54.9 (ins.json) | -54.9 | 14.4 | 1.0 | 172.5 (p_wm) | 108.5 (rst_n) | 281.0 | 529.4 | 172.1 | 107.9 | 168.5 | - | - |

## Violating tiles and the fix each needs


Export-SDC: 3 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
