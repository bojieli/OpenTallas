# POST_GLOBAL_ROUTE, chained by grt_macro_top_layer.tcl: GRT ran to MAX_ROUTING_LAYER+1 (zero capacity there); put the
# block's max signal / clock routing layer back to MAX_ROUTING_LAYER before 5_1_grt.odb is written, because ORFS
# detail_route has no -top_routing_layer and DRT routes up to the block's max routing layer (hgi_topk_heap_rt_m5-h3m5-
# 6d8d554ba: 190 um of M6 under an M5 cap).  Then source whatever POST_GLOBAL_ROUTE hook the flow had set.
set ot_gmlp_b [ord::get_db_block]
$ot_gmlp_b setMaxRoutingLayer $::ot_gml_max_level
if {[$ot_gmlp_b getMaxLayerForClock] > $::ot_gml_max_level} { $ot_gmlp_b setMaxLayerForClock $::ot_gml_max_level }
puts "OT_GRT_TOP_SHADOW: block max routing layer restored to $::env(MAX_ROUTING_LAYER) (level $::ot_gml_max_level) for detailed routing"
if {$::ot_gml_post_chain ne ""} { source $::ot_gml_post_chain }
