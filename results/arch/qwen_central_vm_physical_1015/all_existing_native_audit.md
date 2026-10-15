# Pin-register audit: None (contract vNone, bf3f09ac5)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 8: audited 8 (8 instances); VIOLATING 2 {'out_unreg': 2, 'in_unreg': 2, 'spread': 2}; reach-limited only 5; clean 3; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 47.6 (qfd_vm_qcommit) .. 371.2 (ot_qfd_vm_su_t) ps at TT = 323.6 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 371.2 ps a side = 37.1 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.757..0.837 = 25.8 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 635.1 ps (ot_qfd_vm_bank_t -> ot_qfd_vm_bank_t, wire left 48.2); COMMON-phase entry 767.3 ps (ot_qfd_vm_bank_t -> ot_qfd_vm_sctl_t, wire left -84.0). Hold (need 100): compensated 118.7 ps (ot_qfd_vm_su_t -> ot_qfd_vm_su1024_t); common phase -117.4 ps (qfd_vm_qcommit -> ot_qfd_vm_su_t).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| ot_qfd_vm_bank_t | 1 | tt | 319.3 (ins.json) | -319.3 | 51.9 | 137.0 | 351.0 (q) | 284.1 (wd) | 635.1 | 63.5 | 239.4 | 258.7 | 162.0 | out_unreg in_unreg spread | reach_limited |
| ot_qfd_vm_su_t | 1 | tt | 371.2 (ins.json) | -371.2 | 0.0 | 95.9 | 293.5 (q) | 260.9 (swd) | 554.4 | 169.6 | 231.5 | 227.0 | 127.5 | out_unreg in_unreg spread | reach_limited |
| ot_qfd_vm_rr4_t | 1 | tt | 121.9 (ins.json) | -121.9 | 249.3 | 16.6 | 217.4 (t1) | 184.7 (bx) | 402.1 | 370.0 | 209.6 | 175.9 | 177.5 | - | reach_limited |
| ot_qfd_vm_rr2_nx | 1 | tt | 109.9 (ins.json) | -109.9 | 261.3 | 13.6 | 186.3 (ro) | 179.1 (t1a) | 365.4 | 418.3 | 180.6 | 171.2 | 165.3 | - | reach_limited |
| ot_qfd_vm_sctl_t | 1 | tt | 51.9 (ins.json) | -51.9 | 319.3 | 2.0 | 203.4 (svc) | 148.9 (swl) | 352.3 | 435.6 | 202.3 | 148.0 | 182.1 | - | reach_limited |
| qfd_vm_qcommit | 1 | tt | 47.6 (ins.json) | -47.6 | 323.6 | 1.2 | 175.3 (cm) | 116.2 (rst_n) | 291.5 | 515.6 | 174.8 | 115.5 | 167.1 | - | - |
| ot_qfd_vm_su1024_t | 1 | tt | 104.6 (ins.json) | -104.6 | 266.6 | 16.4 | 151.7 (so) | 135.0 (rtg) | 286.7 | 521.9 | 143.8 | 126.5 | 123.3 | - | - |
| ot_qfd_vm_bctl_nx | 1 | tt | 53.9 (ins.json) | -53.9 | 317.3 | 1.8 | 174.7 (m_wm) | 108.5 (wm) | 283.2 | 526.5 | 173.6 | 107.8 | 170.0 | - | - |

## Violating tiles and the fix each needs

1. **ot_qfd_vm_bank_t** x1 [out_unreg in_unreg spread] (explicit): output pin register missing or far: 4 bits (q), worst q leaves 239 ps after the latest boundary clock = 59 ps over a pin flop (logic, or ~78 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 59 bits (wd, wm), worst wd needs 259 ps before the earliest boundary clock = 109 ps over a pin flop: first flop ~143 um (or logic) behind the pin: register at the pin; boundary clock spread 137 ps > 80: put the boundary registers on one balanced sub-root (or split the root); every ps is inside o + s (1.3 um of reach per ps)
2. **ot_qfd_vm_su_t** x1 [out_unreg in_unreg spread] (explicit): output pin register missing or far: 8 bits (q), worst q leaves 232 ps after the latest boundary clock = 52 ps over a pin flop (logic, or ~68 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 8 bits (swd), worst swd needs 227 ps before the earliest boundary clock = 77 ps over a pin flop: first flop ~101 um (or logic) behind the pin: register at the pin; boundary clock spread 96 ps > 80: put the boundary registers on one balanced sub-root (or split the root); every ps is inside o + s (1.3 um of reach per ps)

Export-SDC: 8 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
