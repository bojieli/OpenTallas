read_db /in/run/results/asap7/dp_slw_hc0__cl1bc59e1c/base/3_place.odb
set b [ord::get_db_block];set du [$b getDbUnitsPerMicron]
set cells 0;set ff 0;set fa 0;set ca 0;set stat {}
foreach i [$b getInsts] {
 if {![string match "u_bound.u_cland_rsf_i/*" [$i getName]]} continue
 set m [$i getMaster];set area [expr {[$m getWidth]*[$m getHeight]/double($du*$du)}]
 incr cells;dict incr stat [$i getPlacementStatus]
 if {[string match "DFF*" [$m getName]]} {incr ff;set fa [expr {$fa+$area}]} else {set ca [expr {$ca+$area}]}
}
puts "RSF_AREA cells=$cells ff=$ff ff_area_um2=$fa other_area_um2=$ca total_area_um2=[expr {$fa+$ca}] status=$stat"
set pins {};set names {}
foreach bt [$b getBTerms] {
 if {![string match "rsf_i*" [$bt getName]]} continue
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {dict incr pins [[$box getTechLayer] getName]}}
 lappend names [$bt getName]
}
puts "RSF_PINS count=[llength $names] by_layer=$pins"
set tech [[ord::get_db] getTech]
foreach layer {M3 M5 M7} {set l [$tech findLayer $layer];puts "RSF_TRACK $layer pitch_um=[expr {[$l getPitchX]/double($du)}]"}
