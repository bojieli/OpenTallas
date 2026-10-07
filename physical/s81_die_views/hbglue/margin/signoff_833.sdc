# Head-bundle glue, margin-first (owner rule 2026-10-06) SIGN-OFF constraints, read by tools/w18/corner_sta.py
# --post-sdc after the routed 6_final.sdc (routed over-constrained at 770 ps): clock back at 833.333 ps, 60 / 25 ps
# uncertainty, die IO budget. Insertion (measured, Codex flat glue route, SS/FF leaf arrival 134-151 ps): 150 ps.
# Every face is registered (MARGIN=1). Neighbour (die station) clock arrival = insertion +/- 150 ps; wire + station
# clk-q allowance 100 ps on the max side.
#   inputs:  max = ins + 150 + 100 = 400, min = ins - 150 = 0     outputs: max = 100 - (ins - 150) = 100, min = -(ins + 150) = -300
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 400 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 100 -clock core_clk [all_outputs]
set_output_delay -min -300 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_false_path -from [get_ports rst_n]
