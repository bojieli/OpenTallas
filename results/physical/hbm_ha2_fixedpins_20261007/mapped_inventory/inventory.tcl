read_db /r/results/asap7/ha2_owner_banked_h2_fixedpins/base/1_synth.odb
set b [ord::get_db_block];set dbu [$b getDbUnitsPerMicron]
set seq 0;set logic 0;set macros 0;set la 0.0;set ma 0.0
set master_counts {}
foreach i [$b getInsts] {
 set m [$i getMaster];set name [$m getName];dict incr master_counts $name
 set a [expr {[$m getWidth]*double([$m getHeight])/$dbu/$dbu}]
 if {[$m isBlock]} {incr macros;set ma [expr {$ma+$a}]} else {incr logic;set la [expr {$la+$a}]}
 if {[regexp {^(S?DFF)} $name]} {incr seq}
}
puts "H2_MAPPED seq=$seq logic_cells=$logic macros=$macros logic_area_um2=$la macro_area_um2=$ma"
dict for {name count} $master_counts {puts "H2_MASTER $name $count"}
exit
