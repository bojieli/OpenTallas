# S81-RCK-BALANCE 11-17 (FABLE-PD-S81-0600, COORD H12): rck clock-tree DEPTH balance, opt-in OT_S81_RCK_BALANCE=1, sourced from
# cts_post.tcl AFTER the clk_leaf_repeat hook and the tap balance.  Post-CTS repeaters (leaf-repeat clkleafrep_*, max-wire wire*)
# made the sparse branches of io_pma_rck[0] up to 390 ps later than the bulk and nothing re-balanced that tree.  Form: the existing
# subtree latency balance (subtree_balance.tcl, top-down: pad the highest node whose whole subtree is early) restricted to the rck
# port, on placement RC, tolerance 20 ps, padded with INVERTER PAIRS (no duty distortion), acceptance = sink insertion span
# <= OT_RCK_BALANCE_SPAN (default 110 ps), reported as OT_STB_SPAN PASS/FAIL.  rck is asynchronous to clk (max-delay crossing),
# so absolute insertion growth is free.  Same ports, flops, logic and cycles: only delaybuf_otstb_* inverters.
# Env: OT_RCK_BALANCE_PORT (default io_pma_rck[0]), OT_RCK_BALANCE_TOL (20), OT_RCK_BALANCE_STAGE (24 = one INVx4 pair),
# OT_RCK_BALANCE_CELL (INVx4_ASAP7_75t_R), OT_RCK_BALANCE_SPAN (110), OT_RCK_BALANCE_FAIL (0 report; 1 stop CTS on FAIL).
proc ot_rck_env {name def} { if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }; return $def }
set ::env(OT_STB_PORTS) [ot_rck_env OT_RCK_BALANCE_PORT {io_pma_rck[0]}]
set ::env(OT_STB_EST) placement
set ::env(OT_STB_TOL) [ot_rck_env OT_RCK_BALANCE_TOL 20]
set ::env(OT_STB_STAGE) [ot_rck_env OT_RCK_BALANCE_STAGE 24]
set ::env(OT_STB_CELL) [ot_rck_env OT_RCK_BALANCE_CELL INVx4_ASAP7_75t_R]
set ::env(OT_STB_PAIR) 1
set ::env(OT_STB_SPAN_MAX) [ot_rck_env OT_RCK_BALANCE_SPAN 110]
set ::env(OT_STB_SPAN_FAIL) [ot_rck_env OT_RCK_BALANCE_FAIL 0]
puts "OT_RCK_BALANCE port $::env(OT_STB_PORTS) tol $::env(OT_STB_TOL) cell $::env(OT_STB_CELL) pair span<=$::env(OT_STB_SPAN_MAX)"
source [file join [file dirname [file normalize [info script]]] subtree_balance.tcl]
