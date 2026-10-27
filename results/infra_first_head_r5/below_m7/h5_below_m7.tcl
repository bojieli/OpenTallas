# INFRA-FIRST-HEAD-5: drop below M7 on the elemB hotspot core (measured activity), M1-M5 = core's own signed PDN,
# M6/M7 = ASSUMED tile partition straps (M6 0.288@4.32 H, M7 0.288@8.64 V = the PDNSim window block M7 pins); ideal M7 sources.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db /work/odb/6_final.odb
read_sdc /work/constraint.sdc
read_spef /work/odb/6_final.spef
set_propagated_clock [all_clocks]
set fh [open /work/act_fix.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
set nm 0; set sum 0.0; set regs [all_registers]
foreach r $regs { set n [get_full_name $r]; regsub {\$_.*$} $n {} k; regsub {^u_m\.} $k {} k
  if {[info exists A($k)]} { set R($n) $A($k); incr nm; set sum [expr {$sum+$A($k)}] } }
set def [expr {$sum/$nm}]
foreach r $regs { set n [get_full_name $r]; set a [expr {[info exists R($n)] ? $R($n) : $def}]
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 } }
foreach p [all_inputs -no_clocks] { set n [get_full_name $p]; set a [expr {[info exists A($n)] ? $A($n) : $def}]; set_power_activity -input_ports $p -activity $a -duty 0.5 }
puts "H5_REG_MATCHED $nm DEF $def"
report_power -digits 6
set block [ord::get_db_block]
set die [$block getDieArea]
puts "H5_DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax]"
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
foreach nn {VDD VSS} { if {[catch {check_power_grid -net $nn} e]} { puts "H5_PG_CHECK_FAIL $nn $e" } else { puts "H5_PG_CHECK_OK $nn" } }
foreach nn {VDD VSS} {
  if {[catch {analyze_power_grid -net $nn -source_type STRAPS -voltage_file /work/out/ir_$nn.csv -error_file /work/out/err_$nn.rpt} e]} { puts "H5_PSM_FAIL $nn $e" } else { puts "H5_PSM_OK $nn" }
}
exit
