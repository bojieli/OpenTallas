# BTAB compact2x2 — PASS-COND for trial data placement

Viewed `results/codex_qc_btab_2348/shrink_estimate.png`, including its actual candidate pin map, 2026-10-29 00:14 PDT. Candidate35472bb7a; current ev_qc25/trial25 unchanged.

Four SRAMs form a 2x2 array inside259.2x138.24um. All4.32um halos are disjoint. The central vertical channel30.456um and outer channels>=17.28um use55.3%/48.8% of estimated M3+M5 tracks. The clock/reset island is in the central cross, clear of macro bodies/halos. Clock pin127.452,69.12 lies on M5 0.012+0.048n. S pins retain source order at0.24um pitch, E pins at0.384um pitch; all1318names/directions unchanged. Rectangle diameter397.44um is a geometric bound, not extracted timing. Parent partition outlines/core origins unchanged; zero added data/control cycles.

PASS-COND for ONE trial data placement and actual sink census. Before CTS: inspect placed density, clock and PG clearance, macro pin escape, full r2r reach, and macro-inclusive planned-tree windows. No CTS/route authorization yet. Actual PG continuity/IR and routed clock arrivals NOT RUN.
