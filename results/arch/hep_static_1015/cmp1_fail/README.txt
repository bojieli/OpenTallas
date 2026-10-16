hep_static_cmp_1016-cmp1-91b2723d4 EARLY_FAIL_CONGESTION (GRT-0116), 11 overflow edges, M4 max H 1, total usage 21.6%.
All 11 overflow gcells lie at x 34.2-40.5, y 43.9-47.3 um, inside the lower-left SRAM (MY, x 22.46-193.75, y 23.76-101.54),
12-18 um in from its W (outer, tie/wd[305:266]) face. The compact outline (434.72 x 224.64) puts the macro rows beside the
W SerDes pin span (sd_tx/sd_rx/sd_st at y 2-143 um, 1,084 pins), so the SerDes gearbox logic and 1,024 lane bits share the
20 um W edge channel with that face's ties (density.png: green column along W). Route 3 (434.72 x 315.36) keeps the macro
rows above y 114, clear of the W pin span: trial GRT overflow 0. The W pin span (>= 104 um at 2 M4 tracks per pin) sets the
band height, so the band is pin-bound, not empty.
