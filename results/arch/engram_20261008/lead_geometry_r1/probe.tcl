read_db /original/3_2_place_iop.odb
source /probe/place.tcl
source /probe/fp_margin_lint.tcl
ot_fp_lint_dump /work/repaired_dump.json
write_db /work/repaired.odb
