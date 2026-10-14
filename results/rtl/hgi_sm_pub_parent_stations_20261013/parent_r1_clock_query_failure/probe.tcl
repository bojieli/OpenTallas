source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_3_place_gp-failed.odb 2_floorplan.sdc
estimate_parasitics -placement
set ::ot_ce_require_wire 1
set ::ot_ref_pre_cts 0
source /probe/smpub-rsz-debug-candidate.tcl
sta::set_cmd_scene [sta::find_scene BC]
set ::ot_ioref_scene BC
ot_ce_apply
report_arrival -scene BC {g_c\[0\].u_port/clk}
report_checks -to [get_ports {vmq[100]}] -path_delay min -format full_clock_expanded
rename ot_ce_clock_wire ot_ce_clock_wire_good
proc ot_ce_clock_wire {pin clock} {
 set bogus [get_clocks ot_entry_0]
 return [ot_ce_clock_wire_good $pin $bogus]
}
if {![catch {ot_ce_apply} msg] || ![string match {*missing unique finite propagated clock arrival*} $msg]} {
 error "NEGATIVE: wrong clock unexpectedly accepted: $msg"
}
puts "NEGATIVE_CLOCK_TAG PASS $msg"
