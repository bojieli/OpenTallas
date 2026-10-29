# QC takeover 2026-10-29

`repair_prog_pg.tcl` restores exactly 216 missing supplies on 108 protected s8b clock buffers using the shared
existing PG hook. Native census is 0 open / 408,482 terms; `pg_only_receipt.json` confirms all cell geometry,
signal connectivity, signal route geometry and PG route geometry unchanged. The archived s8b view is an older
259.2 x 354.24 aspect and fails current reach on 89 arcs (maximum446.364um); no new STA or release credit was taken.

`spread_prog_corner.py` instead addresses the current 354.24 x 259.2 PROG layout's persistent DRT failure. It places
376 combinational cells out of the SRAM E-corner escape column into the east street, changing no cells/nets/clock
or register locations. Maximum move21.87um; register reach remains354.73um with zero over405. See the linked
geometry record for the limited GRT-only approval. Actual jobs/data are on epyc2 in
`/srv/opentallas-scratch2/claude/codex-qc-prog-corner-0835/`.

BTAB F3b/F3r inherited routes remain on intel1 in `qc-fix-2-1029/kits/` (units1217062/1270172); their final
TT/FF, DRC, slew and actual BUF calibration gates remain required. Their source and failed predecessors are preserved.
