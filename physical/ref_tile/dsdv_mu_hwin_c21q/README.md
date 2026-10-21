# dsdv_mu_hwin_c21q (DRIVE-S81-HWIN, 10-20)

Successor of c21n. c21n gate (ep7 ref_gate/dsdv_mu_hwin_c21n-20261020-082130) FAILED trial GRT: total overflow 4657
(M2 1658 / M3 648 / M4 1849 / M5 502; total usage only 20%). All overflow sits in two columns x 140..168 and x 396..424,
across the whole band height 156..208 -- exactly the W|C (x147.8) and C|E (x413.8) EXCLUSIVE-fence seams. Cells whose cones
reach more than one owner are forced into CENTRE and pile against each seam. This is structural to hard region fences.

Fix: ONE band-owner region (CENTRE box = full-width band 2.16..559.44 x 159.84..206.28; all manifest owners CENTRE), as the
unfenced c21h layout that routed GRT0. Unchanged: native-safe RTL/params (c21j, mapped census MAX32), 84 SRAM origins, pins,
band rows, PG bind, birth-ownership hooks, clock. GPL pd 0.48 (c21o 0.55 main / c21p 0.48 fallback, run in parallel).

Safe-design checklist: 1 pins registered PASS (unchanged); 2 reach: fence-box proof no longer applies -> post-place native
reach audit owed (guidance under the 10-20 RULE FREEZE); 3 fanout census MAX32 PASS (RTL unchanged); 4 depth 546.8 ps PASS;
5 storage in SRAM PASS; 6 lattice/one full-width band/aspect 1.44 PASS; 7 clock centre-fed, spread checked at gate;
8 schedule static PASS (no RTL change).
