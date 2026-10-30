# Full-signal structural alternative to single-net reroute: exact same C1 clock wires, new M6 stub exclusion.
proc isclk {n} {set nm [$n getName];return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}]}
set b [ord::get_db_block];set ns 0;set nc 0
foreach n [$b getNets] {
 if {[$n isSpecial]} continue
 if {[isclk $n]} {incr nc;continue}
 set w [$n getWire];if {$w ne "NULL" && $w ne ""} {odb::dbWire_destroy $w;incr ns};$n clearGuides
}
puts "C1FULL signal_wires_destroyed $ns clock_preserved $nc"
set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) $::env(ROUTING_LAYER_ADJUSTMENT)
set_routing_layers -clock $::env(MIN_CLK_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
global_route -congestion_iterations 30 -allow_congestion
write_guides /eco/full.guide
set ::env(OT_F4G_G1) /eco/full.guide
source /work/f4g_pre_drt_sig.tcl
set b [ord::get_db_block]
set m6 [[[ord::get_db] getTech] findLayer M6]
odb::dbObstruction_create $b $m6 123932 11264 124972 11296
$b setMaxRoutingLayer [$m6 getRoutingLevel]
puts "C1FULL exact_M6_stub_exclusion [list 123932 11264 124972 11296]"
