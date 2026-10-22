read_db /work/input_f.odb
foreach bt [[ord::get_db_block] getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }
source /src/io_f.tcl
source /src/fp_margin_lint.tcl
ot_fp_lint_dump /work/corrected_f.json
write_db /work/corrected_f.odb
exit
