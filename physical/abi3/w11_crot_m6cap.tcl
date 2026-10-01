# W11 C_rotate: global-routing layer plan for a VM-strip slice routed M2-M6 under W18b's die check
# (claude/w18-die-assembly d59e7f8d hub_square.json rotate_on_m6_die_check): the die routes with 0 overflow only if the
# rotate takes <= 75 % of the M6 tracks over the bank square.  ORFS's asap7 default reserves ROUTING_LAYER_ADJUSTMENT
# (0.25) of every layer; M6 is additionally capped so global routing may use at most 75 % x (1 - 0.25) of M6's tracks:
# adjustment 1 - 0.75 x 0.75 = 0.4375.  Selected with --orfs-var FASTROUTE_TCL=/src/physical/abi3/w11_crot_m6cap.tcl.
set_global_routing_layer_adjustment \
  $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) \
  $::env(ROUTING_LAYER_ADJUSTMENT)
set_global_routing_layer_adjustment M6 [expr {1.0 - 0.75 * (1.0 - $::env(ROUTING_LAYER_ADJUSTMENT))}]
set_routing_layers -clock $::env(MIN_CLK_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
