###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_dsrom_markov_row
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 770.0000 [get_ports {clk}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
create_clock -name ot_lb_v_core_clk -period 770.0000 
set_clock_uncertainty -setup 60.0000 ot_lb_v_core_clk
set_clock_latency 629.4100 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[0]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[0]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[100]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[100]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[100]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[100]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[101]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[101]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[101]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[101]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[102]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[102]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[102]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[102]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[103]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[103]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[103]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[103]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[104]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[104]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[104]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[104]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[105]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[105]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[105]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[105]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[106]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[106]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[106]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[106]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[107]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[107]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[107]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[107]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[108]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[108]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[108]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[108]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[109]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[109]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[109]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[109]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[10]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[10]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[110]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[110]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[110]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[110]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[111]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[111]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[111]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[111]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[112]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[112]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[112]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[112]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[113]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[113]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[113]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[113]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[114]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[114]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[114]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[114]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[115]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[115]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[115]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[115]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[116]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[116]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[116]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[116]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[117]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[117]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[117]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[117]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[118]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[118]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[118]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[118]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[119]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[119]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[119]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[119]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[11]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[11]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[120]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[120]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[120]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[120]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[121]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[121]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[121]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[121]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[122]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[122]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[122]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[122]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[123]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[123]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[123]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[123]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[124]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[124]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[124]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[124]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[125]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[125]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[125]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[125]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[126]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[126]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[126]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[126]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[127]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[127]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[127]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[127]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[128]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[128]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[128]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[128]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[129]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[129]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[129]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[129]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[12]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[12]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[130]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[130]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[130]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[130]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[131]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[131]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[131]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[131]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[132]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[132]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[132]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[132]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[133]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[133]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[133]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[133]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[134]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[134]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[134]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[134]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[135]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[135]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[135]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[135]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[136]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[136]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[136]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[136]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[137]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[137]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[137]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[137]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[138]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[138]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[138]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[138]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[139]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[139]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[139]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[139]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[13]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[13]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[140]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[140]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[140]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[140]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[141]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[141]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[141]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[141]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[142]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[142]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[142]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[142]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[143]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[143]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[143]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[143]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[144]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[144]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[144]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[144]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[145]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[145]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[145]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[145]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[146]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[146]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[146]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[146]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[147]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[147]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[147]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[147]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[148]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[148]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[148]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[148]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[149]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[149]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[149]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[149]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[14]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[14]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[150]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[150]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[150]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[150]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[151]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[151]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[151]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[151]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[152]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[152]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[152]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[152]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[153]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[153]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[153]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[153]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[154]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[154]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[154]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[154]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[155]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[155]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[155]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[155]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[156]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[156]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[156]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[156]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[157]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[157]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[157]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[157]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[158]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[158]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[158]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[158]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[159]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[159]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[159]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[159]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[15]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[15]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[160]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[160]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[160]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[160]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[161]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[161]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[161]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[161]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[162]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[162]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[162]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[162]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[163]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[163]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[163]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[163]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[164]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[164]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[164]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[164]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[165]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[165]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[165]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[165]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[166]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[166]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[166]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[166]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[167]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[167]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[167]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[167]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[168]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[168]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[168]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[168]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[169]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[169]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[169]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[169]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[16]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[16]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[170]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[170]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[170]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[170]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[171]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[171]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[171]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[171]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[172]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[172]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[172]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[172]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[173]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[173]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[173]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[173]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[174]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[174]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[174]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[174]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[175]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[175]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[175]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[175]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[176]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[176]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[176]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[176]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[177]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[177]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[177]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[177]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[178]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[178]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[178]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[178]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[179]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[179]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[179]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[179]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[17]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[17]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[180]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[180]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[180]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[180]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[181]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[181]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[181]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[181]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[182]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[182]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[182]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[182]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[183]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[183]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[183]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[183]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[184]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[184]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[184]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[184]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[185]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[185]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[185]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[185]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[186]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[186]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[186]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[186]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[187]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[187]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[187]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[187]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[188]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[188]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[188]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[188]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[189]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[189]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[189]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[189]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[18]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[18]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[190]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[190]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[190]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[190]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[191]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[191]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[191]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[191]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[192]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[192]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[192]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[192]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[193]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[193]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[193]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[193]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[194]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[194]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[194]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[194]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[195]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[195]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[195]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[195]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[196]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[196]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[196]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[196]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[197]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[197]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[197]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[197]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[198]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[198]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[198]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[198]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[199]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[199]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[199]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[199]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[19]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[19]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[1]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[1]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[200]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[200]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[200]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[200]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[201]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[201]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[201]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[201]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[202]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[202]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[202]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[202]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[203]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[203]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[203]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[203]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[204]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[204]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[204]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[204]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[205]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[205]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[205]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[205]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[206]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[206]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[206]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[206]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[207]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[207]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[207]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[207]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[208]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[208]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[208]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[208]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[209]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[209]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[209]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[209]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[20]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[20]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[210]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[210]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[210]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[210]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[211]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[211]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[211]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[211]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[212]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[212]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[212]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[212]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[213]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[213]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[213]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[213]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[214]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[214]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[214]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[214]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[215]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[215]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[215]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[215]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[216]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[216]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[216]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[216]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[217]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[217]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[217]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[217]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[218]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[218]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[218]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[218]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[219]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[219]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[219]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[219]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[21]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[21]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[220]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[220]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[220]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[220]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[221]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[221]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[221]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[221]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[222]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[222]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[222]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[222]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[223]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[223]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[223]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[223]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[224]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[224]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[224]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[224]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[225]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[225]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[225]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[225]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[226]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[226]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[226]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[226]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[227]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[227]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[227]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[227]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[228]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[228]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[228]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[228]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[229]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[229]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[229]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[229]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[22]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[22]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[230]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[230]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[230]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[230]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[231]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[231]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[231]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[231]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[232]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[232]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[232]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[232]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[233]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[233]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[233]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[233]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[234]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[234]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[234]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[234]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[235]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[235]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[235]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[235]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[236]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[236]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[236]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[236]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[237]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[237]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[237]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[237]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[238]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[238]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[238]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[238]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[239]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[239]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[239]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[239]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[23]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[23]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[240]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[240]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[240]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[240]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[241]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[241]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[241]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[241]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[242]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[242]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[242]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[242]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[243]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[243]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[243]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[243]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[244]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[244]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[244]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[244]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[245]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[245]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[245]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[245]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[246]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[246]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[246]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[246]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[247]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[247]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[247]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[247]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[248]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[248]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[248]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[248]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[249]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[249]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[249]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[249]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[24]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[24]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[250]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[250]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[250]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[250]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[251]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[251]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[251]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[251]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[252]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[252]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[252]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[252]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[253]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[253]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[253]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[253]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[254]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[254]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[254]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[254]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[255]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[255]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[255]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[255]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[25]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[25]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[26]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[26]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[27]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[27]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[28]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[28]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[29]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[29]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[2]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[2]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[30]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[30]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[31]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[31]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[32]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[32]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[32]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[32]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[33]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[33]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[33]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[33]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[34]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[34]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[34]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[34]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[35]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[35]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[35]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[35]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[36]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[36]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[36]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[36]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[37]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[37]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[37]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[37]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[38]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[38]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[38]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[38]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[39]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[39]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[39]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[39]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[3]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[3]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[40]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[40]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[40]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[40]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[41]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[41]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[41]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[41]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[42]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[42]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[42]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[42]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[43]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[43]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[43]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[43]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[44]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[44]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[44]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[44]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[45]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[45]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[45]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[45]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[46]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[46]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[46]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[46]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[47]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[47]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[47]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[47]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[48]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[48]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[48]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[48]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[49]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[49]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[49]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[49]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[4]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[4]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[50]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[50]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[50]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[50]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[51]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[51]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[51]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[51]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[52]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[52]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[52]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[52]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[53]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[53]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[53]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[53]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[54]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[54]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[54]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[54]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[55]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[55]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[55]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[55]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[56]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[56]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[56]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[56]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[57]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[57]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[57]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[57]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[58]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[58]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[58]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[58]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[59]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[59]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[59]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[59]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[5]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[5]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[60]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[60]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[60]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[60]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[61]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[61]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[61]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[61]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[62]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[62]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[62]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[62]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[63]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[63]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[63]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[63]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[64]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[64]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[64]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[64]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[65]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[65]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[65]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[65]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[66]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[66]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[66]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[66]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[67]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[67]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[67]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[67]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[68]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[68]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[68]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[68]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[69]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[69]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[69]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[69]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[6]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[6]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[70]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[70]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[70]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[70]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[71]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[71]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[71]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[71]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[72]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[72]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[72]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[72]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[73]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[73]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[73]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[73]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[74]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[74]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[74]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[74]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[75]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[75]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[75]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[75]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[76]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[76]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[76]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[76]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[77]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[77]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[77]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[77]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[78]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[78]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[78]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[78]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[79]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[79]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[79]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[79]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[7]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[7]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[80]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[80]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[80]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[80]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[81]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[81]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[81]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[81]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[82]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[82]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[82]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[82]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[83]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[83]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[83]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[83]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[84]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[84]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[84]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[84]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[85]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[85]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[85]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[85]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[86]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[86]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[86]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[86]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[87]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[87]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[87]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[87]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[88]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[88]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[88]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[88]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[89]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[89]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[89]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[89]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[8]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[8]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[90]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[90]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[90]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[90]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[91]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[91]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[91]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[91]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[92]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[92]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[92]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[92]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[93]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[93]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[93]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[93]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[94]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[94]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[94]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[94]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[95]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[95]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[95]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[95]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[96]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[96]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[96]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[96]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[97]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[97]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[97]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[97]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[98]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[98]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[98]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[98]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[99]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[99]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[99]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[99]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {embed_bf16[9]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {embed_bf16[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {embed_bf16[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {embed_bf16[9]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[0]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[0]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[10]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[10]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[11]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[11]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[12]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[12]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[13]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[13]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[14]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[14]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[15]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[15]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[16]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[16]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[17]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[17]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[18]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[18]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[19]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[19]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[1]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[1]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[20]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[20]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[21]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[21]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[22]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[22]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[23]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[23]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[24]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[24]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[25]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[25]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[26]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[26]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[27]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[27]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[28]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[28]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[29]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[29]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[2]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[2]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[30]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[30]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[31]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[31]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[3]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[3]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[4]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[4]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[5]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[5]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[6]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[6]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[7]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[7]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[8]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[8]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {head_logit[9]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {head_logit[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {head_logit[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {head_logit[9]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {in_valid}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {in_valid}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {in_valid}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {in_valid}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_ready}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_ready}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_ready}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_ready}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {rst_n}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {rst_n}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {start}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {start}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {start}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {start}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[0]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[0]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[0]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[100]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[100]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[100]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[100]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[101]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[101]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[101]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[101]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[102]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[102]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[102]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[102]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[103]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[103]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[103]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[103]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[104]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[104]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[104]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[104]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[105]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[105]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[105]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[105]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[106]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[106]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[106]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[106]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[107]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[107]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[107]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[107]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[108]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[108]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[108]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[108]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[109]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[109]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[109]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[109]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[10]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[10]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[10]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[110]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[110]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[110]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[110]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[111]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[111]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[111]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[111]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[112]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[112]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[112]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[112]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[113]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[113]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[113]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[113]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[114]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[114]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[114]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[114]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[115]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[115]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[115]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[115]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[116]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[116]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[116]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[116]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[117]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[117]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[117]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[117]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[118]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[118]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[118]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[118]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[119]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[119]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[119]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[119]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[11]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[11]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[11]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[120]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[120]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[120]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[120]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[121]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[121]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[121]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[121]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[122]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[122]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[122]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[122]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[123]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[123]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[123]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[123]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[124]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[124]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[124]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[124]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[125]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[125]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[125]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[125]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[126]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[126]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[126]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[126]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[127]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[127]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[127]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[127]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[128]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[128]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[128]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[128]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[129]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[129]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[129]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[129]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[12]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[12]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[12]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[130]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[130]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[130]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[130]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[131]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[131]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[131]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[131]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[132]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[132]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[132]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[132]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[133]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[133]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[133]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[133]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[134]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[134]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[134]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[134]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[135]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[135]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[135]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[135]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[136]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[136]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[136]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[136]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[137]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[137]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[137]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[137]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[138]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[138]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[138]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[138]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[139]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[139]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[139]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[139]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[13]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[13]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[13]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[140]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[140]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[140]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[140]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[141]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[141]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[141]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[141]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[142]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[142]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[142]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[142]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[143]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[143]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[143]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[143]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[144]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[144]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[144]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[144]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[145]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[145]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[145]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[145]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[146]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[146]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[146]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[146]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[147]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[147]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[147]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[147]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[148]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[148]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[148]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[148]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[149]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[149]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[149]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[149]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[14]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[14]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[14]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[150]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[150]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[150]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[150]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[151]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[151]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[151]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[151]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[152]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[152]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[152]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[152]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[153]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[153]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[153]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[153]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[154]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[154]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[154]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[154]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[155]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[155]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[155]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[155]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[156]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[156]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[156]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[156]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[157]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[157]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[157]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[157]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[158]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[158]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[158]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[158]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[159]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[159]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[159]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[159]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[15]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[15]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[15]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[160]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[160]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[160]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[160]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[161]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[161]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[161]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[161]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[162]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[162]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[162]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[162]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[163]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[163]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[163]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[163]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[164]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[164]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[164]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[164]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[165]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[165]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[165]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[165]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[166]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[166]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[166]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[166]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[167]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[167]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[167]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[167]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[168]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[168]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[168]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[168]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[169]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[169]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[169]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[169]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[16]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[16]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[16]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[170]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[170]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[170]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[170]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[171]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[171]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[171]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[171]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[172]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[172]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[172]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[172]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[173]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[173]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[173]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[173]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[174]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[174]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[174]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[174]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[175]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[175]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[175]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[175]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[176]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[176]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[176]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[176]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[177]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[177]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[177]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[177]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[178]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[178]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[178]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[178]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[179]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[179]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[179]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[179]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[17]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[17]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[17]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[180]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[180]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[180]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[180]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[181]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[181]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[181]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[181]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[182]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[182]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[182]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[182]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[183]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[183]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[183]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[183]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[184]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[184]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[184]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[184]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[185]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[185]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[185]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[185]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[186]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[186]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[186]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[186]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[187]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[187]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[187]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[187]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[188]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[188]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[188]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[188]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[189]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[189]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[189]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[189]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[18]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[18]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[18]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[190]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[190]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[190]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[190]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[191]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[191]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[191]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[191]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[192]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[192]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[192]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[192]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[193]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[193]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[193]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[193]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[194]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[194]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[194]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[194]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[195]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[195]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[195]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[195]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[196]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[196]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[196]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[196]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[197]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[197]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[197]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[197]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[198]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[198]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[198]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[198]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[199]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[199]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[199]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[199]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[19]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[19]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[19]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[1]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[1]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[1]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[200]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[200]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[200]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[200]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[201]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[201]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[201]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[201]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[202]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[202]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[202]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[202]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[203]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[203]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[203]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[203]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[204]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[204]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[204]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[204]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[205]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[205]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[205]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[205]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[206]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[206]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[206]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[206]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[207]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[207]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[207]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[207]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[208]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[208]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[208]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[208]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[209]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[209]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[209]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[209]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[20]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[20]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[20]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[210]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[210]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[210]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[210]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[211]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[211]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[211]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[211]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[212]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[212]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[212]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[212]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[213]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[213]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[213]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[213]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[214]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[214]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[214]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[214]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[215]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[215]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[215]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[215]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[216]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[216]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[216]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[216]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[217]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[217]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[217]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[217]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[218]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[218]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[218]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[218]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[219]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[219]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[219]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[219]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[21]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[21]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[21]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[220]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[220]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[220]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[220]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[221]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[221]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[221]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[221]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[222]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[222]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[222]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[222]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[223]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[223]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[223]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[223]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[224]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[224]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[224]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[224]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[225]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[225]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[225]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[225]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[226]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[226]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[226]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[226]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[227]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[227]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[227]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[227]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[228]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[228]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[228]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[228]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[229]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[229]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[229]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[229]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[22]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[22]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[22]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[230]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[230]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[230]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[230]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[231]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[231]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[231]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[231]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[232]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[232]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[232]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[232]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[233]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[233]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[233]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[233]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[234]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[234]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[234]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[234]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[235]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[235]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[235]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[235]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[236]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[236]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[236]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[236]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[237]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[237]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[237]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[237]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[238]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[238]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[238]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[238]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[239]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[239]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[239]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[239]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[23]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[23]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[23]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[240]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[240]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[240]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[240]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[241]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[241]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[241]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[241]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[242]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[242]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[242]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[242]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[243]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[243]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[243]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[243]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[244]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[244]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[244]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[244]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[245]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[245]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[245]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[245]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[246]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[246]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[246]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[246]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[247]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[247]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[247]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[247]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[248]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[248]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[248]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[248]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[249]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[249]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[249]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[249]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[24]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[24]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[24]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[250]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[250]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[250]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[250]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[251]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[251]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[251]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[251]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[252]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[252]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[252]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[252]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[253]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[253]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[253]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[253]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[254]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[254]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[254]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[254]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[255]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[255]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[255]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[255]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[25]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[25]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[25]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[26]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[26]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[26]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[27]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[27]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[27]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[28]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[28]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[28]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[29]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[29]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[29]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[2]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[2]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[2]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[30]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[30]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[30]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[31]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[31]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[31]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[32]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[32]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[32]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[32]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[33]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[33]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[33]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[33]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[34]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[34]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[34]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[34]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[35]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[35]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[35]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[35]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[36]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[36]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[36]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[36]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[37]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[37]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[37]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[37]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[38]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[38]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[38]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[38]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[39]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[39]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[39]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[39]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[3]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[3]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[3]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[40]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[40]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[40]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[40]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[41]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[41]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[41]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[41]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[42]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[42]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[42]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[42]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[43]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[43]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[43]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[43]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[44]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[44]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[44]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[44]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[45]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[45]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[45]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[45]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[46]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[46]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[46]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[46]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[47]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[47]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[47]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[47]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[48]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[48]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[48]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[48]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[49]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[49]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[49]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[49]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[4]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[4]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[4]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[50]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[50]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[50]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[50]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[51]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[51]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[51]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[51]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[52]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[52]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[52]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[52]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[53]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[53]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[53]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[53]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[54]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[54]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[54]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[54]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[55]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[55]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[55]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[55]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[56]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[56]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[56]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[56]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[57]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[57]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[57]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[57]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[58]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[58]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[58]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[58]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[59]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[59]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[59]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[59]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[5]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[5]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[5]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[60]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[60]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[60]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[60]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[61]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[61]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[61]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[61]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[62]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[62]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[62]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[62]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[63]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[63]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[63]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[63]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[64]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[64]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[64]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[64]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[65]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[65]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[65]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[65]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[66]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[66]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[66]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[66]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[67]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[67]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[67]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[67]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[68]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[68]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[68]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[68]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[69]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[69]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[69]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[69]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[6]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[6]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[6]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[70]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[70]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[70]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[70]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[71]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[71]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[71]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[71]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[72]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[72]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[72]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[72]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[73]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[73]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[73]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[73]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[74]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[74]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[74]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[74]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[75]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[75]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[75]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[75]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[76]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[76]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[76]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[76]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[77]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[77]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[77]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[77]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[78]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[78]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[78]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[78]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[79]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[79]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[79]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[79]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[7]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[7]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[7]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[80]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[80]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[80]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[80]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[81]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[81]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[81]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[81]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[82]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[82]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[82]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[82]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[83]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[83]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[83]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[83]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[84]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[84]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[84]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[84]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[85]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[85]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[85]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[85]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[86]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[86]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[86]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[86]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[87]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[87]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[87]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[87]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[88]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[88]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[88]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[88]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[89]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[89]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[89]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[89]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[8]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[8]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[8]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[90]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[90]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[90]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[90]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[91]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[91]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[91]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[91]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[92]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[92]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[92]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[92]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[93]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[93]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[93]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[93]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[94]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[94]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[94]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[94]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[95]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[95]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[95]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[95]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[96]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[96]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[96]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[96]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[97]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[97]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[97]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[97]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[98]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[98]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[98]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[98]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[99]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[99]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[99]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[99]}]
set_input_delay 546.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {weight_bf16[9]}]
set_input_delay 907.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {weight_bf16[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {weight_bf16[9]}]
set_input_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {weight_bf16[9]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {fault}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {fault}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {fault}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {fault}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {in_ready}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {in_ready}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {in_ready}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {in_ready}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[0]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[0]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[0]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[0]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[10]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[10]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[10]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[10]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[11]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[11]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[11]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[11]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[12]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[12]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[12]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[12]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[13]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[13]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[13]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[13]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[14]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[14]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[14]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[14]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[15]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[15]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[15]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[15]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[16]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[16]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[16]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[16]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[17]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[17]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[17]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[17]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[18]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[18]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[18]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[18]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[19]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[19]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[19]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[19]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[1]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[1]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[1]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[1]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[20]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[20]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[20]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[20]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[21]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[21]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[21]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[21]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[22]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[22]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[22]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[22]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[23]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[23]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[23]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[23]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[24]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[24]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[24]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[24]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[25]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[25]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[25]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[25]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[26]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[26]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[26]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[26]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[27]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[27]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[27]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[27]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[28]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[28]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[28]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[28]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[29]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[29]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[29]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[29]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[2]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[2]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[2]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[2]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[30]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[30]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[30]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[30]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[31]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[31]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[31]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[31]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[3]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[3]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[3]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[3]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[4]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[4]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[4]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[4]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[5]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[5]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[5]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[5]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[6]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[6]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[6]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[6]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[7]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[7]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[7]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[7]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[8]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[8]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[8]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[8]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_bits[9]}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_bits[9]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_bits[9]}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_bits[9]}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {out_valid}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {out_valid}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {out_valid}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {out_valid}]
set_output_delay -596.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {start_ready}]
set_output_delay -407.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {start_ready}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -rise -max -add_delay [get_ports {start_ready}]
set_output_delay 487.0000 -clock [get_clocks {ot_lb_v_core_clk}] -fall -max -add_delay [get_ports {start_ready}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {busy$_DFFE_PN0P_/RESETN}]\
           [get_pins {busy$_DFFE_PN0P_/SETN}]\
           [get_pins {count[0]$_DFFE_PN0P_/RESETN}]\
           [get_pins {count[0]$_DFFE_PN0P_/SETN}]\
           [get_pins {count[1]$_DFFE_PN0P_/RESETN}]\
           [get_pins {count[1]$_DFFE_PN0P_/SETN}]\
           [get_pins {count[2]$_DFFE_PN0P_/RESETN}]\
           [get_pins {count[2]$_DFFE_PN0P_/SETN}]\
           [get_pins {count[3]$_DFFE_PN0P_/RESETN}]\
           [get_pins {count[3]$_DFFE_PN0P_/SETN}]\
           [get_pins {count[4]$_DFFE_PN0P_/RESETN}]\
           [get_pins {count[4]$_DFFE_PN0P_/SETN}]\
           [get_pins {fault$_DFF_PN0_/RESETN}]\
           [get_pins {fault$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[0].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[1].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[2].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[3].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[4].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[5].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[6].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[0].g_add[7].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[0].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[1].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[2].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[3].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[4].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[5].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[6].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_chunk[1].g_add[7].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[0].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[0].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[10].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[10].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[11].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[11].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[12].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[12].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[13].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[13].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[14].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[14].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[15].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[15].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[1].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[1].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[2].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[2].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[3].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[3].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[4].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[4].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[5].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[5].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[6].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[6].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[7].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[7].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[8].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[8].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.fault$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.fault$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_mul[9].u_mul.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_mul[9].u_mul.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_pin.accepted$_DFF_PN0_/RESETN}]\
           [get_pins {g_pin.accepted$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].have$_DFFE_PN0P_/RESETN}]\
           [get_pins {g_tree[0].have$_DFFE_PN0P_/SETN}]\
           [get_pins {g_tree[0].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[0].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[0].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].have$_DFFE_PN0P_/RESETN}]\
           [get_pins {g_tree[1].have$_DFFE_PN0P_/SETN}]\
           [get_pins {g_tree[1].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[1].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[1].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].have$_DFFE_PN0P_/RESETN}]\
           [get_pins {g_tree[2].have$_DFFE_PN0P_/SETN}]\
           [get_pins {g_tree[2].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[2].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[2].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].have$_DFFE_PN0P_/RESETN}]\
           [get_pins {g_tree[3].have$_DFFE_PN0P_/SETN}]\
           [get_pins {g_tree[3].u_add.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {g_tree[3].u_add.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {g_tree[3].u_add.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {head[0]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[0]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[10]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[10]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[11]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[11]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[12]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[12]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[13]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[13]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[14]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[14]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[15]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[15]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[16]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[16]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[17]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[17]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[18]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[18]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[19]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[19]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[1]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[1]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[20]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[20]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[21]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[21]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[22]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[22]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[23]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[23]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[24]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[24]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[25]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[25]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[26]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[26]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[27]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[27]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[28]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[28]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[29]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[29]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[2]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[2]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[30]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[30]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[31]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[31]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[3]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[3]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[4]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[4]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[5]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[5]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[6]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[6]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[7]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[7]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[8]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[8]$_DFFE_PN0P_/SETN}]\
           [get_pins {head[9]$_DFFE_PN0P_/RESETN}]\
           [get_pins {head[9]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[0]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[0]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[10]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[10]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[11]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[11]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[12]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[12]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[13]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[13]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[14]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[14]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[15]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[15]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[16]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[16]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[17]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[17]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[18]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[18]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[19]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[19]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[1]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[1]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[20]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[20]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[21]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[21]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[22]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[22]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[23]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[23]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[24]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[24]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[25]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[25]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[26]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[26]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[27]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[27]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[28]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[28]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[29]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[29]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[2]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[2]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[30]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[30]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[31]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[31]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[3]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[3]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[4]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[4]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[5]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[5]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[6]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[6]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[7]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[7]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[8]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[8]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_bits[9]$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_bits[9]$_DFFE_PN0P_/SETN}]\
           [get_pins {out_valid$_DFFE_PN0P_/RESETN}]\
           [get_pins {out_valid$_DFFE_PN0P_/SETN}]\
           [get_pins {pv[0]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[0]$_DFF_PN0_/SETN}]\
           [get_pins {pv[1]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[1]$_DFF_PN0_/SETN}]\
           [get_pins {pv[2]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[2]$_DFF_PN0_/SETN}]\
           [get_pins {pv[3]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[3]$_DFF_PN0_/SETN}]\
           [get_pins {pv[4]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[4]$_DFF_PN0_/SETN}]\
           [get_pins {pv[5]$_DFF_PN0_/RESETN}]\
           [get_pins {pv[5]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_join.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {u_join.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {u_join.y[9]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.err[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.err[0]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.err[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.err[1]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.g_s9.v_q$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.g_s9.v_q$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c0.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c0.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c1.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c1.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c2.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c2.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c3.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c3.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c4.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c4.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c5.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c5.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c6.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c6.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c7.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c7.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.u_c8.g_r.v$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.u_c8.g_r.v$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.valid_out$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.valid_out$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[0]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[10]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[11]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[12]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[13]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[14]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[15]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[16]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[16]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[17]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[17]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[18]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[18]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[19]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[19]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[1]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[20]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[20]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[21]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[21]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[22]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[22]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[23]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[23]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[24]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[24]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[25]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[25]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[26]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[26]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[27]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[27]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[28]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[28]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[29]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[29]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[2]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[30]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[30]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[31]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[31]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[3]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[4]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[5]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[6]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[7]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[8]$_DFF_PN0_/SETN}]\
           [get_pins {u_pair.y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {u_pair.y[9]$_DFF_PN0_/SETN}]]
set_false_path\
    -from [get_ports {rst_n}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
set_max_transition 250.0000 [current_design]
set_max_fanout 16.0000 [current_design]
