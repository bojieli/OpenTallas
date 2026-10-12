
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
read_sdc /src/physical/hbm_accel_die_views/vm/vcut8/fclat.sdc
read_sdc /src/physical/hbm_accel_die_views/common/signoff_unc60.sdc
read_sdc /src/physical/hbm_accel_die_views/common/vclk_corner_true.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
set fo [open /t/FF.txt w]
set blk [ord::get_db_block]
foreach bt [$blk getBTerms] {
  set n [regsub {\[0\]$} [$bt getName] {}]
  if {![regexp {^ck[wens][0-9]*$} $n]} { continue }
  # walk the clock tree in the db: through buffers / inverters to the sequential clock pins
  set todo [list [$bt getNet]]; set seen [dict create]; set s 0.0; set k 0
  while {[llength $todo]} {
    set net [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {$net eq "NULL" || [dict exists $seen [$net getName]]} { continue }
    dict set seen [$net getName] 1
    foreach it [$net getITerms] {
      if {[$it isOutputSignal]} { continue }
      set inst [$it getInst]; set m [$inst getMaster]
      if {[$m isSequential]} {
        set nm [$inst getName]
        if {[string match *DFFL* [$m getName]] || [string match *_DFF_N* $nm]} { continue }
        set mt_ [[$it getMTerm] getName]
        set pin [get_pins -quiet "[string map {[ \\[ ] \\]} [string map {\\ {}} $nm]]/$mt_"]
        if {![llength $pin]} { set pin [get_pins -quiet "$nm/$mt_"] }
        if {![llength $pin]} { continue }
        set v [get_property $pin arrival_max_rise]
        if {[string is double -strict $v]} { set s [expr {$s + $v}]; incr k; puts $fo "CK $n $nm $v" }
      } else {
        foreach o [$inst getITerms] { if {[$o isOutputSignal]} { lappend todo [$o getNet] } }
      }
    }
  }
  if {$k} { puts $fo "$n [expr {$s / $k}] $k" }
}
foreach pe [find_timing_paths -path_delay min -group_path_count 30000 -endpoint_path_count 1 -slack_max 0] {
 set slack [get_property $pe slack]; set sp [get_full_name [get_property $pe startpoint]]; set ep [get_full_name [get_property $pe endpoint]]
 puts $fo "H $slack $sp $ep"
}
close $fo
report_checks -path_delay min -group_path_count 30 -format full_clock_expanded -digits 3 > /t/hold_paths.rpt
