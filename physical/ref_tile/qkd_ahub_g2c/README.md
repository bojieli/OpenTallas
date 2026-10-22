# qkd_ahub_g2c (KV-AHUB3 10-19, fallback) -- gate c1 on 9ffb16f94: FAIL (clock_rule)
Gate: FAIL (1 fail, 13 warn); a7 spine 5,930 sinks, TT insertion 977.5 / FF 807.4, pin-flop spread 124.3 TT / 137.8 FF (> 80);
placement reg->reg worst -44.0 ps (u_core.tq[2]); trial GRT overflow 0. PNGs inspected (gate_layout/density.png): logic mass in the
W half between the Z trees, recip leaf E-centre, E-face pin flops at x 734 -> one spine over the full width again (as sfa/sfb).
Checklist: 1 PASS, 2 PASS (GRT 0, 3+3 relays), 3 PASS, 4 placement -44 ps (tq stack-check flops), 5 PASS, 6 PASS (a7 geometry,
zh0/zh1 lattice waiver), 7 FAIL, 8 PASS (HUB_RECIP/PUB +6). Not submitted.
