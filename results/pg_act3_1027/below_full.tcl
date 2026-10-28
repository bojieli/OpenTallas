foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
read_db /old/run/results/asap7/dp_coll_ftm/base/6_final.odb
read_sdc /old/run/results/asap7/dp_coll_ftm/base/6_final.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bb [$b getDieArea]
set ar [expr {double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$dbu/$dbu/1.e6}]
set target [expr {$ar*0.5823}]
set area 0.0
set cells {}
foreach i [$b getInsts] {
 set m [$i getMaster];set ty [$m getType]
 if {![string match CORE* $ty] || $ty in {CORE_SPACER CORE_WELLTAP CORE_ANTENNACELL}} {continue}
 set a [expr {double([$m getWidth])*[$m getHeight]}]
 lappend cells [list [$i getName] $a]
 set area [expr {$area+$a}]
}
foreach z $cells {lassign $z n a;set_pdnsim_inst_power -inst $n -power [expr {$target*$a/$area}]}
puts "QC_BELOW_LOAD area_mm2=$ar target_w=$target cells=[llength $cells] density=0.5823W/mm2 normalized_by_cell_area"
foreach nn $::env(PGA3_NETS) {
 check_power_grid -net $nn
 analyze_power_grid -net $nn -source_type FULL -voltage_file /p/ir_$nn.csv -error_file /p/err_$nn.rpt
 puts "QC_BELOW_DONE $nn"
}
exit
