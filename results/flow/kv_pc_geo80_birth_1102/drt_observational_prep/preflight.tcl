# Read-only actual normal DRT environment/master inventory; no module/constructor.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
if {[info commands ot_native_pg_install] ne ""} {error PC_DRT_PREFLIGHT_MUST_HAVE_NO_NATIVE_MODULE}
foreach k {SKIP_DETAILED_ROUTE SKIP_ANTENNA_REPAIR_POST_DRT MAX_REPAIR_ANTENNAS_ITER_DRT PRE_DETAIL_ROUTE_TCL POST_DETAIL_ROUTE_TCL DETAILED_ROUTE_ARGS DETAILED_ROUTE_END_ITERATION REPAIR_PDN_VIA_LAYER} {
 set v <unset>;if {[info exists ::env($k)]} {set v $::env($k)}
 puts "PC_DRT_ACTUAL_NORMAL_POLICY [list $k $v]"
}
source /work/pg_drt_diag_library_guard.tcl
set masters [ot_pg_drt_diag_library_inventory]
set f [open /work/PREFLIGHT_ALL_LOADED_MASTERS.tcllist {WRONLY CREAT EXCL}]
puts $f $masters;close $f
puts "PC_DRT_READ_ONLY_PREFLIGHT_PASS loaded_masters=[llength $masters]"
