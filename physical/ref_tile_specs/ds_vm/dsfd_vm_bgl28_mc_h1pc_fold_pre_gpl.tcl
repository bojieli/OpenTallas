# Retain actual recipe hold stages and native x1 QN FFs.
source /src/physical/ref_tile_specs/ds_vm/dsfd_vm_bgl28_mc_pre_gpl.tcl
set fold_master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
if {$fold_master eq "NULL"} {error "BGL_OUTPUT_FOLD missing real final24 master"}
set fold_count 0
foreach i [[ord::get_db_block] getInsts] {
 if {![string match ot_ohdrv_*_2 [$i getName]]} {continue}
 if {![$i swapMaster $fold_master]} {error "BGL_OUTPUT_FOLD failed swap [$i getName]"}
 set net [[$i findITerm Y] getNet]
 if {[llength [$net getBTerms]] != 1} {error "BGL_OUTPUT_FOLD final stage not directly on one output"}
 # Protect the explicit final driver topology; timing checks retain actual loads.
 $net setDoNotTouch 1
 incr fold_count
}
set_dont_touch [get_cells ot_ohdrv_*_2]
if {$fold_count != 5441} {error "BGL_OUTPUT_FOLD expected5441 actual output drivers found$fold_count"}
puts "BGL_OUTPUT_FOLD actual single final BUFx24 drivers=$fold_count; all HB4/input stages retained"
