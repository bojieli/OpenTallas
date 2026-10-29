# BTAB turntree diagnostic capacity review

Personally viewed `results/codex_qc_btab_0251/turntree_placed.png` (actual placed ODB render). Four SRAMs form a 2x2 array; broad centre and interrow streets remain clear. Logic follows S and E pin faces. The projected demand hotspot is one small bin beneath the upper-right SRAM southwest corner. No new macro wall, sliver or pin collision appears. Prior actual census includes all four synchronous SRAM endpoints: max conservative hop387.85um,0over405; all319 frozen clock/FT bboxes body0/halo0/hardblock0/PGclear.

GEOM-52 and GEOM-53 requested one >=50-iteration diagnostic before rebuilding. Exact unchanged3_place copy, M2-M5,0.25 layer adjustment,50 congestion iterations, clock nets special: all layers0 overflow,17.52% overall use,368251um wirelength,12096 routed nets. M2/M3/M4/M5 use25.14/17.52/19.95/5.96%. `grt.log` retains exact actual output. The2.604 projection is not measured route shortage.

Verdict: PASS-COND for ONE actual CTS/GRT trial on unchanged turntree, no DRT or signoff approval. Actual propagated TT/FF and related-pair clock gate still required. Existing fullhop, source exactness and PG checks are retained; no RTL/cycles changed. AP7335febad21d waits independent review under BTAB-TURNTREE-GRT50-0251.
