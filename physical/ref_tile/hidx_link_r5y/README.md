# hidx_link_r5y (FAM-HBM-C/C-IDX 10-21) -- parallel fallback to hidx_link_r5x
RTL/spine identical to r5x (ot_hbm_idx_topk_link_static_p SAFE=2, OT_SPINE_SYM 1). r5x first gate: GRT overflow 0, TT/FF spread 44.6,
setup +5.4 ps, census max 31; failed only fill 34.7% < 35%. r5y: bank pitch 129.6 -> 108 um, outline 650 x 518.4 (fill 37.6%).
SAFE-DESIGN checklist: 1 pins registered in RTL (pin-register shell), 2-stage reset landing PASS; 2 reach PASS (r5x reach 0.2 um);
3 fanout census max 31 PASS; 4 depth 352 ps PASS; 5 storage in 8 SRAM macros PASS; 6 macros on 43.2 lattice, 30.6-um channels
(>= 21.6 r3 minimum), full-width std band, aspect 1.25 PASS; 7 symmetric centre spine, spread measured 44.6 in r5x, io_hold 0.03 PASS;
8 static schedule, +5 edges priced in tools/hbm_idx_static_calendar.py PASS.
