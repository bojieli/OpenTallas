set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_ff.lib] { read_liberty $f }
read_db $R/5_1_grt.odb
read_sdc /work/constraint.sdc
set ::env(OT_VCLK_CORNER) ff
source /work/cf/main/vclk_corner.tcl
source /work/cf/rc_cal.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set ps [find_timing_paths -path_delay min -from [all_inputs -no_clocks] -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0]
set ends {}; set dt 0; set ft 0
foreach p $ps {
  set e [get_full_name [get_property $p endpoint]]
  set sp [get_full_name [get_property $p startpoint]]
  lappend ends "$sp -> $e [format %.1f [get_property $p slack]]"
}
puts "N [llength $ps]"
foreach x [lrange $ends 0 15] { puts "E $x" }
set blk [ord::get_db_block]
set n 0; foreach net [$blk getNets] { if {[$net isDoNotTouch]} { incr n } }
puts "dont_touch nets $n"
set n 0; foreach i [$blk getInsts] { if {[$i isDoNotTouch]} { incr n } }
puts "dont_touch insts $n"
report_checks -path_delay min -from [all_inputs -no_clocks] -format full_clock_expanded -fields {cap fanout net}
