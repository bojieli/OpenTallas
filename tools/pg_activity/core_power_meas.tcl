# PG-ACTIVITY-KVHBM (10-27): core power, vectorless (OpenSTA default) AND measured RTL activity, on the same odb.
# Method = INFRA-FIRST-HEAD-4 head_pg_power_meas.tcl: register outputs + input ports annotated from /work/act.txt
# ("rel rate" per bit, transitions/cycle), combinational propagated, unmatched registers get the matched mean.
# env: OT_ODB, OT_SDC, OT_TAG, OT_PREFIX (regsub prefix stripped from register names), OT_PLACED (1 -> estimate_parasitics -placement)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_tt.lib] { read_liberty $f }
read_db $::env(OT_ODB)
read_sdc $::env(OT_SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {$::env(OT_PLACED)} { estimate_parasitics -placement; set_propagated_clock [all_clocks] }
report_power -digits 6 > /work/out/power_$::env(OT_TAG)_vectorless.rpt
set fh [open /work/act.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
set nm 0; set nu 0; set ni 0; set niu 0; set sum 0.0; set mx 0.0
set regs [all_registers]
set pre $::env(OT_PREFIX)
foreach r $regs {
  set n [get_full_name $r]
  regsub {\$_.*$} $n {} k
  regsub -all {/} $k {.} k
  regsub -all {\\} $k {} k
  regsub {_reg(\[[0-9]+\])?$} $k {\1} k2
  if {$pre ne ""} { regsub "^$pre" $k {} k; regsub "^$pre" $k2 {} k2 }
  # exact name, then hierarchical SUFFIX match (drop leading instance segments, keep >= 2 segments):
  # the SM leaf in the bench (u_bdc / u_tcc ...) sits under a different parent path than in the hard core
  set cands [list $k $k2]
  set segs [split $k .]
  for {set j 1} {$j < [llength $segs] - 1} {incr j} { lappend cands [join [lrange $segs $j end] .] }
  foreach kk $cands {
    if {[info exists A($kk)]} { set a $A($kk); set R($n) $a; incr nm; set sum [expr {$sum + $a}]; if {$a > $mx} { set mx $a }; break }
  }
}
set def [expr {$nm ? $sum / $nm : 0.5}]
foreach r $regs {
  set n [get_full_name $r]
  if {[info exists R($n)]} { set a $R($n) } else { set a $def; incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 }
}
foreach p [all_inputs -no_clocks] {
  set n [get_full_name $p]
  if {[info exists A($n)]} { set a $A($n); incr ni } else { set a $def; incr niu }
  set_power_activity -input_ports $p -activity $a -duty 0.5
}
puts "OT_REG_MATCHED $nm OT_REG_DEFAULT $nu OT_REG_TOTAL [llength $regs] OT_REG_MATCHED_MEAN $def OT_REG_MATCHED_MAX $mx OT_IN_MATCHED $ni OT_IN_DEFAULT $niu"
report_power -digits 6 > /work/out/power_$::env(OT_TAG)_meas.rpt
exit
