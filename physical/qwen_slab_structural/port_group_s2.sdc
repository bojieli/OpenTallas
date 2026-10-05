# ot_qwen_slab_port_group with BW_FIFO = 0 (S2: the block-word meso FIFO is its own hardened element at the slab's
# array-facing face, results/uarch/meso_fifo_20261004 meso_d4_v7 CLOSED; this element keeps only the clk datapath).
# Sign-off policy (AGENTS.md): 60 ps setup / 25 ps hold uncertainty, never relaxed.
# Loaded at every ORFS stage (pre-CTS ideal clock): boundary delays referenced to the clock port, as before.
# After CTS the S1 hooks (io_ref.sdc) re-reference them to this block's propagated tree; see README.md.
create_clock -name clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
source [file join [file dirname [info script]] io_plain.sdc]
set_max_fanout 32 [current_design]
set_load 5.55848 [all_outputs]
