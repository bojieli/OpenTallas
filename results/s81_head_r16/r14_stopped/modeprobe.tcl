set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
define_corners tc bc
set TTL [concat [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] /work/macros/ot_rom_4096x274_m8_tt.lib]
set FFL [concat [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] /work/macros/ot_rom_4096x274_m8_ff.lib]
foreach f $TTL { read_liberty -corner tc $f }
foreach f $FFL { read_liberty -corner bc $f }
read_db /work/run/results/asap7/hd_elemA_rb/base/4_cts.odb
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
proc rep {tag} { puts "$tag all [sta::time_sta_ui [sta::worst_slack_cmd min]] n [sta::endpoint_violation_count min]"
  foreach s [get_scenes *] { if {[catch {puts "  $tag scene $s [sta::time_sta_ui [sta::worst_slack_scene $s min]]"} e]} {puts "  $tag scene ERR $e"} } }
set_clock_latency -source 202.5 [get_clocks vclk]
rep GLOBAL202
set_clock_latency -source 250 [get_clocks vclk]
rep GLOBAL250
if {[catch {
  define_scene bc -mode ffm -liberty $FFL
  read_sdc -mode ffm /work/constraint.sdc
  set_mode ffm
  set_propagated_clock [get_clocks clk]
  set_clock_latency -source 202.5 [get_clocks vclk]
  set_mode default
} e]} { puts "MODEERR $e" }
foreach m [get_modes *] { puts "MODE $m" }
rep PERMODE
set p [lindex [find_timing_paths -to {u_m.g_pin.x_q[137]$_DFF_P_/D} -path_delay min -group_path_count 4] 0]
report_checks -to {u_m.g_pin.x_q[137]$_DFF_P_/D} -path_delay min -digits 1 -group_path_count 2
