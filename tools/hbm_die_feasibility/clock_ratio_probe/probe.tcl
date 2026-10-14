read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog /probe/probe.v
link_design ratio_probe
report_units
set cp 833.333
if {$::env(PROBE_MODE) ne "ROUNDED"} { set vp [expr {$cp*4.0/3.0}] } else {set vp 1111.111}
puts "PROBE_PERIOD mode=$::env(PROBE_MODE) C=$cp V=$vp fourC=[expr {4*$cp}] threeV=[expr {3*$vp}]"
create_clock -name C -period $cp -waveform [list 0 [expr {$cp/2.0}]] [get_ports c]
create_clock -name V -period $vp -waveform [list 0 [expr {$vp/2.0}]] [get_ports v]
create_generated_clock -name VN -source [get_ports v] -master_clock V -divide_by 1 -invert [get_pins u_inv/Y]
set_input_transition 25 [get_ports {c v}]
set_clock_uncertainty -setup 210 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
if {$::env(PROBE_MODE) eq "SHIFT100"} {
 set off [sta::time_sta_ui [expr {-100.0*1e-12}]]
 puts "KNOWN_TEST_OFFSET_C_UI $off; not measured child insertion"
 set_clock_latency -source $off [get_clocks C]
}
set_propagated_clock [all_clocks]
foreach pair {{C V} {V C} {C VN} {VN C}} {
 lassign $pair a b
 foreach delay {max min} {
  puts "PAIR_BEGIN $a $b $delay"
  report_checks -from [get_clocks $a] -to [get_clocks $b] -path_delay $delay -group_path_count 1 -format full_clock_expanded -digits 6
  puts "PAIR_END $a $b $delay"
 }
}
puts "PROBE_COMPLETE $::env(PROBE_MODE)"
exit
