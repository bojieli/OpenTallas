proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err" }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }

step libs {
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /work/libs/qfd_etm_ss.lib
read_liberty /work/libs/qfd_elements_ss.lib
read_liberty /work/libs/ot_hbm3e_phy_ss.lib
}
step load { read_db /work/ckpt_grt.odb }
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
step guides { read_guides /work/route.guide }
set_routing_layers -signal M4-M9 -clock M4-M9
step est { estimate_parasitics -global_routing }
# clocks: the stream clock leaves the hub's region PLL pins and the IO collective's stream PLL; serial / UCIe / SerDes
# / HBM controller clocks are separate (asynchronous groups, crossings are CDC FIFOs)
create_clock -name stream -period 833.333 [get_pins -quiet {hub_el/pll_r* io_collective/pll_stream}]
create_clock -name serial -period [expr {833.333*4.0/3.0}] [get_pins -quiet io_collective/pll_serial]
foreach c {ucie serdes} { create_clock -name $c -period 833.333 [get_pins -quiet io_collective/pll_$c] }
foreach s {WS WN ES EN} { create_clock -name hclk_$s -period 1024 [get_pins -quiet ctrl_$s/pll_hbm] }
set_clock_groups -asynchronous -group stream -group serial -group ucie -group serdes -group hclk_WS -group hclk_WN \
  -group hclk_ES -group hclk_EN
set_clock_uncertainty -setup 60 [all_clocks]
step sta {
  report_checks -path_delay max -group_path_count 3000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/grt_ss_ends.rpt
  report_checks -path_delay max -group_path_count 5 -fields {slew cap input_pins nets} -digits 1 > /work/grt_ss_paths.rpt
  report_tns; report_wns; report_worst_slack -max
  report_check_types -max_slew -max_capacitance -violators > /work/grt_ss_drv.rpt
}
puts OT_STA_DONE
