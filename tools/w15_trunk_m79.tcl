# W15 thick-metal trunk measurement (FASTROUTE_TCL): signal routing on M2-M9 so cell pins and short local
# nets keep M1-M6 access, but global routing capacity below M7 is reserved to 5% (adjustment 0.95), so the
# long register-to-register trunk wires are routed on M7-M9.
set_global_routing_layer_adjustment M2-M6 0.95
set_global_routing_layer_adjustment M7-M9 0.0
set_routing_layers -signal M2-M9
