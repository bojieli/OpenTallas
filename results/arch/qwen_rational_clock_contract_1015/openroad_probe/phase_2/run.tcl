set_thread_count 1
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set tlibs [glob $P/lib/NLDM/*RVT_TT*]
set flibs [glob $P/lib/NLDM/*RVT_FF*]
foreach l [concat $tlibs $flibs] {read_liberty $l}
read_verilog /w/top.v
link_design top
read_sdc -mode ss /w/clocks.sdc
read_sdc -mode ff /w/clocks.sdc
define_scene TC -mode ss -liberty $tlibs
define_scene BC -mode ff -liberty $flibs
set_mode ss
foreach sc {TC BC} {
 set_scene $sc
 report_clock_properties [all_clocks]
 foreach clock {core fdi_ck rx0_ck rx1_ck rx2_ck} {
  set expected [expr {$clock eq "core" ? 2500.0/3.0 : 1000.0}]
  if {abs([sta::time_sta_ui [[lindex [get_clocks $clock] 0] period]]-$expected)>0.01} {error "Wrong clock frequency $clock"}
 }
 puts "SCENE $sc"
 report_clock_properties [all_clocks]
 foreach pair {{core_launch fdi_capture} {fdi_capture core_capture} {fdi_capture rx0_capture}} {
  lassign $pair a b
  foreach kind {max min} {
   set paths [find_timing_paths -from [get_pins $a/CLK] -to [get_pins $b/D] -scenes $sc -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
   if {[llength $paths] != 1} {error "Missing ordinary $kind path $a to $b in $sc"}
   puts "ORDINARY_PATH $sc $a $b $kind"
   report_checks -from [get_pins $a/CLK] -to [get_pins $b/D] -scenes $sc -path_delay $kind -format full_clock_expanded -digits 6
  }
 }
 foreach endpoint {padding_fault rx0_input rx1_capture rx2_capture} {
  foreach kind {max min} {
   set paths [find_timing_paths -scenes $sc -from [get_ports shared_rx] -to [get_pins $endpoint/D] -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
   if {[llength $paths] != 1} {error "Missing actual shared input $kind path $endpoint in $sc"}
   puts "SHARED_INPUT_PATH $sc $endpoint $kind"
   report_checks -scenes $sc -from [get_ports shared_rx] -to [get_pins $endpoint/D] -path_delay $kind -format full_clock_expanded -digits 6
  }
 }
}
puts "RATIONAL_EDGE_PROBE PASS_ENGINE_ONLY"
