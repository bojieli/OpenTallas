# Hardened one-head leaf ot_attn_hgrp_m6h1 for the strip tile: every signal pin (inputs, outputs, clk, rst_n) on the
# top edge, so a row of leaves (R0) and the mirrored row above it (MX) face one register strip.
set ot_all {}
foreach ot_p [get_ports *] { lappend ot_all [get_full_name $ot_p] }
set ot_die [ord::get_die_area]
puts "OT_LEAF_IO_TOP pins=[llength $ot_all] die=$ot_die"
set_io_pin_constraint -pin_names $ot_all -region top:*
