# Pin-register audit: ds_rom_s81_layer1 (contract vNone, bc3c8a271)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 1: audited 1 (1 instances); VIOLATING 1 {'out_unreg': 1}; reach-limited only 1; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 186.3 (dsfd_capt_x8_dual) .. 186.3 (dsfd_capt_x8_dual) ps at TT = 0.0 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 186.3 ps a side = 18.6 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.822..0.822 = 0.0 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 436.8 ps (dsfd_capt_x8_dual -> dsfd_capt_x8_dual, wire left 246.5); COMMON-phase entry 436.8 ps (dsfd_capt_x8_dual -> dsfd_capt_x8_dual, wire left 246.5). Hold (need 100): compensated 196.1 ps (dsfd_capt_x8_dual -> dsfd_capt_x8_dual); common phase 196.1 ps (dsfd_capt_x8_dual -> dsfd_capt_x8_dual).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| dsfd_capt_x8_dual | 1 | tt | 186.3 (ins.json) | -186.3 | 0.0 | 23.5 | 278.6 (t_st) | 158.2 (f_w) | 436.8 | 324.4 | 269.7 | 151.7 | 196.1 | out_unreg | reach_limited |

## Violating tiles and the fix each needs

1. **dsfd_capt_x8_dual** x1 [out_unreg] (explicit): output pin register missing or far: 60 bits (t_st), worst t_st leaves 270 ps after the latest boundary clock = 90 ps over a pin flop (logic, or ~118 um of wire, after the flop): add / move the output register to the pin

Export-SDC: 1 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
