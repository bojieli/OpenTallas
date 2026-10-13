source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl
set tt {}; set ff {}
set fh [open /out/libs.txt]; foreach l [split [read $fh] \n] { if {$l eq ""} continue; read_liberty $l
  if {[regexp {_TT_|_tt\.lib} $l]} {lappend tt $l} else {lappend ff $l} }; close $fh
read_db /work/diag_check_2.odb
read_sdc -mode ss /work/diag_check_2.sdc
read_sdc -mode ff /work/diag_check_2.sdc
define_scene WC -mode ss -liberty $tt
define_scene BC -mode ff -liberty $ff
set_mode ss
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set blk [ord::get_db_block]
set f [open /out/insts.txt w]
foreach i [$blk getInsts] { set n [$i getName]
  if {[regexp {clkbuf_sp|u_cgt|^place432|^_1246_$|^_0955_$|^_1249_$|u_v3/q\[0\]|sync_q\[1\]|^input3853$|rebuffer4925|wire4334|wire49013|u_ptw$|u_pte$|u_xs$|u_bdc$|u_tr$|u_h0$|u_h1$} $n]} {
    lassign [$i getLocation] x y; set bb [$i getBBox]
    puts $f "$n [[$i getMaster] getName] [expr {$x/1000.0}] [expr {$y/1000.0}] [expr {[$bb xMax]/1000.0}] [expr {[$bb yMax]/1000.0}] [$i getPlacementStatus]" } }
foreach t [$blk getBTerms] { set n [$t getName]; if {$n in {clk rst_n cgi cgo}} { set bb [$t getBBox]; puts $f "PORT $n [expr {[$bb xMin]/1000.0}] [expr {[$bb yMin]/1000.0}]" } }
close $f
proc rp {name args} { if {[catch {report_checks {*}$args -format full_clock_expanded -fields {slew input_pin fanout} -digits 1 > /out/$name.rpt} why]} { set f [open /out/$name.rpt w]; puts $f "REPORT_ERROR $why"; close $f } }
rp ptw_bin0_WC -corner WC -path_delay max -to [get_pins {u.u.u_ptw/bin[0]}] -group_path_count 1
rp ptw_bin0_BC -corner BC -path_delay min -to [get_pins {u.u.u_ptw/bin[0]}] -group_path_count 1
rp rr_WC -corner WC -path_delay max -to [get_pins {u.u.u_rr.rst_n[0]$_DFF_PN0_/RESETN}] -group_path_count 1
rp bdc_rsta_WC -corner WC -path_delay max -to [get_pins {u.u.g_lf[0].u_lh.u_bdc/rst_a}] -group_path_count 1
rp cgt_setn_WC -corner WC -path_delay max -to [get_pins {u.u_cgt.cgo$_DFF_PN1_/SETN}] -group_path_count 1
rp gout99_WC -corner WC -path_delay max -to [get_ports {gout[99]}] -group_path_count 2
puts DIAG2_DONE
exit
