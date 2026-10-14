# Pin-register audit: None (contract vNone, )

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**views post export-SDC fix**

Cells 18: audited 18 (18 instances); VIOLATING 4 {'out_unreg': 4, 'in_unreg': 1, 'abut': 1, 'spread': 1}; reach-limited only 16; clean 1; reference estimated (no insertion.json) 0; not auditable 0 (0 instances); alias-bound 0.

## Die clock delivery

R spans 86.8 (vm_cp_rwb) .. 305.2 (vm_cp_fe1) ps at TT = 218.4 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 305.2 ps a side = 30.5 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.808..0.843 = 7.6 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 751.5 ps (vm_cp_re -> vm_cp_re, wire left -68.2); COMMON-phase entry 778.7 ps (vm_cp_re -> vm_cp_fe0, wire left -95.4). Hold (need 100): compensated 91.8 ps (vm_cp_slice2 -> vm_cp_rb2); common phase -5.6 ps (vm_cp_rwb -> vm_cp_re).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| vm_cp_re | 1 | tt | 288.7 (ins.json) | -288.7 | 16.5 | 59.0 | 435.7 (ne) | 315.8 (tap) | 751.5 | -89.7 | 391.9 | 300.6 | 128.4 | out_unreg in_unreg abut | - |
| vm_cp_slice2 | 1 | tt | 262.9 (ins.json) | -262.9 | 42.3 | 95.1 | 336.6 (rd) | 168.9 (rst) | 505.5 | 234.0 | 272.4 | 138.0 | 108.4 | out_unreg spread | reach_limited |
| vm_cp_fe0 | 1 | tt | 160.6 (ins.json) | -160.6 | 144.6 | 77.1 | 235.9 (qSE) | 214.9 (f_su_SE) | 450.8 | 306.0 | 194.9 | 178.8 | 184.3 | - | reach_limited |
| vm_cp_fw2 | 1 | tt | 276.5 (ins.json) | -276.5 | 28.7 | 55.1 | 235.9 (xNW) | 200.8 (tap) | 436.7 | 324.5 | 209.3 | 172.3 | 188.5 | - | reach_limited |
| vm_cp_fe1 | 1 | tt | 305.2 (ins.json) | -305.2 | 0.0 | 39.4 | 226.4 (t_su_SE) | 193.5 (tap) | 419.9 | 346.6 | 204.8 | 175.7 | 188.7 | - | reach_limited |
| vm_cp_rwt | 1 | tt | 251.1 (ins.json) | -251.1 | 54.1 | 55.1 | 226.5 (sw) | 192.7 (tap) | 419.2 | 347.5 | 200.6 | 163.5 | 193.1 | - | reach_limited |
| vm_cp_rt2 | 1 | tt | 257.2 (ins.json) | -257.2 | 48.0 | 31.1 | 273.2 (cfg) | 130.3 (wi) | 403.5 | 368.2 | 257.0 | 115.4 | 155.3 | out_unreg | reach_limited |
| vm_cp_slice3 | 1 | tt | 238.5 (ins.json) | -238.5 | 66.7 | 32.6 | 228.0 (rd) | 175.1 (wd) | 403.1 | 368.7 | 209.3 | 161.2 | 188.2 | - | reach_limited |
| vm_cp_rb2 | 1 | tt | 223.6 (ins.json) | -223.6 | 81.6 | 43.7 | 273.9 (rd) | 125.5 (wi) | 399.4 | 373.6 | 244.5 | 111.2 | 151.0 | out_unreg | reach_limited |
| vm_cp_fe2 | 1 | tt | 226.9 (ins.json) | -226.9 | 78.3 | 44.1 | 234.9 (xNE) | 158.6 (ph) | 393.5 | 381.4 | 209.1 | 140.3 | 160.2 | - | reach_limited |
| vm_cp_fw0 | 1 | tt | 246.5 (ins.json) | -246.5 | 58.7 | 52.7 | 238.9 (ph) | 148.3 (f_su_SW) | 387.2 | 389.6 | 209.6 | 124.9 | 161.7 | - | reach_limited |
| vm_cp_fw1 | 1 | tt | 276.0 (ins.json) | -276.0 | 29.2 | 43.0 | 224.9 (t_su_SW) | 140.6 (ph) | 365.5 | 418.2 | 199.6 | 122.9 | 163.5 | - | reach_limited |
| vm_cp_rb | 1 | tt | 215.2 (ins.json) | -215.2 | 90.0 | 26.5 | 227.6 (eo) | 122.4 (wi) | 350.0 | 438.6 | 211.2 | 112.3 | 160.6 | - | reach_limited |
| vm_cp_rwa | 1 | tt | 172.2 (ins.json) | -172.2 | 133.0 | 34.2 | 220.1 (o) | 127.6 (i) | 347.7 | 441.6 | 205.7 | 107.8 | 154.9 | - | reach_limited |
| vm_cp_rt | 1 | tt | 253.0 (ins.json) | -253.0 | 52.2 | 27.1 | 220.6 (eo) | 126.1 (wi) | 346.7 | 442.9 | 209.0 | 110.6 | 159.6 | - | reach_limited |
| vm_cp_fe3 | 1 | tt | 205.0 (ins.json) | -205.0 | 100.2 | 27.3 | 224.8 (ph) | 121.3 (f_su_NE) | 346.1 | 443.7 | 212.0 | 106.8 | 157.9 | - | reach_limited |
| vm_cp_fw3 | 1 | tt | 175.2 (ins.json) | -175.2 | 130.0 | 20.1 | 224.6 (qNW) | 119.0 (f_su_NW) | 343.6 | 447.0 | 214.8 | 108.7 | 157.3 | - | reach_limited |
| vm_cp_rwb | 1 | tt | 86.8 (ins.json) | -86.8 | 218.4 | 7.6 | 197.7 (o) | 93.5 (i) | 291.2 | 516.0 | 194.6 | 89.0 | 159.8 | - | - |

## Violating tiles and the fix each needs

1. **vm_cp_re** x1 [out_unreg in_unreg abut] (explicit): output pin register missing or far: 1310 bits (ne, se), worst ne leaves 392 ps after the latest boundary clock = 212 ps over a pin flop (logic, or ~279 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 589 bits (tap, cfgi), worst tap needs 301 ps before the earliest boundary clock = 151 ps over a pin flop: first flop ~198 um (or logic) behind the pin: register at the pin
2. **vm_cp_slice2** x1 [out_unreg spread] (explicit): output pin register missing or far: 15 bits (rd), worst rd leaves 272 ps after the latest boundary clock = 92 ps over a pin flop (logic, or ~122 um of wire, after the flop): add / move the output register to the pin; boundary clock spread 95 ps > 80: put the boundary registers on one balanced sub-root (or split the root); every ps is inside o + s (1.3 um of reach per ps)
3. **vm_cp_rt2** x1 [out_unreg] (explicit): output pin register missing or far: 1 bits (cfg), worst cfg leaves 257 ps after the latest boundary clock = 77 ps over a pin flop (logic, or ~101 um of wire, after the flop): add / move the output register to the pin
4. **vm_cp_rb2** x1 [out_unreg] (explicit): output pin register missing or far: 21 bits (rd), worst rd leaves 244 ps after the latest boundary clock = 64 ps over a pin flop (logic, or ~85 um of wire, after the flop): add / move the output register to the pin

Export-SDC: 18 audited cells on corrected views, 0 still pre-fix.

Not auditable (no closed view): none

## Hops: no die case given (contract carries placement but no nets)
