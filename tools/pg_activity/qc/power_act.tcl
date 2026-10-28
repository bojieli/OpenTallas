# QC-PG-3: report_power with a given register/input activity file (same method as Codex qc-a0-activity power.tcl /
# INFRA-FIRST-HEAD-4), but unmatched regs/inputs get OT_DEF / OT_IN_DEF (0 = clock floor) instead of the matched mean.
# env: OT_ODB OT_SDC OT_RC OT_TAG OT_ACT (file or none) OT_DEF OT_IN_DEF OT_OUT OT_MACROS (dir)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain $::env(OT_MACROS)/*_tt.lib] { read_liberty $f }
read_db $::env(OT_ODB)
read_sdc $::env(OT_SDC)
source $::env(OT_RC)
estimate_parasitics -placement; set_propagated_clock [all_clocks]
array set A {}
if {$::env(OT_ACT) ne "none"} { set fh [open $::env(OT_ACT) r]; while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }; close $fh }
set nm 0; set nu 0; set ni 0; set niu 0
foreach r [all_registers] {
  set n [get_full_name $r]
  regsub {\$_.*$} $n {} k; regsub -all {/} $k {.} k; regsub -all {\\} $k {} k
  regsub {_reg(\[[0-9]+\])?$} $k {\1} k2
  set cands [list $k $k2]; set segs [split $k .]
  for {set j 1} {$j < [llength $segs] - 1} {incr j} { lappend cands [join [lrange $segs $j end] .] }
  set a $::env(OT_DEF); set hit 0
  foreach kk $cands { if {[info exists A($kk)]} { set a $A($kk); set hit 1; break } }
  if {$hit} { incr nm } else { incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 }
}
foreach p [all_inputs -no_clocks] {
  set n [get_full_name $p]
  if {[info exists A($n)]} { set a $A($n); incr ni } else { set a $::env(OT_IN_DEF); incr niu }
  set_power_activity -input_ports $p -activity $a -duty 0.5
}
puts "OT_REG_MATCHED $nm OT_REG_DEFAULT $nu OT_IN_MATCHED $ni OT_IN_DEFAULT $niu"
report_power -digits 6 > $::env(OT_OUT)
exit
