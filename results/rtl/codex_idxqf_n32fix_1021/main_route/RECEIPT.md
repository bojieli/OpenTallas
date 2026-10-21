# QF MAIN actual routed result

Normal qualified job dsdv_idx_qf-dsdv_idx_qf-d20b68c2b, route.a1 on ot-gold2, source d20b68c2b / logic f7412b6c2 / source repair ed9c179a2. Route terminal rc0, flow_rc0, corner_rc0 at actual15:26:10 PT. Selected propagated-boundary corner STA closes_signoff true: TT setup +59.20ps, FF hold +13.56ps, zero violating D pins; SS sensitivity -225.19ps retained. Final ODB b6d6363327d65b582fbc64af6db51e9937a7446ed8ab6f28007c88eab0b6841d; SPEF70f70a9d4e6e2312794446d6544d52ad1c0accd90639280a37657446fc6a0c7e.

Personally viewed actual final congestion and density PNGs: no congested cells; density blue with small green edge strips, no red. Geometry remains exact ROOT-approved gate profile259.2x432, not a minimum-area claim. Source/native/reset/clock guidance and parent405um landing/compensation obligations are in prior MAIN review packet.

Raw generic physical.json also retained: it reports not_met under its separate timing/slew aggregate (setup -38.6149ps, hold -218.576ps,14max-slew), while actual selected TT/FF signoff above passes owner policy; no claim that every aggregate check passes. DRC=0 in that raw physical report. Daemon collection/verdict still pending at receipt time; no CLOSED/adoption asserted.
