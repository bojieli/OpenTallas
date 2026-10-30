# DIE-QC-47 PRD pass: 4_cts.odb here is the kit 5_1_grt.odb, which already holds the kit PRE_GLOBAL_ROUTE edits
# (96 SRAM keep-off obstructions = 80 pincol + 16 edge M4, CHECKED; 101 planned BUFx6f repeaters). Re-sourcing
# planned_rep.tcl / the keep-off procs on that DB is not idempotent (NULL net) -> only the stateless parts are kept.
source /work/grt_pre.tcl
source /work/drv.tcl
set _b [ord::get_db_block]
if {[llength [$_b getObstructions]] != 96} { error "DIE-QC-47 PRD: expected the kit 96 keep-off obstructions, got [llength [$_b getObstructions]]" }
global_connect
detailed_placement
check_placement -verbose
