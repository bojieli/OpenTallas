# Invoked on mapped 1_synth.odb before physical placement.
set b [ord::get_db_block]
set flop_count 0
set cell_count 0
set area 0.0
set dbu [$b getDbUnitsPerMicron]
foreach i [$b getInsts] {
 incr cell_count
 set m [$i getMaster]
 set area [expr {$area+[$m getWidth]*double([$m getHeight])/$dbu/$dbu}]
 if {[regexp {^(S?DFF)} [$m getName]]} {incr flop_count}
}
puts "HA2_RELAY_TX_MAPPED_INVENTORY cells=$cell_count flops=$flop_count area_um2=$area expected_flops=2306"
if {$flop_count!=2306} {error "Mapped state differs from modeled full-shape2306: $flop_count"}
if {$area>33748.804224*.55} {error "Mapped area exceeds55percent frame budget"}
puts "HA2_RELAY_TX_MAPPED_INVENTORY_PASS"
