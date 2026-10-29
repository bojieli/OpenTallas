# BTAB compact frozen-clock placement-blockage successor — 2026-10-29 01:09 PDT

Picture: /srv/opentallas-scratch/claude/codex-qc-btab-2348/compact_blockage_clock.png (personally viewed by CODEX and independently by GEOM).

PASS-COND for one placement/CTS/GRT trial, after same-source static preflight (PASS0). No DRT/signoff approval. Four SRAMs form a coherent 2x2 arrangement with central cross and side/bottom logic corridors. Existing ordered S/E data pins and parent origin/outline stay unchanged. All 430 frozen physical clock/FT bboxes clear SRAM bodies, 4.32um halos and all32 actual hard placement-blockage rectangles; PG-clearance PASS. The root moves left .864um solely to clear a SRAM pin-column placement strip; exact M5 entry134.700,19.980, rootcenter134.676,19.845. Same clock graph, stages and masters, no latency/cycle addition, no timing trim.

Preserve separate failures: first geometric emission had57 halo overlaps; first actual trial AP065b42d44ca6 had55 DPL outside-row failures because the site/obstacle input omitted hard pin-column placement strips. Successor explicitly includes these32 hard blockages. Actual TT setup/FF hold (833ps,60/25), clock duty/reach and PG decide; predictions/windows remain INFO only. Actual standard-cell/free-area fill is6.87%, not total-occupation0.473.

Independent GEOM verdict: personally viewed successor430bboxes outside bodies/halos/hard strips; CONCUR PASS-COND one placement/CTS/GRT trial, no DRT approval. Next AP59a1cbd07ea4 compactblock.
