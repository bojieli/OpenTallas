# Selected Qwen die boundary: one 430.56 um hop plus receiver pin.
# This is sourced only by CORE_DIE_IO=1 successor routes. Historical recipes
# and their pinned files retain their original IO loading.
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
# REDESIGN-BATCH 2026-10-08: u_me.clk is the gated engine clock (ICG -> ME spine; a CLOCK net after CTS), not a die-link
# data port.  io_plain / io_ref_skew already leave it out of the boundary delays, but run_abi3's constraint.sdc (0.2 T on
# every output) and the link-budget hook (virtual-clock output max) still timed it as data: core_kv_banked -tt TT -410.8
# was exactly clk -> u_me.clk against ot_lb_v_core_clk (every reg/in path >= +60).  Its timing is the parent's clock skew.
if {[llength [get_ports -quiet {u_me.clk}]]} { set_false_path -to [get_ports {u_me.clk}] }
