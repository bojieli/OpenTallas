# m2 (18:50 PT): IO constraints follow the MEASURED CTS insertion of bf_m1 (SS 847-1216 mid 1032, FF 457-656 mid 556; CTS-only calibration /tmp/measure_ins.sh)
# Native BF pair (PINREG=1), margin-first (owner rule 2026-10-06) SIGN-OFF constraints, read by tools/w18/corner_sta.py
# --post-sdc after the routed 6_final.sdc (routed over-constrained at 770 ps): clock back at 833.333 ps, 60 / 25 ps
# uncertainty, die IO budget. Insertion assumed 150 ps (glue-class tree); re-checked against the routed insertion at harvest.
# Every pin is a flop (PINREG=1). Neighbour (die station) clock arrival = insertion +/- 150 ps; wire + station
# clk-q allowance 100 ps on the max side.
#   inputs:  max = ins + 150 + 100 = 400, min = ins - 150 = 0     outputs: max = 100 - (ins - 150) = 100, min = -(ins + 150) = -300
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 1282 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 506 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max -782 -clock core_clk [all_outputs]
set_output_delay -min -606 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_false_path -from [get_ports rst_n]
# Physical PP ROM read/capture: alternate banks, capture two edges after read (as routed).
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
# hold IO per owner clarification (FF insertion ~175 ps as measured on the glue, 50 ps hold IO): in min 125, out min -225
