foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_*.lib*] { read_liberty $lib }
read_db /input/base_4_1_cts.odb
source /work/landing_exports_check.tcl
set passed {}; set opened {}
foreach row $::ot_cland_export_links {
 if {[catch {ot_cland_export_check_one readonly_native {*}$row} msg]} {
  puts "EXPECTED_NATIVE_OPEN [lindex $row 0] $msg"; lappend opened [lindex $row 0]
 } else { lappend passed [lindex $row 0] }
}
if {[lsort $opened] ne {fclk_out_bu_o fclk_out_h_rx_ft_o} || [llength $passed] != 3} {
 error "native fixture classification mismatch: passed=$passed opened=$opened"
}
set row [lindex $::ot_cland_export_links 0]
set wrong [lreplace $row 1 1 {clk_t8}]
if {![catch {ot_cland_export_check_one wrong_declared_source {*}$wrong} msg]} { error "wrong declared source accepted" }
puts "EXPECTED_WRONG_SOURCE $msg"
puts "READ_ONLY_GUARD_TEST_PASS connected=3 physical_open=2 wrong_source_rejected=1; no ODB write/repair"
