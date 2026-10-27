# HBM-CORES-R8 2026-10-27 (collar attempt 5) POST_RESIZE hook: wire-length-driven repeater insertion at placement.
# Root cause of attempt-4 max-slew FAIL (32 TT / 25 FF, worst 369 ps vs 320): 8 config-data nets (cd[*] -> INVx1 ->
# placement BUFx3 place25xx at the N edge, y~76) each fan out to 12-13 AO21 A2 payload-word pins spread over x 8-73 /
# y 7-76; routed 158-205 um, ~80 % on resistive M2/M3. GRT-stage repair_design (slew_margin 20) did not see them:
# setRC_rcx.tcl is calibrated on clock nets and under-estimates signal-net C (its own caveat), so GRT-RC slew was
# < 256 ps while routed RCX is 330-369 ps. Fix = split long nets by length (repair_design -max_wire_length), independent
# of the slew estimate. Trial on attempt-4 3_4_place_resized.odb: L=60 um -> 297 nets / 608 buffers, every failing net split.
estimate_parasitics -placement
log_cmd repair_design -max_wire_length $::env(OT_MAX_WIRE_UM) -slew_margin $::env(SLEW_MARGIN) -verbose
puts "OT_MAX_WIRE repair_design max_wire_length $::env(OT_MAX_WIRE_UM) insts [sta::network_leaf_instance_count]"
