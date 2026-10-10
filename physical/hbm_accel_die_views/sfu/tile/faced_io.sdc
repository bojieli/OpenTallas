# fill-8 2026-10-10: hfd_sfu_tile IO phases (faced tile, tools/hbm_hub_quarter_gen.py emit_tile_faced).  Every input pin
# (bc_in, acc_in) is driven by the abutting peer tile's NEGEDGE face lockup across the 0.54 um gap and captured by this
# tile's posedge pin flop: a real half-cycle path, so the inputs launch on the FALLING edge.  Every output (bc_out,
# acc_out) leaves this tile's negedge lockup (the launch edge comes from the netlist) for the peer's posedge pin flop.
# Budgets unchanged at 0.2 T (166.6 ps) max / 25 ps min, 60 / 25 ps uncertainty; no IO false path.
set fi_c [get_clocks core_clk]
set fi_in [delete_from_list [all_inputs] [get_ports clk]]
set_input_delay -max 166.6 -clock $fi_c -clock_fall $fi_in
set_input_delay -min 25 -clock $fi_c -clock_fall $fi_in
set_output_delay -max 166.6 -clock $fi_c [all_outputs]
set_output_delay -min -25 -clock $fi_c [all_outputs]
