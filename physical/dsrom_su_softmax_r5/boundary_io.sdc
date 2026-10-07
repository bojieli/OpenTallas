# su_softmax round 5 die-boundary IO (owner margin-first addendum + clarification 2026-10-06), time unit ps.
# Every port is pin-direct to a flop.  IO delays are referenced to io_clk, a generated copy of core_clk at an
# input-capture flop's CLK pin: with a propagated clock its edge arrives at that flop's own insertion, so the same
# SDC holds at SS (setup) and FF (hold) with the block's measured insertion at each corner:
#   setup: the far clock may differ by 150 ps (a different clock region), clk->q 50, wire allowance 100 ps
#   hold : 50 ps hold IO uncertainty, clk->q 20 / hold 10, no wire
set rp [get_pins {u_sid.genblk1.g_one.line[0]$_DFF_P_/CLK}]
create_generated_clock -name io_clk -source [get_ports clk] -divide_by 1 $rp
set ins {}
foreach p [all_inputs -no_clocks] { if {[get_name $p] ne "rst_n"} { lappend ins $p } }
set_input_delay -max 300 -clock io_clk $ins
set_input_delay -min -30 -clock io_clk $ins
set_output_delay -max 280 -clock io_clk [all_outputs]
set_output_delay -min -60 -clock io_clk [all_outputs]
