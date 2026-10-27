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
# below-M7 slice (INFRA-FIRST-HEAD-5 head_pg_below_m7.tcl): M1/M2 follow-pins + M5 0.12@4.32 = this core's own kit PDN
# (kit pdn.tcl, identical stripes), M6 0.288@4.32 / M7 0.288@8.64 = ASSUMED partition straps, STRAPS sources.
pdngen -ripup
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {4.32} -offset {2.064}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {2.16}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
define_pdn_grid -macro -default -name {macro} -voltage_domains {CORE} -halo {2.0 2.0} -grid_over_boundary
add_pdn_connect -grid {macro} -layers {M4 M5}
pdngen
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
foreach nn {VDD VSS} { if {[catch {check_power_grid -net $nn} e]} { puts "BM7_PG_CHECK_FAIL $nn $e" } else { puts "BM7_PG_CHECK_OK $nn" } }
foreach nn {VDD VSS} {
  if {[catch {analyze_power_grid -net $nn -source_type STRAPS -voltage_file /work/out/ir_$nn.csv -error_file /work/out/err_$nn.rpt} e]} { puts "BM7_PSM_FAIL $nn $e" } else { puts "BM7_PSM_OK $nn" }
}
exit
