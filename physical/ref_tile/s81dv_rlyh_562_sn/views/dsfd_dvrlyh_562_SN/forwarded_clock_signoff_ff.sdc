###############################################################################
# Created by write_sdc
# Tue Oct 20 15:28:36 2026
###############################################################################
current_design dsfd_dvrlyh_562_SN
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 833.3330 [get_ports {ck}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
create_generated_clock -name ck_o_fwd -source [get_ports {ck}] -divide_by 1 -invert [get_ports {ck_o}]
set_clock_uncertainty -setup 60.0000 ck_o_fwd
set_clock_uncertainty -hold 25.0000 ck_o_fwd
set_propagated_clock [get_clocks {ck_o_fwd}]
create_clock -name ot_lb_v_core_clk -period 770.0000 
set_clock_uncertainty -setup 60.0000 ot_lb_v_core_clk
set_clock_uncertainty -hold 25.0000 ot_lb_v_core_clk
set_clock_latency 69.9008 [get_clocks {ot_lb_v_core_clk}]
set_clock_latency -source 0.0000 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[0]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[0]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[100]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[100]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[101]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[101]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[102]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[102]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[103]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[103]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[104]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[104]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[105]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[105]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[106]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[106]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[107]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[107]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[108]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[108]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[109]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[109]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[10]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[10]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[110]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[110]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[111]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[111]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[112]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[112]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[113]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[113]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[114]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[114]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[115]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[115]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[116]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[116]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[117]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[117]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[118]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[118]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[119]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[119]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[11]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[11]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[120]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[120]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[121]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[121]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[122]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[122]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[123]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[123]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[124]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[124]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[125]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[125]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[126]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[126]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[127]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[127]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[128]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[128]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[129]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[129]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[12]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[12]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[130]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[130]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[131]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[131]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[132]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[132]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[133]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[133]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[134]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[134]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[135]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[135]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[136]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[136]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[137]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[137]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[138]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[138]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[139]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[139]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[13]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[13]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[140]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[140]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[141]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[141]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[142]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[142]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[143]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[143]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[144]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[144]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[145]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[145]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[146]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[146]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[147]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[147]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[148]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[148]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[149]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[149]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[14]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[14]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[150]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[150]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[151]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[151]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[152]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[152]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[153]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[153]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[154]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[154]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[155]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[155]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[156]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[156]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[157]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[157]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[158]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[158]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[159]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[159]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[15]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[15]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[160]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[160]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[161]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[161]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[162]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[162]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[163]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[163]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[164]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[164]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[165]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[165]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[166]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[166]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[167]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[167]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[168]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[168]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[169]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[169]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[16]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[16]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[170]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[170]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[171]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[171]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[172]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[172]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[173]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[173]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[174]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[174]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[175]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[175]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[176]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[176]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[177]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[177]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[178]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[178]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[179]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[179]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[17]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[17]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[180]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[180]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[181]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[181]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[182]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[182]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[183]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[183]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[184]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[184]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[185]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[185]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[186]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[186]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[187]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[187]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[188]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[188]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[189]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[189]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[18]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[18]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[190]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[190]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[191]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[191]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[192]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[192]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[193]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[193]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[194]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[194]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[195]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[195]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[196]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[196]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[197]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[197]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[198]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[198]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[199]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[199]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[19]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[19]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[1]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[1]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[200]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[200]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[201]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[201]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[202]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[202]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[203]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[203]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[204]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[204]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[205]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[205]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[206]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[206]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[207]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[207]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[208]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[208]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[209]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[209]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[20]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[20]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[210]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[210]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[211]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[211]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[212]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[212]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[213]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[213]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[214]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[214]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[215]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[215]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[216]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[216]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[217]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[217]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[218]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[218]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[219]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[219]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[21]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[21]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[220]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[220]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[221]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[221]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[222]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[222]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[223]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[223]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[224]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[224]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[225]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[225]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[226]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[226]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[227]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[227]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[228]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[228]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[229]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[229]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[22]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[22]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[230]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[230]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[231]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[231]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[232]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[232]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[233]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[233]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[234]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[234]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[235]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[235]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[236]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[236]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[237]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[237]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[238]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[238]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[239]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[239]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[23]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[23]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[240]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[240]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[241]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[241]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[242]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[242]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[243]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[243]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[244]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[244]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[245]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[245]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[246]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[246]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[247]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[247]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[248]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[248]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[249]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[249]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[24]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[24]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[250]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[250]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[251]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[251]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[252]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[252]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[253]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[253]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[254]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[254]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[255]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[255]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[256]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[256]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[257]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[257]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[258]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[258]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[259]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[259]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[25]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[25]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[260]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[260]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[261]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[261]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[262]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[262]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[263]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[263]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[264]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[264]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[265]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[265]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[266]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[266]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[267]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[267]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[268]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[268]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[269]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[269]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[26]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[26]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[270]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[270]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[271]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[271]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[272]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[272]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[273]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[273]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[274]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[274]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[275]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[275]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[276]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[276]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[277]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[277]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[278]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[278]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[279]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[279]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[27]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[27]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[280]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[280]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[281]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[281]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[282]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[282]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[283]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[283]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[284]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[284]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[285]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[285]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[286]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[286]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[287]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[287]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[288]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[288]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[289]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[289]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[28]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[28]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[290]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[290]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[291]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[291]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[292]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[292]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[293]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[293]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[294]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[294]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[295]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[295]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[296]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[296]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[297]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[297]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[298]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[298]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[299]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[299]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[29]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[29]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[2]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[2]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[300]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[300]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[301]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[301]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[302]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[302]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[303]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[303]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[304]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[304]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[305]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[305]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[306]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[306]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[307]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[307]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[308]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[308]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[309]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[309]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[30]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[30]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[310]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[310]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[311]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[311]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[312]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[312]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[313]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[313]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[314]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[314]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[315]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[315]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[316]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[316]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[317]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[317]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[318]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[318]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[319]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[319]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[31]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[31]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[320]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[320]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[321]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[321]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[322]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[322]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[323]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[323]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[324]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[324]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[325]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[325]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[326]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[326]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[327]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[327]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[328]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[328]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[329]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[329]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[32]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[32]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[330]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[330]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[331]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[331]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[332]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[332]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[333]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[333]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[334]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[334]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[335]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[335]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[336]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[336]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[337]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[337]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[338]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[338]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[339]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[339]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[33]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[33]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[340]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[340]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[341]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[341]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[342]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[342]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[343]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[343]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[344]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[344]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[345]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[345]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[346]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[346]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[347]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[347]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[348]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[348]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[349]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[349]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[34]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[34]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[350]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[350]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[351]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[351]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[352]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[352]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[353]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[353]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[354]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[354]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[355]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[355]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[356]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[356]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[357]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[357]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[358]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[358]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[359]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[359]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[35]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[35]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[360]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[360]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[361]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[361]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[362]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[362]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[363]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[363]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[364]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[364]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[365]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[365]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[366]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[366]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[367]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[367]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[368]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[368]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[369]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[369]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[36]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[36]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[370]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[370]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[371]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[371]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[372]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[372]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[373]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[373]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[374]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[374]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[375]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[375]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[376]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[376]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[377]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[377]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[378]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[378]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[379]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[379]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[37]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[37]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[380]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[380]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[381]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[381]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[382]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[382]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[383]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[383]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[384]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[384]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[385]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[385]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[386]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[386]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[387]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[387]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[388]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[388]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[389]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[389]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[38]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[38]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[390]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[390]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[391]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[391]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[392]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[392]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[393]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[393]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[394]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[394]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[395]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[395]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[396]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[396]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[397]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[397]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[398]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[398]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[399]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[399]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[39]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[39]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[3]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[3]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[400]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[400]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[401]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[401]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[402]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[402]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[403]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[403]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[404]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[404]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[405]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[405]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[406]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[406]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[407]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[407]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[408]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[408]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[409]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[409]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[40]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[40]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[410]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[410]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[411]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[411]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[412]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[412]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[413]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[413]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[414]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[414]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[415]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[415]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[416]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[416]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[417]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[417]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[418]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[418]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[419]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[419]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[41]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[41]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[420]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[420]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[421]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[421]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[422]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[422]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[423]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[423]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[424]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[424]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[425]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[425]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[426]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[426]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[427]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[427]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[428]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[428]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[429]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[429]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[42]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[42]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[430]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[430]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[431]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[431]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[432]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[432]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[433]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[433]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[434]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[434]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[435]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[435]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[436]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[436]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[437]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[437]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[438]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[438]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[439]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[439]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[43]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[43]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[440]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[440]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[441]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[441]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[442]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[442]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[443]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[443]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[444]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[444]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[445]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[445]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[446]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[446]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[447]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[447]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[448]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[448]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[449]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[449]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[44]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[44]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[450]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[450]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[451]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[451]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[452]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[452]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[453]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[453]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[454]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[454]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[455]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[455]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[456]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[456]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[457]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[457]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[458]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[458]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[459]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[459]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[45]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[45]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[460]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[460]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[461]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[461]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[462]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[462]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[463]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[463]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[464]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[464]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[465]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[465]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[466]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[466]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[467]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[467]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[468]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[468]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[469]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[469]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[46]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[46]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[470]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[470]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[471]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[471]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[472]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[472]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[473]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[473]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[474]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[474]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[475]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[475]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[476]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[476]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[477]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[477]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[478]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[478]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[479]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[479]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[47]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[47]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[480]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[480]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[481]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[481]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[482]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[482]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[483]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[483]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[484]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[484]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[485]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[485]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[486]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[486]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[487]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[487]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[488]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[488]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[489]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[489]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[48]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[48]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[490]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[490]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[491]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[491]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[492]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[492]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[493]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[493]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[494]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[494]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[495]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[495]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[496]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[496]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[497]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[497]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[498]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[498]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[499]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[499]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[49]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[49]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[4]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[4]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[500]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[500]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[501]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[501]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[502]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[502]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[503]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[503]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[504]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[504]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[505]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[505]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[506]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[506]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[507]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[507]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[508]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[508]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[509]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[509]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[50]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[50]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[510]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[510]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[511]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[511]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[512]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[512]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[513]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[513]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[514]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[514]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[515]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[515]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[516]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[516]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[517]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[517]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[518]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[518]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[519]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[519]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[51]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[51]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[520]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[520]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[521]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[521]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[522]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[522]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[523]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[523]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[524]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[524]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[525]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[525]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[526]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[526]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[527]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[527]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[528]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[528]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[529]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[529]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[52]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[52]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[530]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[530]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[531]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[531]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[532]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[532]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[533]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[533]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[534]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[534]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[535]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[535]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[536]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[536]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[537]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[537]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[538]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[538]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[539]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[539]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[53]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[53]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[540]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[540]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[541]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[541]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[542]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[542]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[543]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[543]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[544]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[544]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[545]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[545]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[546]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[546]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[547]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[547]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[548]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[548]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[549]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[549]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[54]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[54]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[550]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[550]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[551]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[551]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[552]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[552]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[553]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[553]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[554]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[554]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[555]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[555]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[556]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[556]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[557]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[557]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[558]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[558]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[559]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[559]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[55]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[55]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[560]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[560]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[561]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[561]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[56]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[56]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[57]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[57]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[58]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[58]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[59]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[59]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[5]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[5]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[60]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[60]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[61]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[61]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[62]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[62]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[63]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[63]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[64]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[64]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[65]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[65]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[66]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[66]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[67]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[67]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[68]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[68]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[69]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[69]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[6]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[6]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[70]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[70]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[71]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[71]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[72]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[72]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[73]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[73]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[74]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[74]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[75]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[75]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[76]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[76]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[77]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[77]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[78]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[78]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[79]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[79]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[7]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[7]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[80]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[80]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[81]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[81]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[82]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[82]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[83]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[83]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[84]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[84]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[85]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[85]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[86]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[86]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[87]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[87]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[88]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[88]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[89]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[89]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[8]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[8]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[90]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[90]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[91]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[91]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[92]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[92]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[93]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[93]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[94]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[94]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[95]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[95]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[96]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[96]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[97]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[97]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[98]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[98]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[99]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[99]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[9]}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[9]}]
set_input_delay 114.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {rs}]
set_input_delay 326.6526 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {rs}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {ck_o}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {ck_o}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[0]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[0]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[100]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[100]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[101]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[101]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[102]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[102]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[103]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[103]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[104]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[104]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[105]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[105]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[106]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[106]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[107]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[107]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[108]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[108]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[109]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[109]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[10]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[10]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[110]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[110]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[111]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[111]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[112]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[112]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[113]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[113]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[114]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[114]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[115]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[115]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[116]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[116]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[117]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[117]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[118]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[118]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[119]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[119]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[11]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[11]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[120]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[120]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[121]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[121]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[122]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[122]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[123]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[123]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[124]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[124]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[125]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[125]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[126]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[126]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[127]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[127]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[128]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[128]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[129]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[129]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[12]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[12]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[130]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[130]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[131]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[131]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[132]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[132]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[133]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[133]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[134]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[134]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[135]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[135]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[136]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[136]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[137]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[137]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[138]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[138]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[139]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[139]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[13]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[13]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[140]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[140]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[141]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[141]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[142]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[142]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[143]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[143]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[144]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[144]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[145]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[145]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[146]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[146]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[147]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[147]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[148]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[148]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[149]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[149]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[14]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[14]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[150]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[150]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[151]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[151]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[152]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[152]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[153]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[153]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[154]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[154]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[155]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[155]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[156]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[156]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[157]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[157]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[158]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[158]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[159]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[159]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[15]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[15]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[160]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[160]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[161]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[161]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[162]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[162]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[163]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[163]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[164]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[164]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[165]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[165]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[166]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[166]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[167]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[167]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[168]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[168]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[169]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[169]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[16]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[16]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[170]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[170]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[171]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[171]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[172]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[172]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[173]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[173]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[174]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[174]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[175]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[175]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[176]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[176]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[177]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[177]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[178]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[178]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[179]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[179]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[17]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[17]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[180]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[180]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[181]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[181]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[182]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[182]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[183]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[183]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[184]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[184]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[185]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[185]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[186]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[186]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[187]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[187]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[188]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[188]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[189]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[189]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[18]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[18]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[190]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[190]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[191]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[191]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[192]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[192]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[193]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[193]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[194]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[194]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[195]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[195]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[196]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[196]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[197]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[197]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[198]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[198]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[199]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[199]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[19]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[19]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[1]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[1]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[200]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[200]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[201]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[201]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[202]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[202]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[203]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[203]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[204]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[204]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[205]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[205]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[206]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[206]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[207]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[207]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[208]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[208]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[209]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[209]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[20]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[20]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[210]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[210]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[211]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[211]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[212]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[212]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[213]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[213]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[214]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[214]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[215]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[215]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[216]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[216]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[217]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[217]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[218]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[218]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[219]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[219]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[21]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[21]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[220]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[220]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[221]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[221]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[222]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[222]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[223]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[223]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[224]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[224]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[225]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[225]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[226]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[226]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[227]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[227]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[228]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[228]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[229]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[229]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[22]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[22]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[230]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[230]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[231]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[231]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[232]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[232]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[233]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[233]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[234]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[234]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[235]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[235]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[236]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[236]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[237]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[237]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[238]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[238]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[239]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[239]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[23]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[23]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[240]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[240]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[241]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[241]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[242]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[242]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[243]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[243]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[244]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[244]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[245]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[245]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[246]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[246]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[247]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[247]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[248]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[248]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[249]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[249]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[24]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[24]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[250]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[250]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[251]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[251]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[252]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[252]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[253]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[253]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[254]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[254]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[255]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[255]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[256]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[256]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[257]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[257]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[258]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[258]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[259]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[259]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[25]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[25]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[260]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[260]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[261]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[261]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[262]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[262]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[263]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[263]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[264]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[264]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[265]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[265]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[266]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[266]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[267]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[267]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[268]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[268]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[269]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[269]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[26]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[26]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[270]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[270]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[271]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[271]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[272]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[272]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[273]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[273]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[274]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[274]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[275]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[275]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[276]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[276]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[277]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[277]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[278]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[278]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[279]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[279]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[27]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[27]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[280]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[280]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[281]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[281]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[282]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[282]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[283]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[283]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[284]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[284]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[285]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[285]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[286]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[286]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[287]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[287]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[288]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[288]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[289]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[289]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[28]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[28]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[290]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[290]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[291]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[291]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[292]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[292]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[293]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[293]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[294]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[294]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[295]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[295]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[296]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[296]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[297]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[297]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[298]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[298]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[299]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[299]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[29]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[29]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[2]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[2]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[300]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[300]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[301]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[301]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[302]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[302]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[303]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[303]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[304]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[304]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[305]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[305]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[306]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[306]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[307]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[307]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[308]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[308]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[309]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[309]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[30]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[30]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[310]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[310]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[311]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[311]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[312]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[312]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[313]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[313]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[314]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[314]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[315]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[315]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[316]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[316]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[317]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[317]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[318]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[318]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[319]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[319]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[31]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[31]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[320]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[320]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[321]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[321]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[322]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[322]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[323]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[323]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[324]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[324]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[325]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[325]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[326]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[326]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[327]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[327]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[328]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[328]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[329]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[329]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[32]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[32]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[330]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[330]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[331]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[331]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[332]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[332]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[333]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[333]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[334]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[334]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[335]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[335]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[336]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[336]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[337]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[337]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[338]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[338]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[339]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[339]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[33]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[33]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[340]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[340]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[341]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[341]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[342]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[342]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[343]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[343]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[344]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[344]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[345]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[345]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[346]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[346]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[347]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[347]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[348]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[348]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[349]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[349]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[34]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[34]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[350]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[350]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[351]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[351]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[352]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[352]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[353]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[353]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[354]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[354]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[355]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[355]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[356]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[356]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[357]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[357]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[358]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[358]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[359]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[359]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[35]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[35]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[360]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[360]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[361]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[361]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[362]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[362]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[363]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[363]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[364]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[364]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[365]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[365]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[366]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[366]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[367]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[367]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[368]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[368]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[369]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[369]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[36]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[36]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[370]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[370]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[371]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[371]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[372]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[372]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[373]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[373]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[374]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[374]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[375]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[375]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[376]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[376]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[377]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[377]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[378]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[378]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[379]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[379]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[37]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[37]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[380]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[380]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[381]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[381]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[382]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[382]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[383]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[383]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[384]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[384]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[385]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[385]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[386]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[386]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[387]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[387]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[388]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[388]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[389]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[389]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[38]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[38]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[390]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[390]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[391]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[391]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[392]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[392]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[393]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[393]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[394]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[394]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[395]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[395]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[396]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[396]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[397]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[397]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[398]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[398]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[399]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[399]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[39]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[39]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[3]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[3]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[400]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[400]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[401]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[401]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[402]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[402]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[403]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[403]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[404]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[404]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[405]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[405]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[406]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[406]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[407]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[407]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[408]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[408]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[409]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[409]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[40]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[40]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[410]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[410]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[411]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[411]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[412]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[412]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[413]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[413]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[414]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[414]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[415]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[415]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[416]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[416]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[417]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[417]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[418]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[418]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[419]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[419]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[41]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[41]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[420]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[420]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[421]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[421]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[422]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[422]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[423]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[423]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[424]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[424]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[425]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[425]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[426]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[426]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[427]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[427]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[428]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[428]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[429]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[429]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[42]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[42]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[430]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[430]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[431]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[431]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[432]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[432]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[433]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[433]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[434]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[434]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[435]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[435]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[436]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[436]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[437]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[437]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[438]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[438]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[439]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[439]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[43]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[43]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[440]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[440]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[441]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[441]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[442]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[442]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[443]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[443]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[444]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[444]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[445]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[445]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[446]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[446]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[447]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[447]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[448]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[448]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[449]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[449]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[44]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[44]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[450]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[450]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[451]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[451]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[452]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[452]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[453]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[453]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[454]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[454]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[455]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[455]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[456]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[456]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[457]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[457]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[458]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[458]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[459]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[459]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[45]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[45]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[460]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[460]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[461]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[461]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[462]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[462]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[463]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[463]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[464]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[464]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[465]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[465]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[466]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[466]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[467]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[467]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[468]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[468]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[469]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[469]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[46]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[46]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[470]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[470]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[471]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[471]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[472]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[472]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[473]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[473]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[474]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[474]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[475]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[475]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[476]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[476]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[477]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[477]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[478]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[478]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[479]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[479]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[47]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[47]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[480]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[480]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[481]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[481]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[482]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[482]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[483]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[483]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[484]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[484]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[485]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[485]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[486]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[486]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[487]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[487]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[488]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[488]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[489]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[489]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[48]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[48]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[490]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[490]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[491]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[491]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[492]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[492]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[493]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[493]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[494]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[494]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[495]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[495]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[496]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[496]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[497]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[497]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[498]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[498]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[499]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[499]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[49]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[49]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[4]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[4]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[500]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[500]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[501]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[501]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[502]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[502]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[503]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[503]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[504]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[504]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[505]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[505]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[506]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[506]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[507]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[507]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[508]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[508]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[509]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[509]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[50]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[50]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[510]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[510]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[511]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[511]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[512]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[512]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[513]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[513]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[514]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[514]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[515]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[515]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[516]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[516]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[517]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[517]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[518]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[518]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[519]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[519]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[51]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[51]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[520]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[520]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[521]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[521]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[522]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[522]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[523]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[523]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[524]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[524]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[525]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[525]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[526]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[526]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[527]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[527]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[528]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[528]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[529]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[529]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[52]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[52]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[530]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[530]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[531]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[531]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[532]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[532]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[533]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[533]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[534]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[534]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[535]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[535]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[536]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[536]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[537]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[537]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[538]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[538]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[539]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[539]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[53]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[53]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[540]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[540]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[541]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[541]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[542]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[542]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[543]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[543]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[544]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[544]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[545]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[545]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[546]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[546]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[547]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[547]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[548]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[548]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[549]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[549]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[54]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[54]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[550]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[550]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[551]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[551]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[552]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[552]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[553]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[553]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[554]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[554]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[555]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[555]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[556]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[556]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[557]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[557]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[558]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[558]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[559]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[559]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[55]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[55]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[560]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[560]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[561]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[561]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[56]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[56]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[57]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[57]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[58]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[58]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[59]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[59]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[5]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[5]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[60]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[60]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[61]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[61]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[62]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[62]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[63]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[63]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[64]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[64]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[65]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[65]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[66]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[66]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[67]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[67]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[68]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[68]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[69]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[69]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[6]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[6]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[70]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[70]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[71]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[71]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[72]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[72]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[73]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[73]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[74]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[74]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[75]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[75]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[76]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[76]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[77]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[77]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[78]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[78]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[79]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[79]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[7]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[7]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[80]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[80]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[81]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[81]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[82]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[82]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[83]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[83]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[84]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[84]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[85]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[85]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[86]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[86]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[87]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[87]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[88]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[88]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[89]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[89]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[8]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[8]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[90]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[90]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[91]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[91]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[92]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[92]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[93]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[93]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[94]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[94]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[95]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[95]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[96]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[96]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[97]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[97]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[98]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[98]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[99]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[99]}]
set_output_delay -64.7839 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[9]}]
set_output_delay 186.6814 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[9]}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {u_st.u.g_rsreg.rq$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.g_rsreg.rq$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[0]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[100]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[100]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[101]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[101]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[102]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[102]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[103]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[103]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[104]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[104]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[105]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[105]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[106]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[106]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[107]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[107]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[108]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[108]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[109]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[109]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[10]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[10]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[110]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[110]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[111]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[111]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[112]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[112]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[113]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[113]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[114]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[114]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[115]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[115]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[116]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[116]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[117]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[117]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[118]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[118]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[119]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[119]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[11]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[11]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[120]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[120]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[121]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[121]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[122]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[122]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[123]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[123]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[124]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[124]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[125]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[125]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[126]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[126]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[127]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[127]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[128]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[128]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[129]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[129]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[12]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[12]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[130]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[130]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[131]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[131]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[132]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[132]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[133]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[133]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[134]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[134]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[135]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[135]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[136]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[136]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[137]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[137]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[138]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[138]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[139]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[139]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[13]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[13]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[140]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[140]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[141]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[141]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[142]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[142]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[143]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[143]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[144]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[144]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[145]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[145]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[146]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[146]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[147]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[147]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[148]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[148]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[149]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[149]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[14]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[14]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[150]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[150]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[151]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[151]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[152]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[152]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[153]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[153]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[154]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[154]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[155]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[155]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[156]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[156]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[157]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[157]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[158]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[158]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[159]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[159]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[15]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[15]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[160]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[160]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[161]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[161]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[162]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[162]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[163]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[163]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[164]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[164]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[165]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[165]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[166]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[166]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[167]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[167]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[168]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[168]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[169]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[169]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[16]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[16]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[170]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[170]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[171]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[171]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[172]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[172]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[173]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[173]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[174]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[174]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[175]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[175]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[176]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[176]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[177]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[177]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[178]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[178]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[179]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[179]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[17]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[17]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[180]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[180]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[181]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[181]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[182]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[182]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[183]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[183]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[184]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[184]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[185]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[185]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[186]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[186]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[187]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[187]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[188]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[188]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[189]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[189]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[18]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[18]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[190]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[190]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[191]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[191]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[192]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[192]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[193]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[193]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[194]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[194]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[195]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[195]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[196]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[196]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[197]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[197]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[198]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[198]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[199]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[199]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[19]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[19]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[1]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[200]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[200]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[201]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[201]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[202]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[202]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[203]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[203]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[204]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[204]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[205]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[205]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[206]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[206]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[207]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[207]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[208]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[208]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[209]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[209]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[20]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[20]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[210]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[210]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[211]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[211]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[212]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[212]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[213]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[213]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[214]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[214]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[215]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[215]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[216]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[216]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[217]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[217]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[218]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[218]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[219]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[219]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[21]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[21]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[220]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[220]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[221]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[221]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[222]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[222]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[223]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[223]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[224]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[224]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[225]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[225]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[226]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[226]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[227]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[227]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[228]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[228]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[229]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[229]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[22]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[22]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[230]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[230]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[231]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[231]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[232]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[232]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[233]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[233]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[234]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[234]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[235]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[235]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[236]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[236]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[237]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[237]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[238]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[238]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[239]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[239]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[23]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[23]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[240]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[240]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[241]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[241]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[242]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[242]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[243]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[243]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[244]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[244]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[245]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[245]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[246]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[246]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[247]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[247]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[248]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[248]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[249]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[249]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[24]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[24]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[250]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[250]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[251]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[251]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[252]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[252]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[253]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[253]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[254]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[254]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[255]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[255]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[256]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[256]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[257]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[257]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[258]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[258]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[259]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[259]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[25]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[25]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[260]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[260]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[261]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[261]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[262]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[262]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[263]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[263]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[264]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[264]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[265]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[265]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[266]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[266]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[267]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[267]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[268]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[268]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[269]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[269]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[26]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[26]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[270]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[270]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[271]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[271]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[272]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[272]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[273]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[273]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[274]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[274]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[275]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[275]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[276]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[276]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[277]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[277]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[278]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[278]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[279]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[279]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[27]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[27]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[280]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[280]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[281]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[281]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[282]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[282]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[283]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[283]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[284]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[284]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[285]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[285]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[286]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[286]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[287]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[287]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[288]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[288]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[289]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[289]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[28]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[28]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[290]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[290]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[291]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[291]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[292]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[292]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[293]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[293]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[294]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[294]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[295]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[295]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[296]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[296]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[297]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[297]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[298]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[298]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[299]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[299]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[29]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[29]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[2]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[2]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[300]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[300]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[301]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[301]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[302]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[302]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[303]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[303]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[304]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[304]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[305]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[305]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[306]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[306]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[307]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[307]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[308]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[308]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[309]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[309]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[30]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[30]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[310]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[310]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[311]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[311]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[312]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[312]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[313]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[313]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[314]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[314]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[315]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[315]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[316]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[316]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[317]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[317]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[318]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[318]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[319]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[319]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[31]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[31]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[320]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[320]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[321]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[321]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[322]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[322]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[323]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[323]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[324]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[324]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[325]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[325]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[326]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[326]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[327]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[327]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[328]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[328]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[329]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[329]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[32]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[32]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[330]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[330]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[331]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[331]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[332]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[332]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[333]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[333]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[334]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[334]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[335]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[335]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[336]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[336]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[337]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[337]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[338]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[338]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[339]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[339]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[33]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[33]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[340]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[340]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[341]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[341]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[342]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[342]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[343]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[343]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[344]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[344]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[345]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[345]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[346]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[346]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[347]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[347]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[348]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[348]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[349]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[349]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[34]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[34]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[350]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[350]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[351]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[351]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[352]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[352]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[353]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[353]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[354]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[354]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[355]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[355]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[356]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[356]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[357]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[357]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[358]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[358]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[359]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[359]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[35]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[35]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[360]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[360]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[361]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[361]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[362]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[362]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[363]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[363]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[364]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[364]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[365]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[365]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[366]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[366]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[367]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[367]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[368]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[368]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[369]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[369]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[36]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[36]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[370]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[370]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[371]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[371]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[372]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[372]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[373]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[373]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[374]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[374]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[375]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[375]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[376]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[376]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[377]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[377]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[378]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[378]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[379]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[379]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[37]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[37]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[380]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[380]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[381]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[381]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[382]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[382]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[383]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[383]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[384]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[384]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[385]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[385]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[386]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[386]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[387]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[387]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[388]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[388]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[389]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[389]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[38]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[38]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[390]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[390]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[391]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[391]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[392]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[392]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[393]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[393]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[394]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[394]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[395]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[395]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[396]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[396]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[397]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[397]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[398]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[398]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[399]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[399]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[39]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[39]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[3]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[3]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[400]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[400]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[401]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[401]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[402]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[402]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[403]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[403]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[404]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[404]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[405]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[405]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[406]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[406]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[407]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[407]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[408]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[408]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[409]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[409]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[40]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[40]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[410]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[410]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[411]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[411]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[412]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[412]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[413]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[413]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[414]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[414]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[415]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[415]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[416]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[416]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[417]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[417]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[418]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[418]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[419]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[419]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[41]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[41]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[420]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[420]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[421]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[421]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[422]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[422]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[423]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[423]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[424]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[424]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[425]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[425]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[426]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[426]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[427]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[427]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[428]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[428]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[429]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[429]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[42]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[42]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[430]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[430]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[431]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[431]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[432]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[432]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[433]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[433]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[434]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[434]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[435]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[435]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[436]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[436]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[437]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[437]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[438]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[438]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[439]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[439]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[43]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[43]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[440]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[440]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[441]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[441]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[442]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[442]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[443]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[443]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[444]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[444]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[445]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[445]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[446]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[446]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[447]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[447]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[448]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[448]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[449]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[449]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[44]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[44]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[450]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[450]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[451]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[451]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[452]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[452]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[453]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[453]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[454]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[454]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[455]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[455]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[456]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[456]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[457]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[457]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[458]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[458]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[459]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[459]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[45]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[45]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[460]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[460]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[461]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[461]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[462]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[462]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[463]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[463]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[464]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[464]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[465]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[465]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[466]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[466]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[467]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[467]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[468]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[468]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[469]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[469]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[46]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[46]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[470]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[470]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[471]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[471]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[472]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[472]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[473]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[473]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[474]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[474]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[475]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[475]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[476]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[476]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[477]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[477]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[478]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[478]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[479]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[479]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[47]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[47]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[480]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[480]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[481]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[481]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[482]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[482]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[483]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[483]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[484]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[484]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[485]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[485]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[486]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[486]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[487]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[487]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[488]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[488]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[489]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[489]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[48]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[48]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[490]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[490]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[491]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[491]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[492]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[492]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[493]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[493]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[494]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[494]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[495]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[495]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[496]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[496]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[497]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[497]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[498]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[498]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[499]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[499]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[49]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[49]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[4]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[4]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[500]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[500]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[501]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[501]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[502]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[502]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[503]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[503]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[504]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[504]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[505]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[505]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[506]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[506]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[507]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[507]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[508]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[508]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[509]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[509]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[50]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[50]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[510]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[510]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[511]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[511]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[512]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[512]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[513]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[513]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[514]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[514]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[515]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[515]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[516]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[516]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[517]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[517]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[518]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[518]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[519]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[519]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[51]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[51]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[520]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[520]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[521]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[521]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[522]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[522]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[523]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[523]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[524]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[524]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[525]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[525]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[526]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[526]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[527]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[527]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[528]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[528]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[529]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[529]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[52]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[52]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[530]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[530]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[531]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[531]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[532]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[532]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[533]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[533]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[534]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[534]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[535]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[535]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[536]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[536]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[537]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[537]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[538]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[538]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[539]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[539]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[53]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[53]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[540]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[540]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[541]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[541]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[542]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[542]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[543]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[543]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[544]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[544]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[545]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[545]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[546]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[546]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[547]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[547]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[548]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[548]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[549]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[549]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[54]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[54]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[550]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[550]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[551]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[551]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[552]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[552]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[553]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[553]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[554]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[554]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[555]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[555]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[556]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[556]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[557]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[557]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[558]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[558]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[559]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[559]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[55]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[55]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[560]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[560]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[561]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[561]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[56]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[56]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[57]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[57]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[58]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[58]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[59]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[59]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[5]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[5]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[60]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[60]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[61]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[61]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[62]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[62]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[63]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[63]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[64]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[64]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[65]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[65]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[66]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[66]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[67]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[67]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[68]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[68]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[69]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[69]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[6]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[6]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[70]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[70]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[71]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[71]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[72]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[72]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[73]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[73]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[74]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[74]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[75]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[75]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[76]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[76]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[77]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[77]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[78]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[78]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[79]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[79]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[7]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[7]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[80]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[80]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[81]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[81]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[82]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[82]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[83]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[83]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[84]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[84]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[85]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[85]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[86]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[86]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[87]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[87]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[88]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[88]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[89]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[89]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[8]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[8]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[90]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[90]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[91]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[91]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[92]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[92]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[93]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[93]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[94]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[94]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[95]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[95]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[96]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[96]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[97]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[97]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[98]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[98]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[99]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[99]$_DFF_PN0_/SETN}]\
           [get_pins {u_st.u.o[9]$_DFF_PN0_/RESETN}]\
           [get_pins {u_st.u.o[9]$_DFF_PN0_/SETN}]]
