# VIS-S81-MISC handoff (Opus, 11-22 23:5x PST)
Scope: 54 S81 unsigned non-col/non-leaf types in lanes/VIS-COVERAGE.tsv (vis_lane VIS-S81-MISC).
Tools: <host>:/srv/opentallas-scratch2/claude/vis-s81-misc/tools/{vism_one.sh,vism_render.py} (dump via geom_dump.tcl in docker + density/hierarchy/GRT H/V maps). Launch: ot-run --hosts H --mem 24 --threads 2 --dir /srv/opentallas-scratch2/claude/vis-s81-misc -- bash .../tools/vism_one.sh ODB OUTDIR NAME [congestion.rpt]. Outputs .../out/<name>/<name>.{png,json}. Use python3 -E (matplotlib is in user site; epyc10 has none).
Queued renders (intel2 ~/vis-s81-misc/*.log): lepwmuLP_t2, ref_t52 (intel1 memory wait), serdes_t13 (epyc7 load wait).
Verdicts: GEOM-REVIEW.md 23:3x (6 kits) + VIS-COVERAGE 54 rows DRAFT (16 svc NO-RENDER: no placed/bound DB since 11-19).
Family rows to build (STEP 2):
- SLICEC-XGARRAY-1 (16 C + 4 LP): re-site the xg macro array. Generator physical/die_plan/s81/csite_1105/delta_c_macro_sites_1105.py uses CH=10.8 channels + 10.8 stack gaps, packs columns from the W edge. All 3 masters have pins ONLY on W+E (sram128x256 410/409, rom 43/43, sram128x64 105/105). Form: stacks abut N/S (gap 0), pin-face channels demand-sized (>= 64.8 um), array spread east into the empty 2/3. Rows replace contents[] origin_um of the 37 xg macros per type in v10 plan (fam-s81-slice-r6/rows/plan_j8_slice_v10.json). Then plan_gate_pre --baseline-plan, fast place+GRT probe on c1x_C t4, re-render, read. Hand to FAM-S81-SLICE-R6 + S81-J6-ASSEMBLY-R5 (J9 cut 11-23 12:00).
- SERDES-RCK-TAPGRID-1: io_pma_rck enters at one point (27k sinks t16) -> rck tap grid; ft relay siting. Coordinate FAM-S81-SERDES-R8 / FLOW-CLKGRT-R2.
- phy__t1: ruling posted (no clock change; fallback grow N/E 43.2 um if J8p5 GRT shows N-strip overflow).
- singles: BKSEL-BAND-1, GUNIT-SPREAD-1, ENG-NROW-1, station siting seqhost/iqf, t51 DRT map.
