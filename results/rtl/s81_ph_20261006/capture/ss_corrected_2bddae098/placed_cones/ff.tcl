
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

set ot_ck_requested {core_clk}
set ot_ck_selected [get_clocks -quiet $ot_ck_requested]
if {![llength $ot_ck_selected]} {
  set ot_ck_ports [list $ot_ck_requested]
  if {[regexp {^(.*)\[0\]$} $ot_ck_requested -> ot_ck_base]} {
    lappend ot_ck_ports $ot_ck_base
  } else {
    lappend ot_ck_ports [format {%s[0]} $ot_ck_requested]
  }
  foreach c [all_clocks] {
    foreach s [get_property $c sources] {
      set ot_ck_source [get_full_name $s]
      if {$ot_ck_source in $ot_ck_ports && [llength [get_ports -quiet $ot_ck_source]]} {
        lappend ot_ck_selected $c
      }
    }
  }
}
set ot_ck_selected [lsort -unique $ot_ck_selected]
if {[llength $ot_ck_selected] != 1} {
  error "CK_INSERTION: clock '$ot_ck_requested' must resolve to one clock, found [llength $ot_ck_selected]"
}
puts "OT_CK_SELECTED [get_full_name [lindex $ot_ck_selected 0]]"
foreach c [all_clocks] {
  foreach s [get_property $c sources] {
    set sn [get_full_name $s]
    if {![llength [get_ports -quiet $sn]]} continue
    foreach refclk [all_clocks] {
      unset_input_delay -clock $refclk [get_ports $sn]
      unset_input_delay -clock $refclk -clock_fall [get_ports $sn]
    }
    unset_input_delay [get_ports $sn]
    puts "OT_CK_CLOCK_PORT $sn: data input delays dropped"
  }
}


puts "OT_RAW_ROOT_CONTEXT_BEGIN ff before_boundary"
report_clock_properties [all_clocks]
foreach pin {ck[0] ckv[0]} {
 foreach prop {slew_max_rise slew_min_rise} {
  if {[catch {get_property [get_ports $pin] $prop} value]} {puts "OT_RAW_SLEW_UNAVAILABLE $pin $prop $value"} else {puts "OT_RAW_SLEW $pin $prop $value"}
 }
}
report_checks -from [all_registers -clock_pins -clock [get_clocks core_clk]] -to [all_registers -data_pins -clock [get_clocks ser_clk]] -path_delay max -fields {slew capacitance fanout} -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
source /src/physical/s81_ph_views/capture/x8_dual_boundary.tcl
puts "OT_RAW_ROOT_CONTEXT_BEGIN ff after_boundary"
report_clock_properties [all_clocks]
foreach pin {ck[0] ckv[0]} {
 foreach prop {slew_max_rise slew_min_rise} {
  if {[catch {get_property [get_ports $pin] $prop} value]} {puts "OT_RAW_SLEW_UNAVAILABLE $pin $prop $value"} else {puts "OT_RAW_SLEW $pin $prop $value"}
 }
}
report_checks -from [all_registers -clock_pins -clock [get_clocks core_clk]] -to [all_registers -data_pins -clock [get_clocks ser_clk]] -path_delay max -fields {slew capacitance fanout} -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source -165.9 [get_clocks core_clk]
set_clock_latency -source -162.8 [get_clocks ser_clk]
foreach pair {{core_clk core_clk} {ser_clk ser_clk} {core_clk ser_clk} {ser_clk core_clk}} {
 lassign $pair launch capture
 puts "OT_CONE_BEGIN ff $launch $capture"
 set starts [all_registers -clock_pins -clock [get_clocks $launch]]
 set ends [all_registers -data_pins -clock [get_clocks $capture]]
 foreach sense {max min} {
 set paths [find_timing_paths -from $starts -to $ends -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
 if {![llength $paths]} {error "Missing actual cone"}
 set p [lindex $paths 0]
 puts "OT_CONE ff $launch $capture $sense [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]"
 report_checks -from $starts -to $ends -path_delay $sense -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
 }
 puts "OT_CONE_END ff $launch $capture"
}
set bank 0
foreach inst [[ord::get_db_block] getInsts] {if {[string match *bank_n* [$inst getName]]} {incr bank}}
puts "OT_BANK_INSTANCES $bank"
report_checks -path_delay max -format full_clock_expanded -group_path_count 5
exit
