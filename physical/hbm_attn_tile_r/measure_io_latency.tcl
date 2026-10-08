# Routed H16 quad parent IO sign-off (OWNER RULE 2026-10-06 ADDENDUM) at 833.333 ps, from the routed tile's MEASURED
# clock latencies: the die's neighbouring flops are clocked at this tile's insertion +/- 150 ps --
#   inputs : captured by the ROOT bank (median clk latency RIN) -> launch on vclk_in (latency RIN), max 300 / min -150
#   outputs: launched by the quads' leaf flops (quad clk pin + the quad ETM max_clock_tree_path QINS) -> captured on
#            vclk_out (latency QPIN + QINS), max 300 / min -150.
# (-reference_pin crashes buffer_ports in this OpenROAD, so the route runs with false-path IO and this script signs
# the IO off on the routed database.)  env: OT_PLAT, OT_CORNER (ss|ff), OT_QINS, OT_OUT_SDC
set L $::env(OT_PLAT)/lib/NLDM
set C $::env(OT_CORNER)
if {$C eq "ss"} {
  set libs {asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz}
} else {
  set libs {asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
}
foreach l $libs { read_liberty $L/$l }
read_liberty /mv/ot_attn_tile_m6h1q_${C}.lib
read_db [glob /work/results/asap7/*/base/6_final.odb]
read_spef [glob /work/results/asap7/*/base/6_final.spef]
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [get_clocks core_clk]
set q {}; set r {}
foreach i [[ord::get_db_block] getInsts] {
  set m [[$i getMaster] getName]
  if {$m eq "ot_attn_tile_m6h1q"} { lappend q [get_property [get_pins [$i getName]/clk] arrival_max_rise]; continue }
  set n [string map {\\ {}} [$i getName]]
  if {![string match "u_root/*" $n]} {continue}
  if {[$i findITerm CLK] eq "NULL"} {continue}
  lappend r [get_property [get_pins [$i getName]/CLK] arrival_max_rise]
}
set q [lsort -real $q]; set r [lsort -real $r]
set rin [lindex $r [expr {[llength $r] / 2}]]
set qout [expr {[lindex $q end] + $::env(OT_QINS)}]
set sdc [list \
  "create_clock -name core_clk -period 833.333 \[get_ports clk\]" \
  "set_clock_uncertainty -setup 60 \[all_clocks\]" "set_clock_uncertainty -hold 25 \[all_clocks\]" \
  "set_propagated_clock \[get_clocks core_clk\]" \
  "create_clock -name vclk_in -period 833.333" "set_clock_latency [format %.1f $rin] \[get_clocks vclk_in\]" \
  "create_clock -name vclk_out -period 833.333" "set_clock_latency [format %.1f $qout] \[get_clocks vclk_out\]" \
  "set_clock_uncertainty -setup 60 \[get_clocks {vclk_in vclk_out}\]" "set_clock_uncertainty -hold 25 \[get_clocks {vclk_in vclk_out}\]" \
  "set_input_delay -max 300 -clock vclk_in \[all_inputs -no_clocks\]" "set_input_delay -min -150 -clock vclk_in \[all_inputs -no_clocks\]" \
  "set_output_delay -max 300 -clock vclk_out \[all_outputs\]" "set_output_delay -min -150 -clock vclk_out \[all_outputs\]" \
  "set_load 3.898 \[all_outputs\]"]
set f [open $::env(OT_OUT_SDC) w]
puts $f "# $C: measured quad clk pins [join $q ,] ps; ROOT bank clk min/median/max [lindex $r 0] / $rin / [lindex $r end] ps; QINS $::env(OT_QINS)"
foreach l $sdc { puts $f $l }
close $f
foreach l $sdc { eval $l }
set chk [expr {$C eq "ss" ? "max" : "min"}]
set pi [find_timing_paths -path_delay $chk -from [all_inputs -no_clocks] -group_path_count 1]
set po [find_timing_paths -path_delay $chk -to [all_outputs] -group_path_count 1]
puts "OT_IOLAT corner=$C qclk=[join $q ,] root_min=[lindex $r 0] root_med=$rin root_max=[lindex $r end] vclk_in=$rin vclk_out=$qout"
puts "OT_IO_SLACK corner=$C check=$chk in=[get_property [lindex $pi 0] slack] out=[get_property [lindex $po 0] slack]"
report_checks -path_delay $chk -from [all_inputs -no_clocks] -group_path_count 1
report_checks -path_delay $chk -to [all_outputs] -group_path_count 1
