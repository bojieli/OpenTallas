# Installed ASAP7 fastroute uses global MAX_ROUTING_LAYER for the clock bound.
# Explicit legal layer sets implement the already-selected M8 clock/M2-M7 data.
set_global_routing_layer_adjustment M2-M7 $::env(ROUTING_LAYER_ADJUSTMENT)
set_routing_layers -clock M7-M8
set_routing_layers -signal M2-M7
