read_db /work/input_e.odb
foreach bt [[ord::get_db_block] getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }
source /src/io_e.tcl
source /src/fp_margin_lint.tcl
ot_fp_lint_dump /work/corrected_e.json
write_db /work/corrected_e.odb
exit
