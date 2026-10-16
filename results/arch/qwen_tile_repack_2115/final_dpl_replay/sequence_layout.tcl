read_db /out/$::env(R5_STAGE).odb
set ::env(OT_LAYOUT_OUT) /out/$::env(R5_STAGE)_layout.json
set ::env(OT_LAYOUT_TOP) "R5 $::env(R5_TILE) $::env(R5_STAGE) exact source a7a08ca3c"
source /src/tools/ref_tile/layout_dump.tcl
exit
