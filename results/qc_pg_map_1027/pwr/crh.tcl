foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
read_db /k/6_final.odb
read_sdc /k/6_final.sdc
read_spef /k/6_final.spef
set_propagated_clock [all_clocks]
set b [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]; set bb [$b getDieArea]
puts "AREA_MM2 [expr {double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$dbu/$dbu/1.e6}] W [expr {([$bb xMax]-[$bb xMin])/$dbu}] H [expr {([$bb yMax]-[$bb yMin])/$dbu}]"
foreach c [all_clocks] { puts "CLK [get_name $c] [get_property $c period]" }
report_power -digits 6
