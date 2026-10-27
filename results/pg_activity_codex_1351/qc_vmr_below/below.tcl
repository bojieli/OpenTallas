foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /macros/*_tt.lib] {read_liberty $f}
read_db /old/6_final.odb
read_sdc /old/6_final.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bb [$b getDieArea]
set ar [expr {double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$dbu/$dbu/1.e6}]
set target [expr {$ar*0.5823}]
set area 0.0;set cells {};set macros 0
foreach i [$b getInsts] {
 set m [$i getMaster];set ty [$m getType]
 if {(![string match CORE* $ty] && ![string match BLOCK* $ty]) || $ty in {CORE_SPACER CORE_WELLTAP CORE_ANTENNACELL}} {continue}
 if {[string match BLOCK* $ty]} {incr macros}
 set a [expr {double([$m getWidth])*[$m getHeight]}]
 lappend cells [list [$i getName] $a];set area [expr {$area+$a}]
}
foreach z $cells {lassign $z n a;set_pdnsim_inst_power -inst $n -power [expr {$target*$a/$area}]}
puts "QC_BELOW_LOAD area_mm2=$ar target_w=$target cells=[llength $cells] macros=$macros density=0.5823W/mm2 normalized_by_functional_cell_macro_area"
array set cnt {}
foreach nn {VDD VSS} {foreach sw [[$b findNet $nn] getSWires] {foreach s [$sw getWires] {if {![$s isVia]} {set ly [[$s getTechLayer] getName];if {![info exists cnt($ly)]} {set cnt($ly) 0};incr cnt($ly)}}}}
puts "QC_PG_LAYER_SHAPES [array get cnt]"
foreach nn {VDD VSS} {
 check_power_grid -net $nn
 analyze_power_grid -net $nn -source_type STRAPS -voltage_file /out/ir_$nn.csv -error_file /out/err_$nn.rpt
 puts "QC_BELOW_DONE $nn"
}
exit
