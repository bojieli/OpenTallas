# DIE-HBM-55 (2026-10-31)
1. CE-tail root bind: ot_hbm_hc_root_static_ce_phys ports == bound ot_hbm_hc_root_static_s blackbox (39 ports / 3986 bits, names/dirs/widths).
   Strict all-gap bind d44p (die_plan d8d63587cf3e) with alias -> ce_phys vs without, same main tool, cached g3 elaboration:
   identical {crossings 907, crossing_bits 382719, errors 258, unbound 42412, tied 16072} (tied/errors vs the 10-30 d44f run = newer bind.py, not CE).
2. q_b011 g50 140,343 ov (d44f) = L15x1 (4128 b) stations 1+2 stacked in the 25-um W strip (x 0-25) beside the macro column x 24.8-277.6.
   Variant A (site_mx corridor walk --resite): G2 0-it 3,138,868 (worse, stopped). Variant B (site_strip.py: 3 station columns in the E strip
   346-374/314-342/282-310, y-interpolated, last station y = out pin, M6 run over macros; hops 301/328/328/310 <= 394.9):
   G2 q_b011 0-it 1,026,793 -> 605,087; L15x1 share 3.23M -> 0.84M. G0/G0C 0 new / 0 gone (966 / 1319). 50-it B: epyc2 die-hbm-55/g2/d44q_B_i50.
