# GENERATED-COPY of tools/die_plan/cons_grt_pre.tcl (PRE_GLOBAL_ROUTE hook of OT_CONS_KIT=1 kits whose own pins sit
# above OT_CONS_MAX_LAYER, KW-FIX-24/CONSKIT 11-06): signals are kept at or below OT_CONS_SIGNAL_MAX.  The pin layers
# above it (OT_CONS_PIN_LAYERS) stay inside MAX_ROUTING_LAYER, because GRT stops on a pin with no geometry below the
# max routing layer, and get set_global_routing_layer_adjustment OT_CONS_PIN_LAYER_ADJ: GRT keeps only that share of
# their tracks, enough for the via stack down from each pin, so nets route on the layers <= OT_CONS_SIGNAL_MAX.
# The kit's standard hook (OT_CONS_BASE_PRE_GRT, normally hold_repair_pre.tcl -> grt_pre.tcl -> grt_layers.tcl sync)
# runs first, so the adjustment is the last layer command before global_route.
set cgr_base $::env(OT_CONS_BASE_PRE_GRT)
if {$cgr_base ne ""} { source $cgr_base }
foreach cgr_ln $::env(OT_CONS_PIN_LAYERS) {
  set_global_routing_layer_adjustment $cgr_ln $::env(OT_CONS_PIN_LAYER_ADJ)
}
puts "OT_CONS_KIT signals <= $::env(OT_CONS_SIGNAL_MAX); pin-access layers $::env(OT_CONS_PIN_LAYERS) adjustment $::env(OT_CONS_PIN_LAYER_ADJ) (max routing layer $::env(MAX_ROUTING_LAYER))"
