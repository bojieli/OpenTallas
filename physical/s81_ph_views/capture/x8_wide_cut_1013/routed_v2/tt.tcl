
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

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
set_clock_latency -source -173.8 [get_clocks core_clk]
set_clock_latency -source -208.9 [get_clocks ser_clk]
foreach pair {{core_clk ser_clk core serial} {ser_clk core_clk serial core}} {
 lassign $pair launch capture a b
 foreach sense {max min} {
  set paths [find_timing_paths -from [all_registers -clock_pins -clock [get_clocks $launch]] -to [all_registers -data_pins -clock [get_clocks $capture]] -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
  if {![llength $paths]} {error "missing actual crossing $launch/$capture/$sense"}
  set p [lindex $paths 0]
  puts "OT_CAPTURE_PHASE {\"corner\":\"tt\",\"launch\":\"$a\",\"capture\":\"$b\",\"sense\":\"$sense\",\"startpoint\":\"[get_full_name [get_property $p startpoint]]\",\"endpoint\":\"[get_full_name [get_property $p endpoint]]\",\"slack_ps\":[get_property $p slack]}"
 }
}
if {"tt" eq "tt"} {
 set block [ord::get_db_block]
 set dbu [$block getDbUnitsPerMicron]
 foreach net [$block getNets] {
  if {![$net isSpecial]} continue
  foreach sw [$net getSWires] {
   foreach box [$sw getWires] {
    set layer [$box getTechLayer]
    if {$layer eq "NULL" || [$layer getName] ne "M5"} continue
    set x0 [expr {[$box xMin]/double($dbu)}]; set x1 [expr {[$box xMax]/double($dbu)}]
    set y0 [expr {[$box yMin]/double($dbu)}]; set y1 [expr {[$box yMax]/double($dbu)}]
    if {($y0 <= 0.192 && $y1 >= 0) || ($y0 <= 136.08 && $y1 >= 135.888)} {puts "OT_CAPTURE_PG [$net getName] $x0 $y0 $x1 $y1"}
   }
  }
 }
}
exit
