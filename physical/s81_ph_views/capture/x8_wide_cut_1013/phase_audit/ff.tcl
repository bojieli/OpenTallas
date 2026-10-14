
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


proc phase_report {corner stage} {
    foreach pair {{core_clk ser_clk} {ser_clk core_clk}} {
        lassign $pair launch capture
        set starts [all_registers -clock_pins -clock [get_clocks $launch]]
        set ends [all_registers -data_pins -clock [get_clocks $capture]]
        foreach sense {max min} {
            set paths [find_timing_paths -from $starts -to $ends -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
            if {![llength $paths]} {error "phase probe missing $launch->$capture/$sense"}
            set p [lindex $paths 0]
            puts "PHASE_PAIR $corner $stage $launch->$capture $sense [get_property $p slack] [get_full_name [get_property $p endpoint]]"
        }
    }
}
phase_report ff common_pin_phase
set_clock_latency -source -141.5 [get_clocks core_clk]
set_clock_latency -source -162.1 [get_clocks ser_clk]
phase_report ff compensated_pin_phase
