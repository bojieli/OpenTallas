# DS-ROM field spine v13 (margin-first, owner rule 2026-10-06) SIGN-OFF constraints for the R = 128 screen, read by
# tools/w18/corner_sta.py --post-sdc after the routed 6_final.sdc (routed over-constrained at 770 ps): the clock back
# at 833.333 ps with 60 / 25 ps uncertainty, and the die-integration IO budget.  Block insertion (measured, v11 routed
# R = 128, SS): 850 ps.  Every port is registered at the block boundary (screen wrapper), so the IO paths are pin-to-flop
# and flop-to-pin wire only.  Neighbour (die station) clock arrival: insertion +/- 150 ps; wire + station clk-q
# allowance 100 ps on the max side.
#   inputs:  max = ins + 150 + 100, min = ins - 150      outputs: max = 100 - (ins - 150), min = -(ins + 150)
# rst_n is false-pathed (the die distributes a synchronised reset on its own tree; recovery is not a datapath)
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 700 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max -600 -clock core_clk [all_outputs]
set_output_delay -min -1000 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_false_path -from [get_ports rst_n]
