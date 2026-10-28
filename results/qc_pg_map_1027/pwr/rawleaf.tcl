foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
read_db /k/3_place.odb
read_sdc /k/3_place.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set b [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]; set bb [$b getDieArea]
puts "AREA_MM2 [expr {double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$dbu/$dbu/1.e6}] W [expr {([$bb xMax]-[$bb xMin])/$dbu}] H [expr {([$bb yMax]-[$bb yMin])/$dbu}]"
set n 0; set ff 0; foreach i [$b getInsts] { incr n; if {[string match *DFF* [[$i getMaster] getName]]} {incr ff} }; puts "INSTS $n FF $ff"
foreach c [all_clocks] { puts "CLK [get_name $c] [get_property $c period]" }
report_power -digits 6
