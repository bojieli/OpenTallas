source /kit/libs_TT.tcl
read_db /baseline/output/cts_checkpoint.odb
source $p/setRC.tcl
source /kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set b [ord::get_db_block]
set db [ord::get_db]
puts "DATABASE_MASTER [[$db findMaster HB4xp67_ASAP7_75t_R] getName]"
set row [lindex [$b getRows] 0]
puts "NATIVE_ROW orient=[$row getOrient] x=[[$row getBBox] xMin] y=[[$row getBBox] yMin]"
foreach master {HB4xp67_ASAP7_75t_R INVx6_ASAP7_75t_R NAND2x2_ASAP7_75t_R} {
 set m [$db findMaster $master];puts "MASTER $master w=[$m getWidth] h=[$m getHeight]"
 foreach p [$m getMTerms] {puts "NATIVE_PIN [$p getName] [$p getIoType] [$p getSigType]"}
}
help report_check_types
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9
report_check_types -min_pulse_width -violators -digits 9
check_placement -verbose
puts "READ_ONLY_API_SMOKE_PASS NO_MUTATION_NO_DB_EXPORT"
