# PG-ACTIVITY-KVHBM 10-27 KV (INFRA-FIRST-HEAD-4 head_pg_power_meas.tcl method, generalised): hard-core power on its routed
# 6_final.odb + 6_final.spef (TT NLDM RVT), register outputs + input ports annotated from /work/act.txt (kv_vcd_activity.py
# lines "name rate"); combinational nets PROPAGATED by OpenSTA.  Kit register/port names normalised: '$_...' stripped, '/' -> '.',
# ports "g_t_<n>_<inst>__<pin>" -> "u_g_t_<n>_<inst>.<pin>".  Unmatched registers / inputs = mean of the matched registers.
# Reports the vectorless (OpenSTA default activity) power of the same view first, for the ratio.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_tt.lib /work/macros/*_typ.lib] { read_liberty $f }
read_db /work/odb/6_final.odb
read_sdc /work/odb/6_final.sdc
read_spef /work/odb/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_VECTORLESS_BEGIN"
report_power -digits 6
puts "OT_VECTORLESS_END"
set fh [open /work/act.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
proc norm {n} { regsub {\$_.*$} $n {} k; regsub -all {/} $k {.} k; regsub {^\\} $k {} k; return $k }
set nm 0; set nu 0; set ni 0; set niu 0; set sum 0.0; set mx 0.0
set regs [all_registers -edge_triggered]
foreach r $regs {
  set n [get_full_name $r]; set k [norm $n]
  if {[info exists A($k)]} { set a $A($k); set R($n) $a; incr nm; set sum [expr {$sum + $a}]; if {$a > $mx} { set mx $a } }
}
set def [expr {$nm ? $sum / $nm : 0.5}]
foreach r $regs {
  set n [get_full_name $r]
  if {[info exists R($n)]} { set a $R($n) } else { set a $def; incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 }
}
foreach p [all_inputs -no_clocks] {
  set n [get_full_name $p]
  regsub {^g_t_([0-9]+)_(u_[a-z0-9]+)__(.*)$} $n {u_g_t_\1_\2.\3} k
  if {[info exists A($k)]} { set a $A($k); incr ni } else { set a $def; incr niu }
  set_power_activity -input_ports $p -activity $a -duty 0.5
}
puts "OT_REG_MATCHED $nm OT_REG_DEFAULT $nu OT_REG_MATCHED_MEAN $def OT_REG_MATCHED_MAX $mx OT_IN_MATCHED $ni OT_IN_DEFAULT $niu"
puts "OT_MEASURED_BEGIN"
report_power -digits 6
puts "OT_MEASURED_END"
exit
