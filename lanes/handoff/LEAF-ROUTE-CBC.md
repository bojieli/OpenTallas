# LEAF-ROUTE-CBC handoff (Opus; started 11-22 22:5x PST by COORD)
Goal: close the routing-demand gap in CBC for the S81 leaf family. Pairs with OPUS-FIX-S81-LEAF-R10 (owns leaf GRTCONG/REACH/SRE-SRC rows; their J9-LEAF-GRTCONG covers t68/t50/t54/t13/t51 macro moves) and OPUS-FIX-S81-LEAF-TAPHOLD-R2. Rows -> S81-J6-ASSEMBLY-R5 (J9 cut 11-23 12:00).
Lane dirs: /srv/opentallas-scratch3/claude/leaf-route-cbc on every gen host (kit/ = lrc_dump.tcl, lrc_run.sh, lrc_cong.py; db/<t> staged 4_cts.odb + congestion rpt copies; dump/<t>; cong/<t>). Clone: epyc9 /srv/opentallas-scratch3/claude/leaf-route-cbc/clone (main c4c1e9e0c1). intel2 /srv/opentallas-scratch2/claude/leaf-route-cbc/leaf_types_j8.json = 80 leaf types from J8 f65f62779bef (relay_sites dropped).

## Task 1 (LOOK): 10 worst leaf types at 5_1_grt
t21 t44 t39 t52 t58 t42 t65 t25 t53 t11 (t60 kit gone). Source DB = staged 4_cts.odb; GRT = highest-round congestion-N.rpt (OpenROAD caps at 20000 entries: spatially random sample, so treat as a sample).
Status: dumps launched 23:2x (ot-run pinned per host, 8 GB). Renders + GEOM-REVIEW verdicts next.

## Task 2 (estimator) / 3 (form) / 4 (probe rule): not started