###############################################################################
# Environment
###############################################################################
set_input_transition 150.0000 [get_ports {rs}]
set_input_transition 150.0000 [get_ports {i[561]}]
set_input_transition 150.0000 [get_ports {i[560]}]
set_input_transition 150.0000 [get_ports {i[559]}]
set_input_transition 150.0000 [get_ports {i[558]}]
set_input_transition 150.0000 [get_ports {i[557]}]
set_input_transition 150.0000 [get_ports {i[556]}]
set_input_transition 150.0000 [get_ports {i[555]}]
set_input_transition 150.0000 [get_ports {i[554]}]
set_input_transition 150.0000 [get_ports {i[553]}]
set_input_transition 150.0000 [get_ports {i[552]}]
set_input_transition 150.0000 [get_ports {i[551]}]
set_input_transition 150.0000 [get_ports {i[550]}]
set_input_transition 150.0000 [get_ports {i[549]}]
set_input_transition 150.0000 [get_ports {i[548]}]
set_input_transition 150.0000 [get_ports {i[547]}]
set_input_transition 150.0000 [get_ports {i[546]}]
set_input_transition 150.0000 [get_ports {i[545]}]
set_input_transition 150.0000 [get_ports {i[544]}]
set_input_transition 150.0000 [get_ports {i[543]}]
set_input_transition 150.0000 [get_ports {i[542]}]
set_input_transition 150.0000 [get_ports {i[541]}]
set_input_transition 150.0000 [get_ports {i[540]}]
set_input_transition 150.0000 [get_ports {i[539]}]
set_input_transition 150.0000 [get_ports {i[538]}]
set_input_transition 150.0000 [get_ports {i[537]}]
set_input_transition 150.0000 [get_ports {i[536]}]
set_input_transition 150.0000 [get_ports {i[535]}]
set_input_transition 150.0000 [get_ports {i[534]}]
set_input_transition 150.0000 [get_ports {i[533]}]
set_input_transition 150.0000 [get_ports {i[532]}]
set_input_transition 150.0000 [get_ports {i[531]}]
set_input_transition 150.0000 [get_ports {i[530]}]
set_input_transition 150.0000 [get_ports {i[529]}]
set_input_transition 150.0000 [get_ports {i[528]}]
set_input_transition 150.0000 [get_ports {i[527]}]
set_input_transition 150.0000 [get_ports {i[526]}]
set_input_transition 150.0000 [get_ports {i[525]}]
set_input_transition 150.0000 [get_ports {i[524]}]
set_input_transition 150.0000 [get_ports {i[523]}]
set_input_transition 150.0000 [get_ports {i[522]}]
set_input_transition 150.0000 [get_ports {i[521]}]
set_input_transition 150.0000 [get_ports {i[520]}]
set_input_transition 150.0000 [get_ports {i[519]}]
set_input_transition 150.0000 [get_ports {i[518]}]
set_input_transition 150.0000 [get_ports {i[517]}]
set_input_transition 150.0000 [get_ports {i[516]}]
set_input_transition 150.0000 [get_ports {i[515]}]
set_input_transition 150.0000 [get_ports {i[514]}]
set_input_transition 150.0000 [get_ports {i[513]}]
set_input_transition 150.0000 [get_ports {i[512]}]
set_input_transition 150.0000 [get_ports {i[511]}]
set_input_transition 150.0000 [get_ports {i[510]}]
set_input_transition 150.0000 [get_ports {i[509]}]
set_input_transition 150.0000 [get_ports {i[508]}]
set_input_transition 150.0000 [get_ports {i[507]}]
set_input_transition 150.0000 [get_ports {i[506]}]
set_input_transition 150.0000 [get_ports {i[505]}]
set_input_transition 150.0000 [get_ports {i[504]}]
set_input_transition 150.0000 [get_ports {i[503]}]
set_input_transition 150.0000 [get_ports {i[502]}]
set_input_transition 150.0000 [get_ports {i[501]}]
set_input_transition 150.0000 [get_ports {i[500]}]
set_input_transition 150.0000 [get_ports {i[499]}]
set_input_transition 150.0000 [get_ports {i[498]}]
set_input_transition 150.0000 [get_ports {i[497]}]
set_input_transition 150.0000 [get_ports {i[496]}]
set_input_transition 150.0000 [get_ports {i[495]}]
set_input_transition 150.0000 [get_ports {i[494]}]
set_input_transition 150.0000 [get_ports {i[493]}]
set_input_transition 150.0000 [get_ports {i[492]}]
set_input_transition 150.0000 [get_ports {i[491]}]
set_input_transition 150.0000 [get_ports {i[490]}]
set_input_transition 150.0000 [get_ports {i[489]}]
set_input_transition 150.0000 [get_ports {i[488]}]
set_input_transition 150.0000 [get_ports {i[487]}]
set_input_transition 150.0000 [get_ports {i[486]}]
set_input_transition 150.0000 [get_ports {i[485]}]
set_input_transition 150.0000 [get_ports {i[484]}]
set_input_transition 150.0000 [get_ports {i[483]}]
set_input_transition 150.0000 [get_ports {i[482]}]
set_input_transition 150.0000 [get_ports {i[481]}]
set_input_transition 150.0000 [get_ports {i[480]}]
set_input_transition 150.0000 [get_ports {i[479]}]
set_input_transition 150.0000 [get_ports {i[478]}]
set_input_transition 150.0000 [get_ports {i[477]}]
set_input_transition 150.0000 [get_ports {i[476]}]
set_input_transition 150.0000 [get_ports {i[475]}]
set_input_transition 150.0000 [get_ports {i[474]}]
set_input_transition 150.0000 [get_ports {i[473]}]
set_input_transition 150.0000 [get_ports {i[472]}]
set_input_transition 150.0000 [get_ports {i[471]}]
set_input_transition 150.0000 [get_ports {i[470]}]
set_input_transition 150.0000 [get_ports {i[469]}]
set_input_transition 150.0000 [get_ports {i[468]}]
set_input_transition 150.0000 [get_ports {i[467]}]
set_input_transition 150.0000 [get_ports {i[466]}]
set_input_transition 150.0000 [get_ports {i[465]}]
set_input_transition 150.0000 [get_ports {i[464]}]
set_input_transition 150.0000 [get_ports {i[463]}]
set_input_transition 150.0000 [get_ports {i[462]}]
set_input_transition 150.0000 [get_ports {i[461]}]
set_input_transition 150.0000 [get_ports {i[460]}]
set_input_transition 150.0000 [get_ports {i[459]}]
set_input_transition 150.0000 [get_ports {i[458]}]
set_input_transition 150.0000 [get_ports {i[457]}]
set_input_transition 150.0000 [get_ports {i[456]}]
set_input_transition 150.0000 [get_ports {i[455]}]
set_input_transition 150.0000 [get_ports {i[454]}]
set_input_transition 150.0000 [get_ports {i[453]}]
set_input_transition 150.0000 [get_ports {i[452]}]
set_input_transition 150.0000 [get_ports {i[451]}]
set_input_transition 150.0000 [get_ports {i[450]}]
set_input_transition 150.0000 [get_ports {i[449]}]
set_input_transition 150.0000 [get_ports {i[448]}]
set_input_transition 150.0000 [get_ports {i[447]}]
set_input_transition 150.0000 [get_ports {i[446]}]
set_input_transition 150.0000 [get_ports {i[445]}]
set_input_transition 150.0000 [get_ports {i[444]}]
set_input_transition 150.0000 [get_ports {i[443]}]
set_input_transition 150.0000 [get_ports {i[442]}]
set_input_transition 150.0000 [get_ports {i[441]}]
set_input_transition 150.0000 [get_ports {i[440]}]
set_input_transition 150.0000 [get_ports {i[439]}]
set_input_transition 150.0000 [get_ports {i[438]}]
set_input_transition 150.0000 [get_ports {i[437]}]
set_input_transition 150.0000 [get_ports {i[436]}]
set_input_transition 150.0000 [get_ports {i[435]}]
set_input_transition 150.0000 [get_ports {i[434]}]
set_input_transition 150.0000 [get_ports {i[433]}]
set_input_transition 150.0000 [get_ports {i[432]}]
set_input_transition 150.0000 [get_ports {i[431]}]
set_input_transition 150.0000 [get_ports {i[430]}]
set_input_transition 150.0000 [get_ports {i[429]}]
set_input_transition 150.0000 [get_ports {i[428]}]
set_input_transition 150.0000 [get_ports {i[427]}]
set_input_transition 150.0000 [get_ports {i[426]}]
set_input_transition 150.0000 [get_ports {i[425]}]
set_input_transition 150.0000 [get_ports {i[424]}]
set_input_transition 150.0000 [get_ports {i[423]}]
set_input_transition 150.0000 [get_ports {i[422]}]
set_input_transition 150.0000 [get_ports {i[421]}]
set_input_transition 150.0000 [get_ports {i[420]}]
set_input_transition 150.0000 [get_ports {i[419]}]
set_input_transition 150.0000 [get_ports {i[418]}]
set_input_transition 150.0000 [get_ports {i[417]}]
set_input_transition 150.0000 [get_ports {i[416]}]
set_input_transition 150.0000 [get_ports {i[415]}]
set_input_transition 150.0000 [get_ports {i[414]}]
set_input_transition 150.0000 [get_ports {i[413]}]
set_input_transition 150.0000 [get_ports {i[412]}]
set_input_transition 150.0000 [get_ports {i[411]}]
set_input_transition 150.0000 [get_ports {i[410]}]
set_input_transition 150.0000 [get_ports {i[409]}]
set_input_transition 150.0000 [get_ports {i[408]}]
set_input_transition 150.0000 [get_ports {i[407]}]
set_input_transition 150.0000 [get_ports {i[406]}]
set_input_transition 150.0000 [get_ports {i[405]}]
set_input_transition 150.0000 [get_ports {i[404]}]
set_input_transition 150.0000 [get_ports {i[403]}]
set_input_transition 150.0000 [get_ports {i[402]}]
set_input_transition 150.0000 [get_ports {i[401]}]
set_input_transition 150.0000 [get_ports {i[400]}]
set_input_transition 150.0000 [get_ports {i[399]}]
set_input_transition 150.0000 [get_ports {i[398]}]
set_input_transition 150.0000 [get_ports {i[397]}]
set_input_transition 150.0000 [get_ports {i[396]}]
set_input_transition 150.0000 [get_ports {i[395]}]
set_input_transition 150.0000 [get_ports {i[394]}]
set_input_transition 150.0000 [get_ports {i[393]}]
set_input_transition 150.0000 [get_ports {i[392]}]
set_input_transition 150.0000 [get_ports {i[391]}]
set_input_transition 150.0000 [get_ports {i[390]}]
set_input_transition 150.0000 [get_ports {i[389]}]
set_input_transition 150.0000 [get_ports {i[388]}]
set_input_transition 150.0000 [get_ports {i[387]}]
set_input_transition 150.0000 [get_ports {i[386]}]
set_input_transition 150.0000 [get_ports {i[385]}]
set_input_transition 150.0000 [get_ports {i[384]}]
set_input_transition 150.0000 [get_ports {i[383]}]
set_input_transition 150.0000 [get_ports {i[382]}]
set_input_transition 150.0000 [get_ports {i[381]}]
set_input_transition 150.0000 [get_ports {i[380]}]
set_input_transition 150.0000 [get_ports {i[379]}]
set_input_transition 150.0000 [get_ports {i[378]}]
set_input_transition 150.0000 [get_ports {i[377]}]
set_input_transition 150.0000 [get_ports {i[376]}]
set_input_transition 150.0000 [get_ports {i[375]}]
set_input_transition 150.0000 [get_ports {i[374]}]
set_input_transition 150.0000 [get_ports {i[373]}]
set_input_transition 150.0000 [get_ports {i[372]}]
set_input_transition 150.0000 [get_ports {i[371]}]
set_input_transition 150.0000 [get_ports {i[370]}]
set_input_transition 150.0000 [get_ports {i[369]}]
set_input_transition 150.0000 [get_ports {i[368]}]
set_input_transition 150.0000 [get_ports {i[367]}]
set_input_transition 150.0000 [get_ports {i[366]}]
set_input_transition 150.0000 [get_ports {i[365]}]
set_input_transition 150.0000 [get_ports {i[364]}]
set_input_transition 150.0000 [get_ports {i[363]}]
set_input_transition 150.0000 [get_ports {i[362]}]
set_input_transition 150.0000 [get_ports {i[361]}]
set_input_transition 150.0000 [get_ports {i[360]}]
set_input_transition 150.0000 [get_ports {i[359]}]
set_input_transition 150.0000 [get_ports {i[358]}]
set_input_transition 150.0000 [get_ports {i[357]}]
set_input_transition 150.0000 [get_ports {i[356]}]
set_input_transition 150.0000 [get_ports {i[355]}]
set_input_transition 150.0000 [get_ports {i[354]}]
set_input_transition 150.0000 [get_ports {i[353]}]
set_input_transition 150.0000 [get_ports {i[352]}]
set_input_transition 150.0000 [get_ports {i[351]}]
set_input_transition 150.0000 [get_ports {i[350]}]
set_input_transition 150.0000 [get_ports {i[349]}]
set_input_transition 150.0000 [get_ports {i[348]}]
set_input_transition 150.0000 [get_ports {i[347]}]
set_input_transition 150.0000 [get_ports {i[346]}]
set_input_transition 150.0000 [get_ports {i[345]}]
set_input_transition 150.0000 [get_ports {i[344]}]
set_input_transition 150.0000 [get_ports {i[343]}]
set_input_transition 150.0000 [get_ports {i[342]}]
set_input_transition 150.0000 [get_ports {i[341]}]
set_input_transition 150.0000 [get_ports {i[340]}]
set_input_transition 150.0000 [get_ports {i[339]}]
set_input_transition 150.0000 [get_ports {i[338]}]
set_input_transition 150.0000 [get_ports {i[337]}]
set_input_transition 150.0000 [get_ports {i[336]}]
set_input_transition 150.0000 [get_ports {i[335]}]
set_input_transition 150.0000 [get_ports {i[334]}]
set_input_transition 150.0000 [get_ports {i[333]}]
set_input_transition 150.0000 [get_ports {i[332]}]
set_input_transition 150.0000 [get_ports {i[331]}]
set_input_transition 150.0000 [get_ports {i[330]}]
set_input_transition 150.0000 [get_ports {i[329]}]
set_input_transition 150.0000 [get_ports {i[328]}]
set_input_transition 150.0000 [get_ports {i[327]}]
set_input_transition 150.0000 [get_ports {i[326]}]
set_input_transition 150.0000 [get_ports {i[325]}]
set_input_transition 150.0000 [get_ports {i[324]}]
set_input_transition 150.0000 [get_ports {i[323]}]
set_input_transition 150.0000 [get_ports {i[322]}]
set_input_transition 150.0000 [get_ports {i[321]}]
set_input_transition 150.0000 [get_ports {i[320]}]
set_input_transition 150.0000 [get_ports {i[319]}]
set_input_transition 150.0000 [get_ports {i[318]}]
set_input_transition 150.0000 [get_ports {i[317]}]
set_input_transition 150.0000 [get_ports {i[316]}]
set_input_transition 150.0000 [get_ports {i[315]}]
set_input_transition 150.0000 [get_ports {i[314]}]
set_input_transition 150.0000 [get_ports {i[313]}]
set_input_transition 150.0000 [get_ports {i[312]}]
set_input_transition 150.0000 [get_ports {i[311]}]
set_input_transition 150.0000 [get_ports {i[310]}]
set_input_transition 150.0000 [get_ports {i[309]}]
set_input_transition 150.0000 [get_ports {i[308]}]
set_input_transition 150.0000 [get_ports {i[307]}]
set_input_transition 150.0000 [get_ports {i[306]}]
set_input_transition 150.0000 [get_ports {i[305]}]
set_input_transition 150.0000 [get_ports {i[304]}]
set_input_transition 150.0000 [get_ports {i[303]}]
set_input_transition 150.0000 [get_ports {i[302]}]
set_input_transition 150.0000 [get_ports {i[301]}]
set_input_transition 150.0000 [get_ports {i[300]}]
set_input_transition 150.0000 [get_ports {i[299]}]
set_input_transition 150.0000 [get_ports {i[298]}]
set_input_transition 150.0000 [get_ports {i[297]}]
set_input_transition 150.0000 [get_ports {i[296]}]
set_input_transition 150.0000 [get_ports {i[295]}]
set_input_transition 150.0000 [get_ports {i[294]}]
set_input_transition 150.0000 [get_ports {i[293]}]
set_input_transition 150.0000 [get_ports {i[292]}]
set_input_transition 150.0000 [get_ports {i[291]}]
set_input_transition 150.0000 [get_ports {i[290]}]
set_input_transition 150.0000 [get_ports {i[289]}]
set_input_transition 150.0000 [get_ports {i[288]}]
set_input_transition 150.0000 [get_ports {i[287]}]
set_input_transition 150.0000 [get_ports {i[286]}]
set_input_transition 150.0000 [get_ports {i[285]}]
set_input_transition 150.0000 [get_ports {i[284]}]
set_input_transition 150.0000 [get_ports {i[283]}]
set_input_transition 150.0000 [get_ports {i[282]}]
set_input_transition 150.0000 [get_ports {i[281]}]
set_input_transition 150.0000 [get_ports {i[280]}]
set_input_transition 150.0000 [get_ports {i[279]}]
set_input_transition 150.0000 [get_ports {i[278]}]
set_input_transition 150.0000 [get_ports {i[277]}]
set_input_transition 150.0000 [get_ports {i[276]}]
set_input_transition 150.0000 [get_ports {i[275]}]
set_input_transition 150.0000 [get_ports {i[274]}]
set_input_transition 150.0000 [get_ports {i[273]}]
set_input_transition 150.0000 [get_ports {i[272]}]
set_input_transition 150.0000 [get_ports {i[271]}]
set_input_transition 150.0000 [get_ports {i[270]}]
set_input_transition 150.0000 [get_ports {i[269]}]
set_input_transition 150.0000 [get_ports {i[268]}]
set_input_transition 150.0000 [get_ports {i[267]}]
set_input_transition 150.0000 [get_ports {i[266]}]
set_input_transition 150.0000 [get_ports {i[265]}]
set_input_transition 150.0000 [get_ports {i[264]}]
set_input_transition 150.0000 [get_ports {i[263]}]
set_input_transition 150.0000 [get_ports {i[262]}]
set_input_transition 150.0000 [get_ports {i[261]}]
set_input_transition 150.0000 [get_ports {i[260]}]
set_input_transition 150.0000 [get_ports {i[259]}]
set_input_transition 150.0000 [get_ports {i[258]}]
set_input_transition 150.0000 [get_ports {i[257]}]
set_input_transition 150.0000 [get_ports {i[256]}]
set_input_transition 150.0000 [get_ports {i[255]}]
set_input_transition 150.0000 [get_ports {i[254]}]
set_input_transition 150.0000 [get_ports {i[253]}]
set_input_transition 150.0000 [get_ports {i[252]}]
set_input_transition 150.0000 [get_ports {i[251]}]
set_input_transition 150.0000 [get_ports {i[250]}]
set_input_transition 150.0000 [get_ports {i[249]}]
set_input_transition 150.0000 [get_ports {i[248]}]
set_input_transition 150.0000 [get_ports {i[247]}]
set_input_transition 150.0000 [get_ports {i[246]}]
set_input_transition 150.0000 [get_ports {i[245]}]
set_input_transition 150.0000 [get_ports {i[244]}]
set_input_transition 150.0000 [get_ports {i[243]}]
set_input_transition 150.0000 [get_ports {i[242]}]
set_input_transition 150.0000 [get_ports {i[241]}]
set_input_transition 150.0000 [get_ports {i[240]}]
set_input_transition 150.0000 [get_ports {i[239]}]
set_input_transition 150.0000 [get_ports {i[238]}]
set_input_transition 150.0000 [get_ports {i[237]}]
set_input_transition 150.0000 [get_ports {i[236]}]
set_input_transition 150.0000 [get_ports {i[235]}]
set_input_transition 150.0000 [get_ports {i[234]}]
set_input_transition 150.0000 [get_ports {i[233]}]
set_input_transition 150.0000 [get_ports {i[232]}]
set_input_transition 150.0000 [get_ports {i[231]}]
set_input_transition 150.0000 [get_ports {i[230]}]
set_input_transition 150.0000 [get_ports {i[229]}]
set_input_transition 150.0000 [get_ports {i[228]}]
set_input_transition 150.0000 [get_ports {i[227]}]
set_input_transition 150.0000 [get_ports {i[226]}]
set_input_transition 150.0000 [get_ports {i[225]}]
set_input_transition 150.0000 [get_ports {i[224]}]
set_input_transition 150.0000 [get_ports {i[223]}]
set_input_transition 150.0000 [get_ports {i[222]}]
set_input_transition 150.0000 [get_ports {i[221]}]
set_input_transition 150.0000 [get_ports {i[220]}]
set_input_transition 150.0000 [get_ports {i[219]}]
set_input_transition 150.0000 [get_ports {i[218]}]
set_input_transition 150.0000 [get_ports {i[217]}]
set_input_transition 150.0000 [get_ports {i[216]}]
set_input_transition 150.0000 [get_ports {i[215]}]
set_input_transition 150.0000 [get_ports {i[214]}]
set_input_transition 150.0000 [get_ports {i[213]}]
set_input_transition 150.0000 [get_ports {i[212]}]
set_input_transition 150.0000 [get_ports {i[211]}]
set_input_transition 150.0000 [get_ports {i[210]}]
set_input_transition 150.0000 [get_ports {i[209]}]
set_input_transition 150.0000 [get_ports {i[208]}]
set_input_transition 150.0000 [get_ports {i[207]}]
set_input_transition 150.0000 [get_ports {i[206]}]
set_input_transition 150.0000 [get_ports {i[205]}]
set_input_transition 150.0000 [get_ports {i[204]}]
set_input_transition 150.0000 [get_ports {i[203]}]
set_input_transition 150.0000 [get_ports {i[202]}]
set_input_transition 150.0000 [get_ports {i[201]}]
set_input_transition 150.0000 [get_ports {i[200]}]
set_input_transition 150.0000 [get_ports {i[199]}]
set_input_transition 150.0000 [get_ports {i[198]}]
set_input_transition 150.0000 [get_ports {i[197]}]
set_input_transition 150.0000 [get_ports {i[196]}]
set_input_transition 150.0000 [get_ports {i[195]}]
set_input_transition 150.0000 [get_ports {i[194]}]
set_input_transition 150.0000 [get_ports {i[193]}]
set_input_transition 150.0000 [get_ports {i[192]}]
set_input_transition 150.0000 [get_ports {i[191]}]
set_input_transition 150.0000 [get_ports {i[190]}]
set_input_transition 150.0000 [get_ports {i[189]}]
set_input_transition 150.0000 [get_ports {i[188]}]
set_input_transition 150.0000 [get_ports {i[187]}]
set_input_transition 150.0000 [get_ports {i[186]}]
set_input_transition 150.0000 [get_ports {i[185]}]
set_input_transition 150.0000 [get_ports {i[184]}]
set_input_transition 150.0000 [get_ports {i[183]}]
set_input_transition 150.0000 [get_ports {i[182]}]
set_input_transition 150.0000 [get_ports {i[181]}]
set_input_transition 150.0000 [get_ports {i[180]}]
set_input_transition 150.0000 [get_ports {i[179]}]
set_input_transition 150.0000 [get_ports {i[178]}]
set_input_transition 150.0000 [get_ports {i[177]}]
set_input_transition 150.0000 [get_ports {i[176]}]
set_input_transition 150.0000 [get_ports {i[175]}]
set_input_transition 150.0000 [get_ports {i[174]}]
set_input_transition 150.0000 [get_ports {i[173]}]
set_input_transition 150.0000 [get_ports {i[172]}]
set_input_transition 150.0000 [get_ports {i[171]}]
set_input_transition 150.0000 [get_ports {i[170]}]
set_input_transition 150.0000 [get_ports {i[169]}]
set_input_transition 150.0000 [get_ports {i[168]}]
set_input_transition 150.0000 [get_ports {i[167]}]
set_input_transition 150.0000 [get_ports {i[166]}]
set_input_transition 150.0000 [get_ports {i[165]}]
set_input_transition 150.0000 [get_ports {i[164]}]
set_input_transition 150.0000 [get_ports {i[163]}]
set_input_transition 150.0000 [get_ports {i[162]}]
set_input_transition 150.0000 [get_ports {i[161]}]
set_input_transition 150.0000 [get_ports {i[160]}]
set_input_transition 150.0000 [get_ports {i[159]}]
set_input_transition 150.0000 [get_ports {i[158]}]
set_input_transition 150.0000 [get_ports {i[157]}]
set_input_transition 150.0000 [get_ports {i[156]}]
set_input_transition 150.0000 [get_ports {i[155]}]
set_input_transition 150.0000 [get_ports {i[154]}]
set_input_transition 150.0000 [get_ports {i[153]}]
set_input_transition 150.0000 [get_ports {i[152]}]
set_input_transition 150.0000 [get_ports {i[151]}]
set_input_transition 150.0000 [get_ports {i[150]}]
set_input_transition 150.0000 [get_ports {i[149]}]
set_input_transition 150.0000 [get_ports {i[148]}]
set_input_transition 150.0000 [get_ports {i[147]}]
set_input_transition 150.0000 [get_ports {i[146]}]
set_input_transition 150.0000 [get_ports {i[145]}]
set_input_transition 150.0000 [get_ports {i[144]}]
set_input_transition 150.0000 [get_ports {i[143]}]
set_input_transition 150.0000 [get_ports {i[142]}]
set_input_transition 150.0000 [get_ports {i[141]}]
set_input_transition 150.0000 [get_ports {i[140]}]
set_input_transition 150.0000 [get_ports {i[139]}]
set_input_transition 150.0000 [get_ports {i[138]}]
set_input_transition 150.0000 [get_ports {i[137]}]
set_input_transition 150.0000 [get_ports {i[136]}]
set_input_transition 150.0000 [get_ports {i[135]}]
set_input_transition 150.0000 [get_ports {i[134]}]
set_input_transition 150.0000 [get_ports {i[133]}]
set_input_transition 150.0000 [get_ports {i[132]}]
set_input_transition 150.0000 [get_ports {i[131]}]
set_input_transition 150.0000 [get_ports {i[130]}]
set_input_transition 150.0000 [get_ports {i[129]}]
set_input_transition 150.0000 [get_ports {i[128]}]
set_input_transition 150.0000 [get_ports {i[127]}]
set_input_transition 150.0000 [get_ports {i[126]}]
set_input_transition 150.0000 [get_ports {i[125]}]
set_input_transition 150.0000 [get_ports {i[124]}]
set_input_transition 150.0000 [get_ports {i[123]}]
set_input_transition 150.0000 [get_ports {i[122]}]
set_input_transition 150.0000 [get_ports {i[121]}]
set_input_transition 150.0000 [get_ports {i[120]}]
set_input_transition 150.0000 [get_ports {i[119]}]
set_input_transition 150.0000 [get_ports {i[118]}]
set_input_transition 150.0000 [get_ports {i[117]}]
set_input_transition 150.0000 [get_ports {i[116]}]
set_input_transition 150.0000 [get_ports {i[115]}]
set_input_transition 150.0000 [get_ports {i[114]}]
set_input_transition 150.0000 [get_ports {i[113]}]
set_input_transition 150.0000 [get_ports {i[112]}]
set_input_transition 150.0000 [get_ports {i[111]}]
set_input_transition 150.0000 [get_ports {i[110]}]
set_input_transition 150.0000 [get_ports {i[109]}]
set_input_transition 150.0000 [get_ports {i[108]}]
set_input_transition 150.0000 [get_ports {i[107]}]
set_input_transition 150.0000 [get_ports {i[106]}]
set_input_transition 150.0000 [get_ports {i[105]}]
set_input_transition 150.0000 [get_ports {i[104]}]
set_input_transition 150.0000 [get_ports {i[103]}]
set_input_transition 150.0000 [get_ports {i[102]}]
set_input_transition 150.0000 [get_ports {i[101]}]
set_input_transition 150.0000 [get_ports {i[100]}]
set_input_transition 150.0000 [get_ports {i[99]}]
set_input_transition 150.0000 [get_ports {i[98]}]
set_input_transition 150.0000 [get_ports {i[97]}]
set_input_transition 150.0000 [get_ports {i[96]}]
set_input_transition 150.0000 [get_ports {i[95]}]
set_input_transition 150.0000 [get_ports {i[94]}]
set_input_transition 150.0000 [get_ports {i[93]}]
set_input_transition 150.0000 [get_ports {i[92]}]
set_input_transition 150.0000 [get_ports {i[91]}]
set_input_transition 150.0000 [get_ports {i[90]}]
set_input_transition 150.0000 [get_ports {i[89]}]
set_input_transition 150.0000 [get_ports {i[88]}]
set_input_transition 150.0000 [get_ports {i[87]}]
set_input_transition 150.0000 [get_ports {i[86]}]
set_input_transition 150.0000 [get_ports {i[85]}]
set_input_transition 150.0000 [get_ports {i[84]}]
set_input_transition 150.0000 [get_ports {i[83]}]
set_input_transition 150.0000 [get_ports {i[82]}]
set_input_transition 150.0000 [get_ports {i[81]}]
set_input_transition 150.0000 [get_ports {i[80]}]
set_input_transition 150.0000 [get_ports {i[79]}]
set_input_transition 150.0000 [get_ports {i[78]}]
set_input_transition 150.0000 [get_ports {i[77]}]
set_input_transition 150.0000 [get_ports {i[76]}]
set_input_transition 150.0000 [get_ports {i[75]}]
set_input_transition 150.0000 [get_ports {i[74]}]
set_input_transition 150.0000 [get_ports {i[73]}]
set_input_transition 150.0000 [get_ports {i[72]}]
set_input_transition 150.0000 [get_ports {i[71]}]
set_input_transition 150.0000 [get_ports {i[70]}]
set_input_transition 150.0000 [get_ports {i[69]}]
set_input_transition 150.0000 [get_ports {i[68]}]
set_input_transition 150.0000 [get_ports {i[67]}]
set_input_transition 150.0000 [get_ports {i[66]}]
set_input_transition 150.0000 [get_ports {i[65]}]
set_input_transition 150.0000 [get_ports {i[64]}]
set_input_transition 150.0000 [get_ports {i[63]}]
set_input_transition 150.0000 [get_ports {i[62]}]
set_input_transition 150.0000 [get_ports {i[61]}]
set_input_transition 150.0000 [get_ports {i[60]}]
set_input_transition 150.0000 [get_ports {i[59]}]
set_input_transition 150.0000 [get_ports {i[58]}]
set_input_transition 150.0000 [get_ports {i[57]}]
set_input_transition 150.0000 [get_ports {i[56]}]
set_input_transition 150.0000 [get_ports {i[55]}]
set_input_transition 150.0000 [get_ports {i[54]}]
set_input_transition 150.0000 [get_ports {i[53]}]
set_input_transition 150.0000 [get_ports {i[52]}]
set_input_transition 150.0000 [get_ports {i[51]}]
set_input_transition 150.0000 [get_ports {i[50]}]
set_input_transition 150.0000 [get_ports {i[49]}]
set_input_transition 150.0000 [get_ports {i[48]}]
set_input_transition 150.0000 [get_ports {i[47]}]
set_input_transition 150.0000 [get_ports {i[46]}]
set_input_transition 150.0000 [get_ports {i[45]}]
set_input_transition 150.0000 [get_ports {i[44]}]
set_input_transition 150.0000 [get_ports {i[43]}]
set_input_transition 150.0000 [get_ports {i[42]}]
set_input_transition 150.0000 [get_ports {i[41]}]
set_input_transition 150.0000 [get_ports {i[40]}]
set_input_transition 150.0000 [get_ports {i[39]}]
set_input_transition 150.0000 [get_ports {i[38]}]
set_input_transition 150.0000 [get_ports {i[37]}]
set_input_transition 150.0000 [get_ports {i[36]}]
set_input_transition 150.0000 [get_ports {i[35]}]
set_input_transition 150.0000 [get_ports {i[34]}]
set_input_transition 150.0000 [get_ports {i[33]}]
set_input_transition 150.0000 [get_ports {i[32]}]
set_input_transition 150.0000 [get_ports {i[31]}]
set_input_transition 150.0000 [get_ports {i[30]}]
set_input_transition 150.0000 [get_ports {i[29]}]
set_input_transition 150.0000 [get_ports {i[28]}]
set_input_transition 150.0000 [get_ports {i[27]}]
set_input_transition 150.0000 [get_ports {i[26]}]
set_input_transition 150.0000 [get_ports {i[25]}]
set_input_transition 150.0000 [get_ports {i[24]}]
set_input_transition 150.0000 [get_ports {i[23]}]
set_input_transition 150.0000 [get_ports {i[22]}]
set_input_transition 150.0000 [get_ports {i[21]}]
set_input_transition 150.0000 [get_ports {i[20]}]
set_input_transition 150.0000 [get_ports {i[19]}]
set_input_transition 150.0000 [get_ports {i[18]}]
set_input_transition 150.0000 [get_ports {i[17]}]
set_input_transition 150.0000 [get_ports {i[16]}]
set_input_transition 150.0000 [get_ports {i[15]}]
set_input_transition 150.0000 [get_ports {i[14]}]
set_input_transition 150.0000 [get_ports {i[13]}]
set_input_transition 150.0000 [get_ports {i[12]}]
set_input_transition 150.0000 [get_ports {i[11]}]
set_input_transition 150.0000 [get_ports {i[10]}]
set_input_transition 150.0000 [get_ports {i[9]}]
set_input_transition 150.0000 [get_ports {i[8]}]
set_input_transition 150.0000 [get_ports {i[7]}]
set_input_transition 150.0000 [get_ports {i[6]}]
set_input_transition 150.0000 [get_ports {i[5]}]
set_input_transition 150.0000 [get_ports {i[4]}]
set_input_transition 150.0000 [get_ports {i[3]}]
set_input_transition 150.0000 [get_ports {i[2]}]
set_input_transition 150.0000 [get_ports {i[1]}]
set_input_transition 150.0000 [get_ports {i[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_transition 260.0000 [current_design]
set_max_fanout 32.0000 [current_design]
