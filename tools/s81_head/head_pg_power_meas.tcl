# INFRA-FIRST-HEAD-4 PG: head hard-core power with MEASURED switching activity (OWNER 10-27).
# Register outputs + input ports annotated from the RTL toggle run (head_activity.py -> /work/act.txt lines "rel rate");
# combinational nets are PROPAGATED by OpenSTA from those (no -global).  Registers whose RTL name is not found get the
# mean rate of the MATCHED registers, counted and reported.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db /work/odb/5_1_grt.odb
read_sdc /work/constraint.sdc
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set fh [open /work/act.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
set nm 0; set nu 0; set ni 0; set niu 0; set sum 0.0; set mx 0.0
set regs [all_registers]
foreach r $regs {
  set n [get_full_name $r]
  regsub {\$_.*$} $n {} k
  regsub {^u_m\.} $k {} k
  if {[info exists A($k)]} { set a $A($k); set R($n) $a; incr nm; set sum [expr {$sum + $a}]; if {$a > $mx} { set mx $a } }
}
set def [expr {$nm ? $sum / $nm : 0.5}]
foreach r $regs {
  set n [get_full_name $r]
  if {[info exists R($n)]} { set a $R($n) } else { set a $def; incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] {
    set_power_activity -pins $p -activity $a -duty 0.5
  }
}
foreach p [all_inputs -no_clocks] {
  set n [get_full_name $p]
  if {[info exists A($n)]} { set a $A($n); incr ni } else { set a $def; incr niu }
  set_power_activity -input_ports $p -activity $a -duty 0.5
}
puts "OT_REG_MATCHED $nm OT_REG_DEFAULT $nu OT_REG_MATCHED_MEAN $def OT_REG_MATCHED_MAX $mx OT_IN_MATCHED $ni OT_IN_DEFAULT $niu"
report_power -digits 6 > /work/power_$::env(OT_TAG).rpt
report_power -digits 6
exit
