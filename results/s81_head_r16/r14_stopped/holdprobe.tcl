# R16 read-only probe: TT vs FF hold at input pin registers on the R14 4_cts.odb, vclk bound per corner vs global.
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db /work/run/results/asap7/$::env(NICK)/base/4_cts.odb
define_corners tt ff
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty -corner tt $f }
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty -corner ff $f }
foreach f [glob -nocomplain /work/macros/*_tt.lib] { read_liberty -corner tt $f }
foreach f [glob -nocomplain /work/macros/*_ff.lib] { read_liberty -corner ff $f }
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
set ep [lindex [get_pins -hierarchical $::env(EP)] 0]
foreach lat {250 202.5} {
  set_clock_latency -source $lat [get_clocks vclk]
  foreach c {tt ff} {
    set s [get_property [lindex [find_timing_paths -to $ep -path_delay min -corner $c] 0] slack]
    puts [format "HOLDPROBE vclk %s corner %s slack_ps %.2f" $lat $c [expr {$s*1e12}]]
  }
}
set_clock_latency -source 202.5 [get_clocks vclk]
report_checks -to $ep -path_delay min -corner tt -format full_clock_expanded -digits 1
