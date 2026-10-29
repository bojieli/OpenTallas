# geom_grt.tcl (GEOM-AUTO-2 2026-10-27): short read-only global-route probe of a placed checkpoint for AUTO-GEOM.
# Deck after the GEOM-REVIEW-25 probes (intel2 geom25/probe.tcl): clock nets excluded (special), signal layers
# M2..MAX_ROUTING_LAYER of the kit, the kit/platform layer adjustment (flow GRT, not the 0.5 review deck), 50 congestion iterations (owner rule: judge GRT only at
# >= 50 iterations), congestion report for the AUTO-GEOM image.  Nothing is written back to the ODB.
#   env: OT_GRT_ODB, OT_GRT_MAX (default M5), OT_GRT_MIN (M2), OT_GRT_ADJ (0.25 = ORFS asap7 default), OT_GRT_ITER (50), OT_GRT_RPT
read_db $::env(OT_GRT_ODB)
check_placement -verbose
set b [ord::get_db_block]
foreach n [$b getNets] { if {[$n getSigType] eq "CLOCK"} { $n setSpecial } }
foreach nm {clk ck tile_clk} { set n [$b findNet $nm]; if {$n ne "NULL"} { $n setSpecial } }
set lo [expr {[info exists ::env(OT_GRT_MIN)] ? $::env(OT_GRT_MIN) : "M2"}]
set hi [expr {[info exists ::env(OT_GRT_MAX)] ? $::env(OT_GRT_MAX) : "M5"}]
set adj [expr {[info exists ::env(OT_GRT_ADJ)] ? $::env(OT_GRT_ADJ) : 0.25}]
set it [expr {[info exists ::env(OT_GRT_ITER)] ? $::env(OT_GRT_ITER) : 50}]
puts "OT_GRT_DECK layers $lo-$hi adjustment $adj iterations $it"
set_routing_layers -signal $lo-$hi
set_global_routing_layer_adjustment $lo-$hi $adj
global_route -congestion_iterations $it -congestion_report_file $::env(OT_GRT_RPT) -allow_congestion -verbose
puts "OT_GRT_DONE"

write_guides /work/spread.guide
write_db /work/spread_grt.odb
