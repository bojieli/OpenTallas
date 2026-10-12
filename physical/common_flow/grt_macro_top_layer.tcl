# PRE_GLOBAL_ROUTE (ref_tile, every kit): give GRT the real capacity of the top routing layer over hard macros.
#
# Measured 2026-10-12 on hrow5_cbw-r5b (5_1_grt-failed.odb, 4 x ot_sram_1r1w_1024x256, LEF OBS M1-M4 only, nothing on
# M5): with MAX_ROUTING_LAYER = M5 FastRoute gives M5 ZERO capacity over every macro (M5 resource 1,363,974; 17 M5
# segments over the west SRAMs, 9,909 cap-0 vertical markers, GRT-0116).  The same db routed M2-M6 has M5 resource
# 1,898,235 (+534k = exactly the macro area) and 0 overflow.  The SRAM really leaves M5 free, so under the M5 tile cap
# every macro became a full routing wall in GRT only (ot_hgi_seq v2.4 failed the same way).
# Fix: route GRT to MAX+1 with that extra layer at 100% adjustment (zero capacity: no wire, no guide on it -- checked:
# M6 demand 0) so MAX keeps its real capacity over the macros.  Detailed routing still stops at MAX_ROUTING_LAYER
# (ORFS detail_route -top_routing_layer), so the tile's layer cap and child_lint (c) are unchanged.
# No-op without hard macros, or when MAX is the top routing layer of the tech.
set ot_gml_tech [ord::get_db_tech]
set ot_gml_max [$ot_gml_tech findLayer $::env(MAX_ROUTING_LAYER)]
set ot_gml_n 0
foreach ot_gml_i [[ord::get_db_block] getInsts] { if {[[$ot_gml_i getMaster] isBlock]} { incr ot_gml_n } }
set ot_gml_up ""
if {$ot_gml_max ne "NULL"} {
  set ot_gml_l [$ot_gml_tech findRoutingLayer [expr {[$ot_gml_max getRoutingLevel] + 1}]]
  if {$ot_gml_l ne "NULL"} { set ot_gml_up [$ot_gml_l getName] }
}
if {$ot_gml_n > 0 && $ot_gml_up ne "" && ![info exists ::env(OT_GRT_NO_TOP_SHADOW)]} {
  set ot_gml_clo [expr {[info exists ::env(MIN_CLK_ROUTING_LAYER)] ? $::env(MIN_CLK_ROUTING_LAYER) : $::env(MIN_ROUTING_LAYER)}]
  set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$ot_gml_up
  set_routing_layers -clock $ot_gml_clo-$ot_gml_up
  set_global_routing_layer_adjustment $ot_gml_up 1.0
  puts "OT_GRT_TOP_SHADOW: $ot_gml_n macros; GRT layers $::env(MIN_ROUTING_LAYER)-$ot_gml_up with $ot_gml_up at zero capacity (detailed route stays <= $::env(MAX_ROUTING_LAYER))"
} else {
  puts "OT_GRT_TOP_SHADOW: skipped (macros $ot_gml_n, layer above $::env(MAX_ROUTING_LAYER) '$ot_gml_up')"
}
