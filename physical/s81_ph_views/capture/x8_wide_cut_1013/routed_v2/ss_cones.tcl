
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_SS_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_SS_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
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


create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source -227.1 [get_clocks core_clk]
set_clock_latency -source -273.4 [get_clocks ser_clk]

foreach pair {{core_clk core_clk} {ser_clk ser_clk} {core_clk ser_clk} {ser_clk core_clk}} {
 lassign $pair launch capture
 puts "SS_CONE_BEGIN $launch $capture"
 set starts [all_registers -clock_pins -clock [get_clocks $launch]]
 set ends [all_registers -data_pins -clock [get_clocks $capture]]
 report_checks -from $starts -to $ends -path_delay max -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
 report_checks -from $starts -to $ends -path_delay min -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
 puts "SS_CONE_END $launch $capture"
}
puts "SS_EPOCH core [get_property [get_clocks core_clk] period] serial [get_property [get_clocks ser_clk] period]"
exit
