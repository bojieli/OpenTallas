# ot_qwen_slab_port_group with BW_FIFO = 0 (S2: the block-word meso FIFO is its own hardened element at the slab's
# array-facing face, results/uarch/meso_fifo_20261004 meso_d4_v7 CLOSED; this element keeps only the clk datapath).
# Sign-off policy (AGENTS.md): 60 ps setup / 25 ps hold uncertainty, never relaxed.
# Loaded at every ORFS stage (pre-CTS ideal clock): boundary delays referenced to the clock port, as before.
# After CTS the S1 hooks (io_ref.sdc) re-reference them to this block's propagated tree; see README.md.
create_clock -name clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Same lines as io_plain.sdc, inlined: ORFS copies this SDC into results/, so a relative `source` cannot resolve.
set_input_delay 166.667 -clock clk [get_ports {rst_n p_* res_in*}]
set_output_delay 166.667 -clock clk [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
set_max_fanout 32 [current_design]
set_load 5.55848 [all_outputs]
# r10 slew class (r6d 120 / r6a 83 / r9b 25 pins over the 320 ps liberty limit; --max-transition-ns never reached this
# custom SDC_FILE): an explicit, stricter max transition makes repair_design buffer to it (library unit ps)
set_max_transition 270 [current_design]
