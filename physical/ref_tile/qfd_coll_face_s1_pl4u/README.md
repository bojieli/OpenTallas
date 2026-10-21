# qfd_coll_face_*_plg / s1_pl4g ('g' recipe, QW-C3-COLLIO 10-21)
From s1_plf/pl4f (fenced) after CTS FAIL cal_ck boundary spread 138.6 ps: 639 cal_ck (u_rxcal.u_r) + 601 cal_lck
(g_land_rx) flops squeezed into the 21.6 um rx/tx ch546 gap. tx ch546 432 -> 475.2 opens a 64.8 um cal channel beside
the cal_ck/cal_lck W pins; 4 clock-region fences (clock_regions.tcl): codec0 band, codec0p E strip, cal_ck W half of
channel, cal_lck E half + E box at phy_*_slot pins. Same RTL/pins/outline as *_pl; P/R/S0/S2 = same geometry.
Checklist: 1 pins PASS (pin regs at region crossings, reset 2-stage landing); 2 reach PASS (textbook reach 0); 3 fanout
PASS (census max 32); 4 depth PASS (488 ps); 5 storage PASS (banks/ch546 SRAM); 6 floorplan: macros on lattice except
inherited 43.224 origins (WARN), channels >= 20 um, outline macro-bound (fill 36%, waived: std area 7k um2 vs 220k macro),
aspect 0.85; 7 clock: regional roots + meso landing rings, spread judged by gate; io_hold 0.03; 8 schedule static (L381/383).
