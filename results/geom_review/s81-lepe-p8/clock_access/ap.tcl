read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /input/$::env(VIEW).lef
read_def /input/fixture.def
source /input/make_tracks.tcl
set b [ord::get_db_block]
set inst [$b findInst lane]
set it [$inst findITerm {ck[0]}]
if {$it == "NULL" || [$it getNet] == "NULL"} { error "Unconnected clock pin" }
set bb [$inst getBBox]
puts "INSTANCE_BOX [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$inst getOrient] PIN [$it getAvgXY]"
set_routing_layers -signal M2-M8 -clock M2-M8
pin_access
set total 0
foreach ap [$b getAccessPoints] {
 if {[catch {$ap getMPin} mp] || $mp == "NULL"} {continue}
 if {[[$mp getMTerm] getName] ne {ck[0]}} {continue}
 incr total
 if {![catch {$ap getPoint} xy]} {puts "CLOCK_AP $xy"}
}
puts "CLOCK_ACCESS_POINTS $total"
