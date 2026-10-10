read_db /evidence/6_final.odb
foreach inst [[ord::get_db_block] getInsts] {if {[string match cap* [$inst getName]]} {$inst setPlacementStatus PLACED}}
source /src/physical/dsrom_markov_lookup_localcapture/capture_anchor.tcl
puts OT_PG_VDD_BEGIN
check_power_grid -net VDD
puts OT_PG_VDD_PASS
puts OT_PG_VSS_BEGIN
check_power_grid -net VSS
puts OT_PG_VSS_PASS
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump /receipt/fp_dump.json
write_db /receipt/corrected.odb
set ::env(OT_PG_ODB) /receipt/corrected.odb
set ::env(OT_PG_DIAG) /receipt/rows_pins_rails.log
source /src/tools/dsrom_markov_lookup_pg_diag.tcl
