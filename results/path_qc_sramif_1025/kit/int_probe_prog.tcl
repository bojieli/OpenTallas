set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
read_liberty /work/macros/ot_sram_1r1w_256x256_m2_r2c2_ff.lib
read_db $R/5_1_grt_prehold.odb
read_sdc /work/constraint.sdc
set ::env(OT_VCLK_CORNER) ff
source /work/cf/main/vclk_corner.tcl
# what-if knobs (diagnostic only, OT_S6_DRY=1 writes to OT_S6_OUT and never touches the kit DB):
#   OT_S6_IN_MIN  : input -min delay (default = kit SDC -40; PROPOSAL IO-HOLD 06:54 asks -30)
#   OT_S6_IO_M0=1 : IO paths carry no hold margin: repair margin 0 + reg->reg margin as +margin hold uncertainty clk->clk
set O [expr {[info exists ::env(OT_S6_OUT)] ? $::env(OT_S6_OUT) : "/work"}]
set dry [expr {[info exists ::env(OT_S6_DRY)] && $::env(OT_S6_DRY)}]
if {[info exists ::env(OT_S6_IN_MIN)]} { set_input_delay -min $::env(OT_S6_IN_MIN) -clock vclk [all_inputs -no_clocks]; puts "S6_WHATIF input -min $::env(OT_S6_IN_MIN)" }
source /work/cf/rc_cal.tcl
set_global_routing_layer_adjustment M2-M5 0.25
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/cf/mscts_core.tcl
ot_ms_assign_corr ff
ot_ms_report hold_ff
proc s6_ps {v} { return [format %.2f [sta::time_sta_ui $v]] }
set s6_m [expr {[info exists ::env(OT_S6_HOLD_MARGIN)] ? $::env(OT_S6_HOLD_MARGIN) : 15}]
if {[info exists ::env(OT_S6_IO_M0)] && $::env(OT_S6_IO_M0)} {
  set_clock_uncertainty -hold [expr {25.0 + $s6_m}] -from [get_clocks clk] -to [get_clocks clk]
  puts "S6_WHATIF IO margin 0: clk->clk hold uncertainty [expr {25.0 + $s6_m}], repair margin 0"; set s6_m 0
}
set ps [find_timing_paths -path_delay min -from [all_registers] -to [all_registers] -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0]
set f [open /work/int_probe_prog.tsv w]
foreach p $ps {
  set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
  set s [get_property $p slack]
  set pts [get_property $p points]
  set la [get_property [lindex $pts 0] arrival]
  set da [get_property [lindex $pts end] arrival]
  puts $f "[format %.2f $s]\t$sp\t$ep\t[format %.1f $la]\t[format %.1f $da]"
}
close $f
