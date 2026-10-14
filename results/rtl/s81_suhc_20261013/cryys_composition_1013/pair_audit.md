# Pin-register audit: ds_rom_s81_layer1 (contract v16, 0e7b856f4)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 3: audited 3 (4 instances); VIOLATING 2 {'out_unreg': 2, 'in_unreg': 2, 'abut': 2}; reach-limited only 1; clean 0; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 256.4 (ot_s81_hc_cryys) .. 300.8 (ot_s81_hc_crootr_f) ps at TT = 44.4 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 300.8 ps a side = 30.1 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.809..0.832 = 1.0 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 926.2 ps (ot_s81_hc_crootr_f -> ot_s81_hc_crootr_f, wire left -242.9); COMMON-phase entry 935.2 ps (ot_s81_hc_crootr_f -> ot_s81_hc_cpin, wire left -251.9). Hold (need 100): compensated 94.3 ps (ot_s81_hc_crootr_f -> ot_s81_hc_cpin); common phase 119.2 ps (ot_s81_hc_cryys -> ot_s81_hc_cpin).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| ot_s81_hc_crootr_f | 2 | tt | 300.8 (ins.json) | -300.8 | 0.0 | 71.2 | 429.2 (ch_fd) | 497.0 (p_y) | 926.2 | -319.6 | 371.7 | 483.3 | 129.2 | out_unreg in_unreg abut | - |
| ot_s81_hc_cpin | 1 | tt | 264.4 (ins.json) | -264.4 | 36.4 | 45.3 | 427.9 (yacc_w) | 469.6 (y_s) | 897.5 | -281.8 | 399.5 | 452.7 | 167.6 | out_unreg in_unreg abut | - |
| ot_s81_hc_cryys | 1 | tt | 256.4 (ins.json) | -256.4 | 44.4 | 14.2 | 197.3 (p_y) | 165.6 (y_s) | 362.9 | 421.6 | 191.2 | 157.5 | 188.2 | - | reach_limited |

## Violating tiles and the fix each needs

1. **ot_s81_hc_crootr_f** x2 [out_unreg in_unreg abut] (explicit): output pin register missing or far: 833 bits (ch_fd, p_req, ch_rst, ch_fv), worst ch_fd leaves 372 ps after the latest boundary clock = 192 ps over a pin flop (logic, or ~252 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 2817 bits (p_y, srs), worst p_y needs 483 ps before the earliest boundary clock = 333 ps over a pin flop: first flop ~439 um (or logic) behind the pin: register at the pin
2. **ot_s81_hc_cpin** x1 [out_unreg in_unreg abut] (explicit): output pin register missing or far: 3650 bits (yacc_w, yacc_e, n_cmd_v, n_cmd_d), worst yacc_w leaves 400 ps after the latest boundary clock = 220 ps over a pin flop (logic, or ~289 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1450 bits (y_s, y_v, rs_d, n_done_v), worst y_s needs 453 ps before the earliest boundary clock = 303 ps over a pin flop: first flop ~398 um (or logic) behind the pin: register at the pin

Export-SDC: 3 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
