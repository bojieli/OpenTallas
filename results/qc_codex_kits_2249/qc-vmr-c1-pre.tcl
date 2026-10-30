# Exact existing C1 non-tree M6 stub; reroute only its data net, preserving every clock and other signal wire.
set b [ord::get_db_block]
set bad {wb_d\[1\]\[106\]}
set n [$b findNet $bad]
if {$n eq "NULL"} {error "C1 stub net not found"}
odb::dbWire_destroy [$n getWire]
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
global_route -congestion_iterations 30 -allow_congestion
foreach n [$b getNets] {if {[$n isSpecial]} continue;if {[$n getName] ne $bad} {$n clearGuides}}
set_routing_layers -signal M2-M6
set m6 [[[ord::get_db] getTech] findLayer M6]
set f [open /work/m6_strip_f4g.txt]
while {[gets $f line]>=0} {lassign $line a c d e;odb::dbObstruction_create $b $m6 $a $c $d $e}
close $f
# Exact M6 shape exclusion (no extra bloat over neighbouring fixed clock metal).
odb::dbObstruction_create $b $m6 123932 11264 124972 11296
set f [open /eco/stub.guide w];set count 0
foreach n [$b getNets] {
 set gs [$n getGuides];if {![llength $gs]} continue
 puts $f [$n getName];puts $f "("
 foreach g $gs {set r [$g getBox];puts $f "[$r xMin] [$r yMin] [$r xMax] [$r yMax] [[$g getLayer] getName]"}
 puts $f ")";$n clearGuides;incr count
}
close $f;read_guides /eco/stub.guide
puts "C1_STUB guided_nets $count expected1"
if {$count!=1} {error "C1 stub expected one data net"}
