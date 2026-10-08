# H16 quad parent IO budget (OWNER RULE 2026-10-06 ADDENDUM), referenced to a quad clk pin so it holds at every stage:
#   inputs  : captured by the ROOT bank at ~ qclk + DIN (DIN: parent register latency over the quad pin; CTS aligns the
#             parent tree to the quad's input strip, quad_cts view) -> max DIN + 300 (150 ps die clock-arrival
#             difference + 150 ps to the nearest station), min DIN - 150;
#   outputs : launched by the quad's leaf output flops at qclk + QINS (the quad ETM's max_clock_tree_path) -> the die
#             captures at QINS +/- 150: max 300 - QINS, min -(QINS - 150).
# DIN / QINS here are the route-time estimates; the sign-off SDC (route_p19.sh) re-states them from the routed tile.
set ot_din 260
set ot_qins 682
set ot_qclk [lindex [get_pins -of_objects [get_cells -hierarchical -filter "ref_name == ot_attn_tile_m6h1q"] -filter "lib_pin_name == clk"] 0]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay -max [expr {$ot_din + 300}] -clock core_clk -reference_pin $ot_qclk $ot_in
set_input_delay -min [expr {$ot_din - 150}] -clock core_clk -reference_pin $ot_qclk $ot_in
set_output_delay -max [expr {300 - $ot_qins}] -clock core_clk -reference_pin $ot_qclk [all_outputs]
set_output_delay -min [expr {-($ot_qins - 150)}] -clock core_clk -reference_pin $ot_qclk [all_outputs]
