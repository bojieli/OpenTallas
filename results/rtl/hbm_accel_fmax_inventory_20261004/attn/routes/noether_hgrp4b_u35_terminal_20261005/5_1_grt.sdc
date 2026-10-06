###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_attn_hgrp_m4
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 833.0000 [get_ports {clk}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[3]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[4]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[5]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[6]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {gid[7]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[100]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[101]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[102]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[103]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[104]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[105]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[106]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[107]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[108]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[109]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[10]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[110]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[111]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[112]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[113]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[114]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[115]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[116]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[117]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[118]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[119]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[11]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[120]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[121]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[122]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[123]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[124]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[125]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[126]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[127]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[128]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[129]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[12]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[130]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[131]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[132]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[133]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[134]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[135]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[136]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[137]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[138]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[139]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[13]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[140]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[141]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[142]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[143]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[144]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[145]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[146]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[147]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[148]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[149]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[14]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[150]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[151]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[152]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[153]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[154]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[155]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[156]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[157]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[158]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[159]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[15]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[160]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[161]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[162]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[163]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[164]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[165]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[166]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[167]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[168]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[169]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[16]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[170]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[171]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[172]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[173]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[174]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[175]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[176]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[177]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[178]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[179]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[17]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[180]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[181]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[182]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[183]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[184]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[185]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[186]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[187]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[188]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[189]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[18]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[190]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[191]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[192]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[193]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[194]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[195]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[196]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[197]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[198]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[199]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[19]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[200]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[201]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[202]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[203]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[204]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[205]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[206]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[207]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[208]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[209]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[20]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[210]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[211]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[212]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[213]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[214]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[215]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[216]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[217]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[218]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[219]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[21]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[220]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[221]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[222]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[223]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[224]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[225]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[226]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[227]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[228]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[229]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[22]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[230]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[231]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[232]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[233]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[234]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[235]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[236]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[237]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[238]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[239]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[23]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[240]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[241]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[242]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[243]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[244]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[245]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[246]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[247]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[248]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[249]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[24]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[250]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[251]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[252]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[253]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[254]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[255]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[256]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[257]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[258]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[259]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[25]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[260]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[261]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[262]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[263]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[264]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[265]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[266]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[267]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[268]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[269]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[26]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[270]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[271]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[272]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[273]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[274]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[275]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[276]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[277]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[278]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[279]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[27]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[280]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[281]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[282]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[283]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[284]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[285]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[286]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[287]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[288]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[289]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[28]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[290]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[291]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[292]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[293]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[294]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[295]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[296]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[297]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[298]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[299]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[29]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[300]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[301]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[302]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[303]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[304]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[305]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[306]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[307]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[308]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[309]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[30]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[310]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[311]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[312]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[313]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[314]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[315]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[316]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[317]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[318]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[319]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[31]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[320]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[321]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[322]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[323]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[324]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[325]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[326]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[327]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[328]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[329]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[32]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[330]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[331]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[332]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[333]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[334]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[335]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[336]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[337]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[338]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[339]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[33]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[340]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[341]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[342]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[343]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[344]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[345]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[346]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[347]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[348]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[349]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[34]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[350]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[351]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[352]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[353]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[354]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[355]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[356]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[357]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[358]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[359]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[35]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[360]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[361]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[362]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[363]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[364]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[365]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[366]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[367]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[368]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[369]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[36]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[370]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[371]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[372]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[373]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[374]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[375]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[376]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[377]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[378]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[379]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[37]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[380]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[381]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[382]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[383]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[384]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[385]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[386]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[387]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[388]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[389]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[38]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[390]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[391]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[392]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[393]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[394]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[395]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[396]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[397]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[398]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[399]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[39]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[3]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[400]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[401]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[402]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[403]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[404]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[405]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[406]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[407]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[408]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[409]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[40]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[410]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[411]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[412]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[413]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[414]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[415]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[416]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[417]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[418]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[419]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[41]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[420]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[421]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[422]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[423]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[424]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[425]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[426]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[427]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[428]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[429]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[42]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[430]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[431]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[432]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[433]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[434]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[435]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[436]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[437]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[438]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[439]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[43]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[440]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[441]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[442]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[443]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[444]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[445]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[446]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[447]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[448]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[449]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[44]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[450]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[451]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[452]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[453]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[454]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[455]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[456]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[457]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[458]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[459]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[45]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[460]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[461]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[462]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[463]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[464]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[465]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[466]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[467]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[468]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[469]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[46]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[470]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[471]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[472]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[473]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[474]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[475]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[476]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[477]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[478]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[479]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[47]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[480]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[481]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[482]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[483]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[484]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[485]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[486]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[487]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[488]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[489]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[48]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[490]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[491]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[492]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[493]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[494]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[495]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[496]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[497]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[498]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[499]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[49]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[4]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[500]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[501]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[502]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[503]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[504]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[505]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[506]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[507]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[508]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[509]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[50]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[510]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[511]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[512]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[513]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[514]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[515]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[516]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[517]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[518]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[519]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[51]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[520]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[521]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[522]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[523]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[524]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[525]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[526]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[527]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[528]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[529]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[52]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[530]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[531]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[532]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[533]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[534]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[535]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[536]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[537]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[538]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[539]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[53]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[540]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[541]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[542]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[543]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[544]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[545]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[546]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[547]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[548]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[549]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[54]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[550]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[551]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[552]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[553]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[554]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[555]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[556]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[557]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[558]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[559]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[55]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[560]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[561]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[562]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[563]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[564]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[565]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[566]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[567]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[568]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[569]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[56]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[570]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[571]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[572]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[573]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[574]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[575]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[57]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[58]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[59]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[5]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[60]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[61]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[62]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[63]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[64]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[65]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[66]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[67]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[68]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[69]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[6]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[70]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[71]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[72]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[73]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[74]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[75]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[76]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[77]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[78]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[79]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[7]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[80]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[81]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[82]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[83]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[84]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[85]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[86]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[87]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[88]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[89]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[8]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[90]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[91]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[92]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[93]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[94]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[95]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[96]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[97]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[98]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[99]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ib[9]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ibank[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ibank[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ibank[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {iv}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_bank[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_bank[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_bank[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[3]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[4]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[5]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[6]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_grp[7]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_mode}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_v}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w2v}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[0]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1000]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1001]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1002]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1003]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1004]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1005]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1006]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1007]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1008]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1009]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[100]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1010]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1011]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1012]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1013]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1014]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1015]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1016]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1017]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1018]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1019]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[101]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1020]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1021]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1022]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1023]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[102]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[103]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[104]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[105]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[106]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[107]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[108]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[109]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[10]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[110]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[111]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[112]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[113]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[114]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[115]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[116]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[117]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[118]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[119]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[11]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[120]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[121]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[122]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[123]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[124]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[125]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[126]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[127]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[128]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[129]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[12]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[130]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[131]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[132]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[133]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[134]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[135]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[136]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[137]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[138]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[139]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[13]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[140]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[141]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[142]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[143]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[144]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[145]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[146]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[147]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[148]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[149]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[14]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[150]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[151]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[152]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[153]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[154]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[155]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[156]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[157]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[158]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[159]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[15]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[160]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[161]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[162]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[163]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[164]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[165]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[166]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[167]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[168]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[169]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[16]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[170]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[171]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[172]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[173]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[174]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[175]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[176]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[177]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[178]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[179]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[17]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[180]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[181]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[182]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[183]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[184]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[185]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[186]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[187]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[188]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[189]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[18]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[190]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[191]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[192]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[193]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[194]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[195]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[196]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[197]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[198]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[199]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[19]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[1]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[200]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[201]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[202]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[203]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[204]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[205]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[206]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[207]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[208]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[209]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[20]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[210]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[211]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[212]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[213]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[214]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[215]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[216]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[217]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[218]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[219]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[21]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[220]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[221]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[222]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[223]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[224]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[225]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[226]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[227]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[228]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[229]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[22]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[230]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[231]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[232]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[233]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[234]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[235]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[236]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[237]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[238]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[239]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[23]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[240]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[241]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[242]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[243]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[244]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[245]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[246]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[247]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[248]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[249]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[24]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[250]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[251]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[252]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[253]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[254]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[255]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[256]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[257]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[258]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[259]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[25]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[260]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[261]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[262]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[263]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[264]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[265]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[266]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[267]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[268]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[269]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[26]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[270]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[271]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[272]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[273]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[274]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[275]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[276]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[277]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[278]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[279]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[27]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[280]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[281]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[282]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[283]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[284]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[285]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[286]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[287]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[288]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[289]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[28]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[290]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[291]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[292]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[293]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[294]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[295]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[296]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[297]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[298]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[299]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[29]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[2]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[300]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[301]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[302]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[303]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[304]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[305]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[306]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[307]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[308]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[309]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[30]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[310]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[311]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[312]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[313]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[314]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[315]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[316]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[317]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[318]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[319]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[31]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[320]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[321]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[322]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[323]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[324]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[325]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[326]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[327]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[328]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[329]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[32]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[330]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[331]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[332]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[333]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[334]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[335]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[336]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[337]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[338]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[339]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[33]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[340]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[341]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[342]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[343]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[344]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[345]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[346]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[347]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[348]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[349]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[34]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[350]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[351]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[352]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[353]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[354]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[355]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[356]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[357]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[358]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[359]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[35]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[360]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[361]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[362]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[363]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[364]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[365]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[366]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[367]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[368]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[369]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[36]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[370]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[371]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[372]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[373]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[374]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[375]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[376]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[377]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[378]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[379]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[37]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[380]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[381]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[382]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[383]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[384]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[385]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[386]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[387]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[388]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[389]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[38]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[390]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[391]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[392]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[393]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[394]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[395]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[396]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[397]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[398]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[399]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[39]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[3]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[400]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[401]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[402]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[403]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[404]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[405]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[406]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[407]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[408]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[409]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[40]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[410]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[411]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[412]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[413]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[414]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[415]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[416]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[417]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[418]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[419]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[41]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[420]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[421]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[422]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[423]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[424]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[425]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[426]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[427]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[428]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[429]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[42]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[430]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[431]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[432]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[433]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[434]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[435]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[436]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[437]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[438]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[439]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[43]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[440]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[441]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[442]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[443]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[444]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[445]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[446]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[447]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[448]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[449]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[44]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[450]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[451]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[452]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[453]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[454]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[455]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[456]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[457]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[458]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[459]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[45]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[460]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[461]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[462]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[463]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[464]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[465]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[466]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[467]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[468]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[469]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[46]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[470]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[471]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[472]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[473]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[474]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[475]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[476]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[477]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[478]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[479]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[47]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[480]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[481]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[482]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[483]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[484]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[485]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[486]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[487]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[488]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[489]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[48]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[490]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[491]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[492]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[493]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[494]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[495]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[496]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[497]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[498]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[499]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[49]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[4]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[500]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[501]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[502]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[503]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[504]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[505]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[506]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[507]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[508]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[509]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[50]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[510]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[511]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[512]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[513]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[514]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[515]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[516]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[517]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[518]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[519]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[51]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[520]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[521]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[522]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[523]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[524]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[525]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[526]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[527]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[528]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[529]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[52]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[530]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[531]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[532]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[533]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[534]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[535]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[536]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[537]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[538]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[539]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[53]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[540]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[541]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[542]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[543]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[544]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[545]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[546]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[547]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[548]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[549]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[54]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[550]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[551]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[552]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[553]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[554]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[555]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[556]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[557]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[558]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[559]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[55]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[560]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[561]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[562]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[563]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[564]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[565]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[566]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[567]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[568]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[569]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[56]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[570]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[571]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[572]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[573]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[574]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[575]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[576]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[577]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[578]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[579]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[57]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[580]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[581]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[582]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[583]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[584]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[585]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[586]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[587]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[588]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[589]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[58]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[590]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[591]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[592]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[593]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[594]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[595]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[596]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[597]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[598]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[599]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[59]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[5]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[600]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[601]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[602]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[603]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[604]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[605]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[606]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[607]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[608]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[609]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[60]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[610]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[611]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[612]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[613]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[614]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[615]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[616]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[617]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[618]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[619]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[61]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[620]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[621]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[622]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[623]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[624]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[625]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[626]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[627]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[628]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[629]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[62]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[630]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[631]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[632]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[633]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[634]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[635]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[636]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[637]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[638]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[639]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[63]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[640]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[641]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[642]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[643]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[644]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[645]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[646]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[647]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[648]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[649]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[64]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[650]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[651]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[652]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[653]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[654]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[655]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[656]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[657]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[658]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[659]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[65]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[660]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[661]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[662]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[663]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[664]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[665]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[666]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[667]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[668]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[669]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[66]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[670]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[671]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[672]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[673]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[674]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[675]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[676]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[677]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[678]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[679]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[67]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[680]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[681]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[682]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[683]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[684]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[685]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[686]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[687]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[688]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[689]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[68]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[690]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[691]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[692]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[693]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[694]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[695]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[696]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[697]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[698]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[699]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[69]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[6]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[700]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[701]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[702]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[703]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[704]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[705]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[706]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[707]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[708]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[709]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[70]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[710]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[711]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[712]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[713]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[714]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[715]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[716]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[717]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[718]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[719]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[71]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[720]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[721]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[722]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[723]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[724]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[725]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[726]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[727]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[728]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[729]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[72]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[730]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[731]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[732]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[733]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[734]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[735]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[736]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[737]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[738]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[739]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[73]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[740]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[741]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[742]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[743]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[744]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[745]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[746]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[747]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[748]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[749]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[74]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[750]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[751]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[752]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[753]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[754]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[755]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[756]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[757]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[758]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[759]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[75]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[760]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[761]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[762]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[763]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[764]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[765]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[766]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[767]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[768]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[769]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[76]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[770]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[771]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[772]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[773]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[774]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[775]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[776]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[777]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[778]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[779]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[77]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[780]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[781]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[782]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[783]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[784]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[785]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[786]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[787]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[788]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[789]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[78]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[790]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[791]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[792]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[793]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[794]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[795]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[796]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[797]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[798]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[799]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[79]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[7]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[800]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[801]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[802]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[803]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[804]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[805]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[806]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[807]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[808]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[809]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[80]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[810]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[811]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[812]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[813]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[814]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[815]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[816]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[817]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[818]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[819]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[81]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[820]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[821]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[822]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[823]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[824]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[825]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[826]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[827]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[828]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[829]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[82]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[830]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[831]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[832]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[833]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[834]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[835]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[836]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[837]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[838]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[839]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[83]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[840]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[841]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[842]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[843]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[844]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[845]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[846]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[847]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[848]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[849]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[84]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[850]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[851]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[852]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[853]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[854]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[855]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[856]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[857]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[858]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[859]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[85]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[860]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[861]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[862]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[863]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[864]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[865]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[866]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[867]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[868]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[869]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[86]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[870]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[871]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[872]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[873]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[874]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[875]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[876]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[877]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[878]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[879]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[87]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[880]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[881]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[882]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[883]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[884]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[885]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[886]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[887]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[888]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[889]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[88]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[890]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[891]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[892]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[893]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[894]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[895]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[896]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[897]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[898]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[899]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[89]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[8]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[900]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[901]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[902]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[903]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[904]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[905]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[906]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[907]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[908]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[909]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[90]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[910]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[911]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[912]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[913]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[914]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[915]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[916]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[917]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[918]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[919]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[91]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[920]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[921]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[922]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[923]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[924]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[925]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[926]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[927]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[928]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[929]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[92]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[930]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[931]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[932]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[933]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[934]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[935]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[936]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[937]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[938]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[939]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[93]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[940]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[941]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[942]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[943]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[944]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[945]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[946]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[947]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[948]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[949]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[94]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[950]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[951]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[952]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[953]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[954]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[955]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[956]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[957]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[958]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[959]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[95]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[960]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[961]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[962]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[963]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[964]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[965]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[966]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[967]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[968]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[969]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[96]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[970]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[971]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[972]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[973]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[974]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[975]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[976]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[977]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[978]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[979]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[97]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[980]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[981]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[982]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[983]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[984]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[985]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[986]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[987]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[988]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[989]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[98]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[990]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[991]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[992]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[993]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[994]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[995]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[996]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[997]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[998]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[999]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[99]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ld_w[9]}]
set_input_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {rst_n}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oflt[0]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oflt[1]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oflt[2]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oflt[3]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {ov}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[0]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[100]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[101]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[102]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[103]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[104]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[105]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[106]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[107]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[108]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[109]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[10]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[110]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[111]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[112]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[113]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[114]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[115]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[116]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[117]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[118]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[119]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[11]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[120]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[121]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[122]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[123]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[124]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[125]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[126]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[127]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[12]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[13]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[14]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[15]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[16]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[17]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[18]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[19]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[1]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[20]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[21]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[22]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[23]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[24]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[25]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[26]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[27]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[28]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[29]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[2]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[30]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[31]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[32]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[33]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[34]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[35]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[36]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[37]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[38]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[39]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[3]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[40]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[41]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[42]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[43]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[44]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[45]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[46]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[47]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[48]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[49]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[4]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[50]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[51]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[52]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[53]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[54]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[55]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[56]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[57]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[58]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[59]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[5]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[60]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[61]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[62]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[63]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[64]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[65]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[66]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[67]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[68]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[69]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[6]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[70]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[71]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[72]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[73]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[74]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[75]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[76]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[77]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[78]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[79]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[7]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[80]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[81]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[82]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[83]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[84]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[85]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[86]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[87]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[88]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[89]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[8]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[90]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[91]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[92]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[93]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[94]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[95]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[96]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[97]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[98]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[99]}]
set_output_delay 166.6000 -clock [get_clocks {core_clk}] -add_delay [get_ports {oy[9]}]
set_false_path\
    -from [list [get_ports {gid[0]}]\
           [get_ports {gid[1]}]\
           [get_ports {gid[2]}]\
           [get_ports {gid[3]}]\
           [get_ports {gid[4]}]\
           [get_ports {gid[5]}]\
           [get_ports {gid[6]}]\
           [get_ports {gid[7]}]\
           [get_ports {ib[0]}]\
           [get_ports {ib[100]}]\
           [get_ports {ib[101]}]\
           [get_ports {ib[102]}]\
           [get_ports {ib[103]}]\
           [get_ports {ib[104]}]\
           [get_ports {ib[105]}]\
           [get_ports {ib[106]}]\
           [get_ports {ib[107]}]\
           [get_ports {ib[108]}]\
           [get_ports {ib[109]}]\
           [get_ports {ib[10]}]\
           [get_ports {ib[110]}]\
           [get_ports {ib[111]}]\
           [get_ports {ib[112]}]\
           [get_ports {ib[113]}]\
           [get_ports {ib[114]}]\
           [get_ports {ib[115]}]\
           [get_ports {ib[116]}]\
           [get_ports {ib[117]}]\
           [get_ports {ib[118]}]\
           [get_ports {ib[119]}]\
           [get_ports {ib[11]}]\
           [get_ports {ib[120]}]\
           [get_ports {ib[121]}]\
           [get_ports {ib[122]}]\
           [get_ports {ib[123]}]\
           [get_ports {ib[124]}]\
           [get_ports {ib[125]}]\
           [get_ports {ib[126]}]\
           [get_ports {ib[127]}]\
           [get_ports {ib[128]}]\
           [get_ports {ib[129]}]\
           [get_ports {ib[12]}]\
           [get_ports {ib[130]}]\
           [get_ports {ib[131]}]\
           [get_ports {ib[132]}]\
           [get_ports {ib[133]}]\
           [get_ports {ib[134]}]\
           [get_ports {ib[135]}]\
           [get_ports {ib[136]}]\
           [get_ports {ib[137]}]\
           [get_ports {ib[138]}]\
           [get_ports {ib[139]}]\
           [get_ports {ib[13]}]\
           [get_ports {ib[140]}]\
           [get_ports {ib[141]}]\
           [get_ports {ib[142]}]\
           [get_ports {ib[143]}]\
           [get_ports {ib[144]}]\
           [get_ports {ib[145]}]\
           [get_ports {ib[146]}]\
           [get_ports {ib[147]}]\
           [get_ports {ib[148]}]\
           [get_ports {ib[149]}]\
           [get_ports {ib[14]}]\
           [get_ports {ib[150]}]\
           [get_ports {ib[151]}]\
           [get_ports {ib[152]}]\
           [get_ports {ib[153]}]\
           [get_ports {ib[154]}]\
           [get_ports {ib[155]}]\
           [get_ports {ib[156]}]\
           [get_ports {ib[157]}]\
           [get_ports {ib[158]}]\
           [get_ports {ib[159]}]\
           [get_ports {ib[15]}]\
           [get_ports {ib[160]}]\
           [get_ports {ib[161]}]\
           [get_ports {ib[162]}]\
           [get_ports {ib[163]}]\
           [get_ports {ib[164]}]\
           [get_ports {ib[165]}]\
           [get_ports {ib[166]}]\
           [get_ports {ib[167]}]\
           [get_ports {ib[168]}]\
           [get_ports {ib[169]}]\
           [get_ports {ib[16]}]\
           [get_ports {ib[170]}]\
           [get_ports {ib[171]}]\
           [get_ports {ib[172]}]\
           [get_ports {ib[173]}]\
           [get_ports {ib[174]}]\
           [get_ports {ib[175]}]\
           [get_ports {ib[176]}]\
           [get_ports {ib[177]}]\
           [get_ports {ib[178]}]\
           [get_ports {ib[179]}]\
           [get_ports {ib[17]}]\
           [get_ports {ib[180]}]\
           [get_ports {ib[181]}]\
           [get_ports {ib[182]}]\
           [get_ports {ib[183]}]\
           [get_ports {ib[184]}]\
           [get_ports {ib[185]}]\
           [get_ports {ib[186]}]\
           [get_ports {ib[187]}]\
           [get_ports {ib[188]}]\
           [get_ports {ib[189]}]\
           [get_ports {ib[18]}]\
           [get_ports {ib[190]}]\
           [get_ports {ib[191]}]\
           [get_ports {ib[192]}]\
           [get_ports {ib[193]}]\
           [get_ports {ib[194]}]\
           [get_ports {ib[195]}]\
           [get_ports {ib[196]}]\
           [get_ports {ib[197]}]\
           [get_ports {ib[198]}]\
           [get_ports {ib[199]}]\
           [get_ports {ib[19]}]\
           [get_ports {ib[1]}]\
           [get_ports {ib[200]}]\
           [get_ports {ib[201]}]\
           [get_ports {ib[202]}]\
           [get_ports {ib[203]}]\
           [get_ports {ib[204]}]\
           [get_ports {ib[205]}]\
           [get_ports {ib[206]}]\
           [get_ports {ib[207]}]\
           [get_ports {ib[208]}]\
           [get_ports {ib[209]}]\
           [get_ports {ib[20]}]\
           [get_ports {ib[210]}]\
           [get_ports {ib[211]}]\
           [get_ports {ib[212]}]\
           [get_ports {ib[213]}]\
           [get_ports {ib[214]}]\
           [get_ports {ib[215]}]\
           [get_ports {ib[216]}]\
           [get_ports {ib[217]}]\
           [get_ports {ib[218]}]\
           [get_ports {ib[219]}]\
           [get_ports {ib[21]}]\
           [get_ports {ib[220]}]\
           [get_ports {ib[221]}]\
           [get_ports {ib[222]}]\
           [get_ports {ib[223]}]\
           [get_ports {ib[224]}]\
           [get_ports {ib[225]}]\
           [get_ports {ib[226]}]\
           [get_ports {ib[227]}]\
           [get_ports {ib[228]}]\
           [get_ports {ib[229]}]\
           [get_ports {ib[22]}]\
           [get_ports {ib[230]}]\
           [get_ports {ib[231]}]\
           [get_ports {ib[232]}]\
           [get_ports {ib[233]}]\
           [get_ports {ib[234]}]\
           [get_ports {ib[235]}]\
           [get_ports {ib[236]}]\
           [get_ports {ib[237]}]\
           [get_ports {ib[238]}]\
           [get_ports {ib[239]}]\
           [get_ports {ib[23]}]\
           [get_ports {ib[240]}]\
           [get_ports {ib[241]}]\
           [get_ports {ib[242]}]\
           [get_ports {ib[243]}]\
           [get_ports {ib[244]}]\
           [get_ports {ib[245]}]\
           [get_ports {ib[246]}]\
           [get_ports {ib[247]}]\
           [get_ports {ib[248]}]\
           [get_ports {ib[249]}]\
           [get_ports {ib[24]}]\
           [get_ports {ib[250]}]\
           [get_ports {ib[251]}]\
           [get_ports {ib[252]}]\
           [get_ports {ib[253]}]\
           [get_ports {ib[254]}]\
           [get_ports {ib[255]}]\
           [get_ports {ib[256]}]\
           [get_ports {ib[257]}]\
           [get_ports {ib[258]}]\
           [get_ports {ib[259]}]\
           [get_ports {ib[25]}]\
           [get_ports {ib[260]}]\
           [get_ports {ib[261]}]\
           [get_ports {ib[262]}]\
           [get_ports {ib[263]}]\
           [get_ports {ib[264]}]\
           [get_ports {ib[265]}]\
           [get_ports {ib[266]}]\
           [get_ports {ib[267]}]\
           [get_ports {ib[268]}]\
           [get_ports {ib[269]}]\
           [get_ports {ib[26]}]\
           [get_ports {ib[270]}]\
           [get_ports {ib[271]}]\
           [get_ports {ib[272]}]\
           [get_ports {ib[273]}]\
           [get_ports {ib[274]}]\
           [get_ports {ib[275]}]\
           [get_ports {ib[276]}]\
           [get_ports {ib[277]}]\
           [get_ports {ib[278]}]\
           [get_ports {ib[279]}]\
           [get_ports {ib[27]}]\
           [get_ports {ib[280]}]\
           [get_ports {ib[281]}]\
           [get_ports {ib[282]}]\
           [get_ports {ib[283]}]\
           [get_ports {ib[284]}]\
           [get_ports {ib[285]}]\
           [get_ports {ib[286]}]\
           [get_ports {ib[287]}]\
           [get_ports {ib[288]}]\
           [get_ports {ib[289]}]\
           [get_ports {ib[28]}]\
           [get_ports {ib[290]}]\
           [get_ports {ib[291]}]\
           [get_ports {ib[292]}]\
           [get_ports {ib[293]}]\
           [get_ports {ib[294]}]\
           [get_ports {ib[295]}]\
           [get_ports {ib[296]}]\
           [get_ports {ib[297]}]\
           [get_ports {ib[298]}]\
           [get_ports {ib[299]}]\
           [get_ports {ib[29]}]\
           [get_ports {ib[2]}]\
           [get_ports {ib[300]}]\
           [get_ports {ib[301]}]\
           [get_ports {ib[302]}]\
           [get_ports {ib[303]}]\
           [get_ports {ib[304]}]\
           [get_ports {ib[305]}]\
           [get_ports {ib[306]}]\
           [get_ports {ib[307]}]\
           [get_ports {ib[308]}]\
           [get_ports {ib[309]}]\
           [get_ports {ib[30]}]\
           [get_ports {ib[310]}]\
           [get_ports {ib[311]}]\
           [get_ports {ib[312]}]\
           [get_ports {ib[313]}]\
           [get_ports {ib[314]}]\
           [get_ports {ib[315]}]\
           [get_ports {ib[316]}]\
           [get_ports {ib[317]}]\
           [get_ports {ib[318]}]\
           [get_ports {ib[319]}]\
           [get_ports {ib[31]}]\
           [get_ports {ib[320]}]\
           [get_ports {ib[321]}]\
           [get_ports {ib[322]}]\
           [get_ports {ib[323]}]\
           [get_ports {ib[324]}]\
           [get_ports {ib[325]}]\
           [get_ports {ib[326]}]\
           [get_ports {ib[327]}]\
           [get_ports {ib[328]}]\
           [get_ports {ib[329]}]\
           [get_ports {ib[32]}]\
           [get_ports {ib[330]}]\
           [get_ports {ib[331]}]\
           [get_ports {ib[332]}]\
           [get_ports {ib[333]}]\
           [get_ports {ib[334]}]\
           [get_ports {ib[335]}]\
           [get_ports {ib[336]}]\
           [get_ports {ib[337]}]\
           [get_ports {ib[338]}]\
           [get_ports {ib[339]}]\
           [get_ports {ib[33]}]\
           [get_ports {ib[340]}]\
           [get_ports {ib[341]}]\
           [get_ports {ib[342]}]\
           [get_ports {ib[343]}]\
           [get_ports {ib[344]}]\
           [get_ports {ib[345]}]\
           [get_ports {ib[346]}]\
           [get_ports {ib[347]}]\
           [get_ports {ib[348]}]\
           [get_ports {ib[349]}]\
           [get_ports {ib[34]}]\
           [get_ports {ib[350]}]\
           [get_ports {ib[351]}]\
           [get_ports {ib[352]}]\
           [get_ports {ib[353]}]\
           [get_ports {ib[354]}]\
           [get_ports {ib[355]}]\
           [get_ports {ib[356]}]\
           [get_ports {ib[357]}]\
           [get_ports {ib[358]}]\
           [get_ports {ib[359]}]\
           [get_ports {ib[35]}]\
           [get_ports {ib[360]}]\
           [get_ports {ib[361]}]\
           [get_ports {ib[362]}]\
           [get_ports {ib[363]}]\
           [get_ports {ib[364]}]\
           [get_ports {ib[365]}]\
           [get_ports {ib[366]}]\
           [get_ports {ib[367]}]\
           [get_ports {ib[368]}]\
           [get_ports {ib[369]}]\
           [get_ports {ib[36]}]\
           [get_ports {ib[370]}]\
           [get_ports {ib[371]}]\
           [get_ports {ib[372]}]\
           [get_ports {ib[373]}]\
           [get_ports {ib[374]}]\
           [get_ports {ib[375]}]\
           [get_ports {ib[376]}]\
           [get_ports {ib[377]}]\
           [get_ports {ib[378]}]\
           [get_ports {ib[379]}]\
           [get_ports {ib[37]}]\
           [get_ports {ib[380]}]\
           [get_ports {ib[381]}]\
           [get_ports {ib[382]}]\
           [get_ports {ib[383]}]\
           [get_ports {ib[384]}]\
           [get_ports {ib[385]}]\
           [get_ports {ib[386]}]\
           [get_ports {ib[387]}]\
           [get_ports {ib[388]}]\
           [get_ports {ib[389]}]\
           [get_ports {ib[38]}]\
           [get_ports {ib[390]}]\
           [get_ports {ib[391]}]\
           [get_ports {ib[392]}]\
           [get_ports {ib[393]}]\
           [get_ports {ib[394]}]\
           [get_ports {ib[395]}]\
           [get_ports {ib[396]}]\
           [get_ports {ib[397]}]\
           [get_ports {ib[398]}]\
           [get_ports {ib[399]}]\
           [get_ports {ib[39]}]\
           [get_ports {ib[3]}]\
           [get_ports {ib[400]}]\
           [get_ports {ib[401]}]\
           [get_ports {ib[402]}]\
           [get_ports {ib[403]}]\
           [get_ports {ib[404]}]\
           [get_ports {ib[405]}]\
           [get_ports {ib[406]}]\
           [get_ports {ib[407]}]\
           [get_ports {ib[408]}]\
           [get_ports {ib[409]}]\
           [get_ports {ib[40]}]\
           [get_ports {ib[410]}]\
           [get_ports {ib[411]}]\
           [get_ports {ib[412]}]\
           [get_ports {ib[413]}]\
           [get_ports {ib[414]}]\
           [get_ports {ib[415]}]\
           [get_ports {ib[416]}]\
           [get_ports {ib[417]}]\
           [get_ports {ib[418]}]\
           [get_ports {ib[419]}]\
           [get_ports {ib[41]}]\
           [get_ports {ib[420]}]\
           [get_ports {ib[421]}]\
           [get_ports {ib[422]}]\
           [get_ports {ib[423]}]\
           [get_ports {ib[424]}]\
           [get_ports {ib[425]}]\
           [get_ports {ib[426]}]\
           [get_ports {ib[427]}]\
           [get_ports {ib[428]}]\
           [get_ports {ib[429]}]\
           [get_ports {ib[42]}]\
           [get_ports {ib[430]}]\
           [get_ports {ib[431]}]\
           [get_ports {ib[432]}]\
           [get_ports {ib[433]}]\
           [get_ports {ib[434]}]\
           [get_ports {ib[435]}]\
           [get_ports {ib[436]}]\
           [get_ports {ib[437]}]\
           [get_ports {ib[438]}]\
           [get_ports {ib[439]}]\
           [get_ports {ib[43]}]\
           [get_ports {ib[440]}]\
           [get_ports {ib[441]}]\
           [get_ports {ib[442]}]\
           [get_ports {ib[443]}]\
           [get_ports {ib[444]}]\
           [get_ports {ib[445]}]\
           [get_ports {ib[446]}]\
           [get_ports {ib[447]}]\
           [get_ports {ib[448]}]\
           [get_ports {ib[449]}]\
           [get_ports {ib[44]}]\
           [get_ports {ib[450]}]\
           [get_ports {ib[451]}]\
           [get_ports {ib[452]}]\
           [get_ports {ib[453]}]\
           [get_ports {ib[454]}]\
           [get_ports {ib[455]}]\
           [get_ports {ib[456]}]\
           [get_ports {ib[457]}]\
           [get_ports {ib[458]}]\
           [get_ports {ib[459]}]\
           [get_ports {ib[45]}]\
           [get_ports {ib[460]}]\
           [get_ports {ib[461]}]\
           [get_ports {ib[462]}]\
           [get_ports {ib[463]}]\
           [get_ports {ib[464]}]\
           [get_ports {ib[465]}]\
           [get_ports {ib[466]}]\
           [get_ports {ib[467]}]\
           [get_ports {ib[468]}]\
           [get_ports {ib[469]}]\
           [get_ports {ib[46]}]\
           [get_ports {ib[470]}]\
           [get_ports {ib[471]}]\
           [get_ports {ib[472]}]\
           [get_ports {ib[473]}]\
           [get_ports {ib[474]}]\
           [get_ports {ib[475]}]\
           [get_ports {ib[476]}]\
           [get_ports {ib[477]}]\
           [get_ports {ib[478]}]\
           [get_ports {ib[479]}]\
           [get_ports {ib[47]}]\
           [get_ports {ib[480]}]\
           [get_ports {ib[481]}]\
           [get_ports {ib[482]}]\
           [get_ports {ib[483]}]\
           [get_ports {ib[484]}]\
           [get_ports {ib[485]}]\
           [get_ports {ib[486]}]\
           [get_ports {ib[487]}]\
           [get_ports {ib[488]}]\
           [get_ports {ib[489]}]\
           [get_ports {ib[48]}]\
           [get_ports {ib[490]}]\
           [get_ports {ib[491]}]\
           [get_ports {ib[492]}]\
           [get_ports {ib[493]}]\
           [get_ports {ib[494]}]\
           [get_ports {ib[495]}]\
           [get_ports {ib[496]}]\
           [get_ports {ib[497]}]\
           [get_ports {ib[498]}]\
           [get_ports {ib[499]}]\
           [get_ports {ib[49]}]\
           [get_ports {ib[4]}]\
           [get_ports {ib[500]}]\
           [get_ports {ib[501]}]\
           [get_ports {ib[502]}]\
           [get_ports {ib[503]}]\
           [get_ports {ib[504]}]\
           [get_ports {ib[505]}]\
           [get_ports {ib[506]}]\
           [get_ports {ib[507]}]\
           [get_ports {ib[508]}]\
           [get_ports {ib[509]}]\
           [get_ports {ib[50]}]\
           [get_ports {ib[510]}]\
           [get_ports {ib[511]}]\
           [get_ports {ib[512]}]\
           [get_ports {ib[513]}]\
           [get_ports {ib[514]}]\
           [get_ports {ib[515]}]\
           [get_ports {ib[516]}]\
           [get_ports {ib[517]}]\
           [get_ports {ib[518]}]\
           [get_ports {ib[519]}]\
           [get_ports {ib[51]}]\
           [get_ports {ib[520]}]\
           [get_ports {ib[521]}]\
           [get_ports {ib[522]}]\
           [get_ports {ib[523]}]\
           [get_ports {ib[524]}]\
           [get_ports {ib[525]}]\
           [get_ports {ib[526]}]\
           [get_ports {ib[527]}]\
           [get_ports {ib[528]}]\
           [get_ports {ib[529]}]\
           [get_ports {ib[52]}]\
           [get_ports {ib[530]}]\
           [get_ports {ib[531]}]\
           [get_ports {ib[532]}]\
           [get_ports {ib[533]}]\
           [get_ports {ib[534]}]\
           [get_ports {ib[535]}]\
           [get_ports {ib[536]}]\
           [get_ports {ib[537]}]\
           [get_ports {ib[538]}]\
           [get_ports {ib[539]}]\
           [get_ports {ib[53]}]\
           [get_ports {ib[540]}]\
           [get_ports {ib[541]}]\
           [get_ports {ib[542]}]\
           [get_ports {ib[543]}]\
           [get_ports {ib[544]}]\
           [get_ports {ib[545]}]\
           [get_ports {ib[546]}]\
           [get_ports {ib[547]}]\
           [get_ports {ib[548]}]\
           [get_ports {ib[549]}]\
           [get_ports {ib[54]}]\
           [get_ports {ib[550]}]\
           [get_ports {ib[551]}]\
           [get_ports {ib[552]}]\
           [get_ports {ib[553]}]\
           [get_ports {ib[554]}]\
           [get_ports {ib[555]}]\
           [get_ports {ib[556]}]\
           [get_ports {ib[557]}]\
           [get_ports {ib[558]}]\
           [get_ports {ib[559]}]\
           [get_ports {ib[55]}]\
           [get_ports {ib[560]}]\
           [get_ports {ib[561]}]\
           [get_ports {ib[562]}]\
           [get_ports {ib[563]}]\
           [get_ports {ib[564]}]\
           [get_ports {ib[565]}]\
           [get_ports {ib[566]}]\
           [get_ports {ib[567]}]\
           [get_ports {ib[568]}]\
           [get_ports {ib[569]}]\
           [get_ports {ib[56]}]\
           [get_ports {ib[570]}]\
           [get_ports {ib[571]}]\
           [get_ports {ib[572]}]\
           [get_ports {ib[573]}]\
           [get_ports {ib[574]}]\
           [get_ports {ib[575]}]\
           [get_ports {ib[57]}]\
           [get_ports {ib[58]}]\
           [get_ports {ib[59]}]\
           [get_ports {ib[5]}]\
           [get_ports {ib[60]}]\
           [get_ports {ib[61]}]\
           [get_ports {ib[62]}]\
           [get_ports {ib[63]}]\
           [get_ports {ib[64]}]\
           [get_ports {ib[65]}]\
           [get_ports {ib[66]}]\
           [get_ports {ib[67]}]\
           [get_ports {ib[68]}]\
           [get_ports {ib[69]}]\
           [get_ports {ib[6]}]\
           [get_ports {ib[70]}]\
           [get_ports {ib[71]}]\
           [get_ports {ib[72]}]\
           [get_ports {ib[73]}]\
           [get_ports {ib[74]}]\
           [get_ports {ib[75]}]\
           [get_ports {ib[76]}]\
           [get_ports {ib[77]}]\
           [get_ports {ib[78]}]\
           [get_ports {ib[79]}]\
           [get_ports {ib[7]}]\
           [get_ports {ib[80]}]\
           [get_ports {ib[81]}]\
           [get_ports {ib[82]}]\
           [get_ports {ib[83]}]\
           [get_ports {ib[84]}]\
           [get_ports {ib[85]}]\
           [get_ports {ib[86]}]\
           [get_ports {ib[87]}]\
           [get_ports {ib[88]}]\
           [get_ports {ib[89]}]\
           [get_ports {ib[8]}]\
           [get_ports {ib[90]}]\
           [get_ports {ib[91]}]\
           [get_ports {ib[92]}]\
           [get_ports {ib[93]}]\
           [get_ports {ib[94]}]\
           [get_ports {ib[95]}]\
           [get_ports {ib[96]}]\
           [get_ports {ib[97]}]\
           [get_ports {ib[98]}]\
           [get_ports {ib[99]}]\
           [get_ports {ib[9]}]\
           [get_ports {ibank[0]}]\
           [get_ports {ibank[1]}]\
           [get_ports {ibank[2]}]\
           [get_ports {iv}]\
           [get_ports {ld_bank[0]}]\
           [get_ports {ld_bank[1]}]\
           [get_ports {ld_bank[2]}]\
           [get_ports {ld_grp[0]}]\
           [get_ports {ld_grp[1]}]\
           [get_ports {ld_grp[2]}]\
           [get_ports {ld_grp[3]}]\
           [get_ports {ld_grp[4]}]\
           [get_ports {ld_grp[5]}]\
           [get_ports {ld_grp[6]}]\
           [get_ports {ld_grp[7]}]\
           [get_ports {ld_mode}]\
           [get_ports {ld_v}]\
           [get_ports {ld_w2v}]\
           [get_ports {ld_w[0]}]\
           [get_ports {ld_w[1000]}]\
           [get_ports {ld_w[1001]}]\
           [get_ports {ld_w[1002]}]\
           [get_ports {ld_w[1003]}]\
           [get_ports {ld_w[1004]}]\
           [get_ports {ld_w[1005]}]\
           [get_ports {ld_w[1006]}]\
           [get_ports {ld_w[1007]}]\
           [get_ports {ld_w[1008]}]\
           [get_ports {ld_w[1009]}]\
           [get_ports {ld_w[100]}]\
           [get_ports {ld_w[1010]}]\
           [get_ports {ld_w[1011]}]\
           [get_ports {ld_w[1012]}]\
           [get_ports {ld_w[1013]}]\
           [get_ports {ld_w[1014]}]\
           [get_ports {ld_w[1015]}]\
           [get_ports {ld_w[1016]}]\
           [get_ports {ld_w[1017]}]\
           [get_ports {ld_w[1018]}]\
           [get_ports {ld_w[1019]}]\
           [get_ports {ld_w[101]}]\
           [get_ports {ld_w[1020]}]\
           [get_ports {ld_w[1021]}]\
           [get_ports {ld_w[1022]}]\
           [get_ports {ld_w[1023]}]\
           [get_ports {ld_w[102]}]\
           [get_ports {ld_w[103]}]\
           [get_ports {ld_w[104]}]\
           [get_ports {ld_w[105]}]\
           [get_ports {ld_w[106]}]\
           [get_ports {ld_w[107]}]\
           [get_ports {ld_w[108]}]\
           [get_ports {ld_w[109]}]\
           [get_ports {ld_w[10]}]\
           [get_ports {ld_w[110]}]\
           [get_ports {ld_w[111]}]\
           [get_ports {ld_w[112]}]\
           [get_ports {ld_w[113]}]\
           [get_ports {ld_w[114]}]\
           [get_ports {ld_w[115]}]\
           [get_ports {ld_w[116]}]\
           [get_ports {ld_w[117]}]\
           [get_ports {ld_w[118]}]\
           [get_ports {ld_w[119]}]\
           [get_ports {ld_w[11]}]\
           [get_ports {ld_w[120]}]\
           [get_ports {ld_w[121]}]\
           [get_ports {ld_w[122]}]\
           [get_ports {ld_w[123]}]\
           [get_ports {ld_w[124]}]\
           [get_ports {ld_w[125]}]\
           [get_ports {ld_w[126]}]\
           [get_ports {ld_w[127]}]\
           [get_ports {ld_w[128]}]\
           [get_ports {ld_w[129]}]\
           [get_ports {ld_w[12]}]\
           [get_ports {ld_w[130]}]\
           [get_ports {ld_w[131]}]\
           [get_ports {ld_w[132]}]\
           [get_ports {ld_w[133]}]\
           [get_ports {ld_w[134]}]\
           [get_ports {ld_w[135]}]\
           [get_ports {ld_w[136]}]\
           [get_ports {ld_w[137]}]\
           [get_ports {ld_w[138]}]\
           [get_ports {ld_w[139]}]\
           [get_ports {ld_w[13]}]\
           [get_ports {ld_w[140]}]\
           [get_ports {ld_w[141]}]\
           [get_ports {ld_w[142]}]\
           [get_ports {ld_w[143]}]\
           [get_ports {ld_w[144]}]\
           [get_ports {ld_w[145]}]\
           [get_ports {ld_w[146]}]\
           [get_ports {ld_w[147]}]\
           [get_ports {ld_w[148]}]\
           [get_ports {ld_w[149]}]\
           [get_ports {ld_w[14]}]\
           [get_ports {ld_w[150]}]\
           [get_ports {ld_w[151]}]\
           [get_ports {ld_w[152]}]\
           [get_ports {ld_w[153]}]\
           [get_ports {ld_w[154]}]\
           [get_ports {ld_w[155]}]\
           [get_ports {ld_w[156]}]\
           [get_ports {ld_w[157]}]\
           [get_ports {ld_w[158]}]\
           [get_ports {ld_w[159]}]\
           [get_ports {ld_w[15]}]\
           [get_ports {ld_w[160]}]\
           [get_ports {ld_w[161]}]\
           [get_ports {ld_w[162]}]\
           [get_ports {ld_w[163]}]\
           [get_ports {ld_w[164]}]\
           [get_ports {ld_w[165]}]\
           [get_ports {ld_w[166]}]\
           [get_ports {ld_w[167]}]\
           [get_ports {ld_w[168]}]\
           [get_ports {ld_w[169]}]\
           [get_ports {ld_w[16]}]\
           [get_ports {ld_w[170]}]\
           [get_ports {ld_w[171]}]\
           [get_ports {ld_w[172]}]\
           [get_ports {ld_w[173]}]\
           [get_ports {ld_w[174]}]\
           [get_ports {ld_w[175]}]\
           [get_ports {ld_w[176]}]\
           [get_ports {ld_w[177]}]\
           [get_ports {ld_w[178]}]\
           [get_ports {ld_w[179]}]\
           [get_ports {ld_w[17]}]\
           [get_ports {ld_w[180]}]\
           [get_ports {ld_w[181]}]\
           [get_ports {ld_w[182]}]\
           [get_ports {ld_w[183]}]\
           [get_ports {ld_w[184]}]\
           [get_ports {ld_w[185]}]\
           [get_ports {ld_w[186]}]\
           [get_ports {ld_w[187]}]\
           [get_ports {ld_w[188]}]\
           [get_ports {ld_w[189]}]\
           [get_ports {ld_w[18]}]\
           [get_ports {ld_w[190]}]\
           [get_ports {ld_w[191]}]\
           [get_ports {ld_w[192]}]\
           [get_ports {ld_w[193]}]\
           [get_ports {ld_w[194]}]\
           [get_ports {ld_w[195]}]\
           [get_ports {ld_w[196]}]\
           [get_ports {ld_w[197]}]\
           [get_ports {ld_w[198]}]\
           [get_ports {ld_w[199]}]\
           [get_ports {ld_w[19]}]\
           [get_ports {ld_w[1]}]\
           [get_ports {ld_w[200]}]\
           [get_ports {ld_w[201]}]\
           [get_ports {ld_w[202]}]\
           [get_ports {ld_w[203]}]\
           [get_ports {ld_w[204]}]\
           [get_ports {ld_w[205]}]\
           [get_ports {ld_w[206]}]\
           [get_ports {ld_w[207]}]\
           [get_ports {ld_w[208]}]\
           [get_ports {ld_w[209]}]\
           [get_ports {ld_w[20]}]\
           [get_ports {ld_w[210]}]\
           [get_ports {ld_w[211]}]\
           [get_ports {ld_w[212]}]\
           [get_ports {ld_w[213]}]\
           [get_ports {ld_w[214]}]\
           [get_ports {ld_w[215]}]\
           [get_ports {ld_w[216]}]\
           [get_ports {ld_w[217]}]\
           [get_ports {ld_w[218]}]\
           [get_ports {ld_w[219]}]\
           [get_ports {ld_w[21]}]\
           [get_ports {ld_w[220]}]\
           [get_ports {ld_w[221]}]\
           [get_ports {ld_w[222]}]\
           [get_ports {ld_w[223]}]\
           [get_ports {ld_w[224]}]\
           [get_ports {ld_w[225]}]\
           [get_ports {ld_w[226]}]\
           [get_ports {ld_w[227]}]\
           [get_ports {ld_w[228]}]\
           [get_ports {ld_w[229]}]\
           [get_ports {ld_w[22]}]\
           [get_ports {ld_w[230]}]\
           [get_ports {ld_w[231]}]\
           [get_ports {ld_w[232]}]\
           [get_ports {ld_w[233]}]\
           [get_ports {ld_w[234]}]\
           [get_ports {ld_w[235]}]\
           [get_ports {ld_w[236]}]\
           [get_ports {ld_w[237]}]\
           [get_ports {ld_w[238]}]\
           [get_ports {ld_w[239]}]\
           [get_ports {ld_w[23]}]\
           [get_ports {ld_w[240]}]\
           [get_ports {ld_w[241]}]\
           [get_ports {ld_w[242]}]\
           [get_ports {ld_w[243]}]\
           [get_ports {ld_w[244]}]\
           [get_ports {ld_w[245]}]\
           [get_ports {ld_w[246]}]\
           [get_ports {ld_w[247]}]\
           [get_ports {ld_w[248]}]\
           [get_ports {ld_w[249]}]\
           [get_ports {ld_w[24]}]\
           [get_ports {ld_w[250]}]\
           [get_ports {ld_w[251]}]\
           [get_ports {ld_w[252]}]\
           [get_ports {ld_w[253]}]\
           [get_ports {ld_w[254]}]\
           [get_ports {ld_w[255]}]\
           [get_ports {ld_w[256]}]\
           [get_ports {ld_w[257]}]\
           [get_ports {ld_w[258]}]\
           [get_ports {ld_w[259]}]\
           [get_ports {ld_w[25]}]\
           [get_ports {ld_w[260]}]\
           [get_ports {ld_w[261]}]\
           [get_ports {ld_w[262]}]\
           [get_ports {ld_w[263]}]\
           [get_ports {ld_w[264]}]\
           [get_ports {ld_w[265]}]\
           [get_ports {ld_w[266]}]\
           [get_ports {ld_w[267]}]\
           [get_ports {ld_w[268]}]\
           [get_ports {ld_w[269]}]\
           [get_ports {ld_w[26]}]\
           [get_ports {ld_w[270]}]\
           [get_ports {ld_w[271]}]\
           [get_ports {ld_w[272]}]\
           [get_ports {ld_w[273]}]\
           [get_ports {ld_w[274]}]\
           [get_ports {ld_w[275]}]\
           [get_ports {ld_w[276]}]\
           [get_ports {ld_w[277]}]\
           [get_ports {ld_w[278]}]\
           [get_ports {ld_w[279]}]\
           [get_ports {ld_w[27]}]\
           [get_ports {ld_w[280]}]\
           [get_ports {ld_w[281]}]\
           [get_ports {ld_w[282]}]\
           [get_ports {ld_w[283]}]\
           [get_ports {ld_w[284]}]\
           [get_ports {ld_w[285]}]\
           [get_ports {ld_w[286]}]\
           [get_ports {ld_w[287]}]\
           [get_ports {ld_w[288]}]\
           [get_ports {ld_w[289]}]\
           [get_ports {ld_w[28]}]\
           [get_ports {ld_w[290]}]\
           [get_ports {ld_w[291]}]\
           [get_ports {ld_w[292]}]\
           [get_ports {ld_w[293]}]\
           [get_ports {ld_w[294]}]\
           [get_ports {ld_w[295]}]\
           [get_ports {ld_w[296]}]\
           [get_ports {ld_w[297]}]\
           [get_ports {ld_w[298]}]\
           [get_ports {ld_w[299]}]\
           [get_ports {ld_w[29]}]\
           [get_ports {ld_w[2]}]\
           [get_ports {ld_w[300]}]\
           [get_ports {ld_w[301]}]\
           [get_ports {ld_w[302]}]\
           [get_ports {ld_w[303]}]\
           [get_ports {ld_w[304]}]\
           [get_ports {ld_w[305]}]\
           [get_ports {ld_w[306]}]\
           [get_ports {ld_w[307]}]\
           [get_ports {ld_w[308]}]\
           [get_ports {ld_w[309]}]\
           [get_ports {ld_w[30]}]\
           [get_ports {ld_w[310]}]\
           [get_ports {ld_w[311]}]\
           [get_ports {ld_w[312]}]\
           [get_ports {ld_w[313]}]\
           [get_ports {ld_w[314]}]\
           [get_ports {ld_w[315]}]\
           [get_ports {ld_w[316]}]\
           [get_ports {ld_w[317]}]\
           [get_ports {ld_w[318]}]\
           [get_ports {ld_w[319]}]\
           [get_ports {ld_w[31]}]\
           [get_ports {ld_w[320]}]\
           [get_ports {ld_w[321]}]\
           [get_ports {ld_w[322]}]\
           [get_ports {ld_w[323]}]\
           [get_ports {ld_w[324]}]\
           [get_ports {ld_w[325]}]\
           [get_ports {ld_w[326]}]\
           [get_ports {ld_w[327]}]\
           [get_ports {ld_w[328]}]\
           [get_ports {ld_w[329]}]\
           [get_ports {ld_w[32]}]\
           [get_ports {ld_w[330]}]\
           [get_ports {ld_w[331]}]\
           [get_ports {ld_w[332]}]\
           [get_ports {ld_w[333]}]\
           [get_ports {ld_w[334]}]\
           [get_ports {ld_w[335]}]\
           [get_ports {ld_w[336]}]\
           [get_ports {ld_w[337]}]\
           [get_ports {ld_w[338]}]\
           [get_ports {ld_w[339]}]\
           [get_ports {ld_w[33]}]\
           [get_ports {ld_w[340]}]\
           [get_ports {ld_w[341]}]\
           [get_ports {ld_w[342]}]\
           [get_ports {ld_w[343]}]\
           [get_ports {ld_w[344]}]\
           [get_ports {ld_w[345]}]\
           [get_ports {ld_w[346]}]\
           [get_ports {ld_w[347]}]\
           [get_ports {ld_w[348]}]\
           [get_ports {ld_w[349]}]\
           [get_ports {ld_w[34]}]\
           [get_ports {ld_w[350]}]\
           [get_ports {ld_w[351]}]\
           [get_ports {ld_w[352]}]\
           [get_ports {ld_w[353]}]\
           [get_ports {ld_w[354]}]\
           [get_ports {ld_w[355]}]\
           [get_ports {ld_w[356]}]\
           [get_ports {ld_w[357]}]\
           [get_ports {ld_w[358]}]\
           [get_ports {ld_w[359]}]\
           [get_ports {ld_w[35]}]\
           [get_ports {ld_w[360]}]\
           [get_ports {ld_w[361]}]\
           [get_ports {ld_w[362]}]\
           [get_ports {ld_w[363]}]\
           [get_ports {ld_w[364]}]\
           [get_ports {ld_w[365]}]\
           [get_ports {ld_w[366]}]\
           [get_ports {ld_w[367]}]\
           [get_ports {ld_w[368]}]\
           [get_ports {ld_w[369]}]\
           [get_ports {ld_w[36]}]\
           [get_ports {ld_w[370]}]\
           [get_ports {ld_w[371]}]\
           [get_ports {ld_w[372]}]\
           [get_ports {ld_w[373]}]\
           [get_ports {ld_w[374]}]\
           [get_ports {ld_w[375]}]\
           [get_ports {ld_w[376]}]\
           [get_ports {ld_w[377]}]\
           [get_ports {ld_w[378]}]\
           [get_ports {ld_w[379]}]\
           [get_ports {ld_w[37]}]\
           [get_ports {ld_w[380]}]\
           [get_ports {ld_w[381]}]\
           [get_ports {ld_w[382]}]\
           [get_ports {ld_w[383]}]\
           [get_ports {ld_w[384]}]\
           [get_ports {ld_w[385]}]\
           [get_ports {ld_w[386]}]\
           [get_ports {ld_w[387]}]\
           [get_ports {ld_w[388]}]\
           [get_ports {ld_w[389]}]\
           [get_ports {ld_w[38]}]\
           [get_ports {ld_w[390]}]\
           [get_ports {ld_w[391]}]\
           [get_ports {ld_w[392]}]\
           [get_ports {ld_w[393]}]\
           [get_ports {ld_w[394]}]\
           [get_ports {ld_w[395]}]\
           [get_ports {ld_w[396]}]\
           [get_ports {ld_w[397]}]\
           [get_ports {ld_w[398]}]\
           [get_ports {ld_w[399]}]\
           [get_ports {ld_w[39]}]\
           [get_ports {ld_w[3]}]\
           [get_ports {ld_w[400]}]\
           [get_ports {ld_w[401]}]\
           [get_ports {ld_w[402]}]\
           [get_ports {ld_w[403]}]\
           [get_ports {ld_w[404]}]\
           [get_ports {ld_w[405]}]\
           [get_ports {ld_w[406]}]\
           [get_ports {ld_w[407]}]\
           [get_ports {ld_w[408]}]\
           [get_ports {ld_w[409]}]\
           [get_ports {ld_w[40]}]\
           [get_ports {ld_w[410]}]\
           [get_ports {ld_w[411]}]\
           [get_ports {ld_w[412]}]\
           [get_ports {ld_w[413]}]\
           [get_ports {ld_w[414]}]\
           [get_ports {ld_w[415]}]\
           [get_ports {ld_w[416]}]\
           [get_ports {ld_w[417]}]\
           [get_ports {ld_w[418]}]\
           [get_ports {ld_w[419]}]\
           [get_ports {ld_w[41]}]\
           [get_ports {ld_w[420]}]\
           [get_ports {ld_w[421]}]\
           [get_ports {ld_w[422]}]\
           [get_ports {ld_w[423]}]\
           [get_ports {ld_w[424]}]\
           [get_ports {ld_w[425]}]\
           [get_ports {ld_w[426]}]\
           [get_ports {ld_w[427]}]\
           [get_ports {ld_w[428]}]\
           [get_ports {ld_w[429]}]\
           [get_ports {ld_w[42]}]\
           [get_ports {ld_w[430]}]\
           [get_ports {ld_w[431]}]\
           [get_ports {ld_w[432]}]\
           [get_ports {ld_w[433]}]\
           [get_ports {ld_w[434]}]\
           [get_ports {ld_w[435]}]\
           [get_ports {ld_w[436]}]\
           [get_ports {ld_w[437]}]\
           [get_ports {ld_w[438]}]\
           [get_ports {ld_w[439]}]\
           [get_ports {ld_w[43]}]\
           [get_ports {ld_w[440]}]\
           [get_ports {ld_w[441]}]\
           [get_ports {ld_w[442]}]\
           [get_ports {ld_w[443]}]\
           [get_ports {ld_w[444]}]\
           [get_ports {ld_w[445]}]\
           [get_ports {ld_w[446]}]\
           [get_ports {ld_w[447]}]\
           [get_ports {ld_w[448]}]\
           [get_ports {ld_w[449]}]\
           [get_ports {ld_w[44]}]\
           [get_ports {ld_w[450]}]\
           [get_ports {ld_w[451]}]\
           [get_ports {ld_w[452]}]\
           [get_ports {ld_w[453]}]\
           [get_ports {ld_w[454]}]\
           [get_ports {ld_w[455]}]\
           [get_ports {ld_w[456]}]\
           [get_ports {ld_w[457]}]\
           [get_ports {ld_w[458]}]\
           [get_ports {ld_w[459]}]\
           [get_ports {ld_w[45]}]\
           [get_ports {ld_w[460]}]\
           [get_ports {ld_w[461]}]\
           [get_ports {ld_w[462]}]\
           [get_ports {ld_w[463]}]\
           [get_ports {ld_w[464]}]\
           [get_ports {ld_w[465]}]\
           [get_ports {ld_w[466]}]\
           [get_ports {ld_w[467]}]\
           [get_ports {ld_w[468]}]\
           [get_ports {ld_w[469]}]\
           [get_ports {ld_w[46]}]\
           [get_ports {ld_w[470]}]\
           [get_ports {ld_w[471]}]\
           [get_ports {ld_w[472]}]\
           [get_ports {ld_w[473]}]\
           [get_ports {ld_w[474]}]\
           [get_ports {ld_w[475]}]\
           [get_ports {ld_w[476]}]\
           [get_ports {ld_w[477]}]\
           [get_ports {ld_w[478]}]\
           [get_ports {ld_w[479]}]\
           [get_ports {ld_w[47]}]\
           [get_ports {ld_w[480]}]\
           [get_ports {ld_w[481]}]\
           [get_ports {ld_w[482]}]\
           [get_ports {ld_w[483]}]\
           [get_ports {ld_w[484]}]\
           [get_ports {ld_w[485]}]\
           [get_ports {ld_w[486]}]\
           [get_ports {ld_w[487]}]\
           [get_ports {ld_w[488]}]\
           [get_ports {ld_w[489]}]\
           [get_ports {ld_w[48]}]\
           [get_ports {ld_w[490]}]\
           [get_ports {ld_w[491]}]\
           [get_ports {ld_w[492]}]\
           [get_ports {ld_w[493]}]\
           [get_ports {ld_w[494]}]\
           [get_ports {ld_w[495]}]\
           [get_ports {ld_w[496]}]\
           [get_ports {ld_w[497]}]\
           [get_ports {ld_w[498]}]\
           [get_ports {ld_w[499]}]\
           [get_ports {ld_w[49]}]\
           [get_ports {ld_w[4]}]\
           [get_ports {ld_w[500]}]\
           [get_ports {ld_w[501]}]\
           [get_ports {ld_w[502]}]\
           [get_ports {ld_w[503]}]\
           [get_ports {ld_w[504]}]\
           [get_ports {ld_w[505]}]\
           [get_ports {ld_w[506]}]\
           [get_ports {ld_w[507]}]\
           [get_ports {ld_w[508]}]\
           [get_ports {ld_w[509]}]\
           [get_ports {ld_w[50]}]\
           [get_ports {ld_w[510]}]\
           [get_ports {ld_w[511]}]\
           [get_ports {ld_w[512]}]\
           [get_ports {ld_w[513]}]\
           [get_ports {ld_w[514]}]\
           [get_ports {ld_w[515]}]\
           [get_ports {ld_w[516]}]\
           [get_ports {ld_w[517]}]\
           [get_ports {ld_w[518]}]\
           [get_ports {ld_w[519]}]\
           [get_ports {ld_w[51]}]\
           [get_ports {ld_w[520]}]\
           [get_ports {ld_w[521]}]\
           [get_ports {ld_w[522]}]\
           [get_ports {ld_w[523]}]\
           [get_ports {ld_w[524]}]\
           [get_ports {ld_w[525]}]\
           [get_ports {ld_w[526]}]\
           [get_ports {ld_w[527]}]\
           [get_ports {ld_w[528]}]\
           [get_ports {ld_w[529]}]\
           [get_ports {ld_w[52]}]\
           [get_ports {ld_w[530]}]\
           [get_ports {ld_w[531]}]\
           [get_ports {ld_w[532]}]\
           [get_ports {ld_w[533]}]\
           [get_ports {ld_w[534]}]\
           [get_ports {ld_w[535]}]\
           [get_ports {ld_w[536]}]\
           [get_ports {ld_w[537]}]\
           [get_ports {ld_w[538]}]\
           [get_ports {ld_w[539]}]\
           [get_ports {ld_w[53]}]\
           [get_ports {ld_w[540]}]\
           [get_ports {ld_w[541]}]\
           [get_ports {ld_w[542]}]\
           [get_ports {ld_w[543]}]\
           [get_ports {ld_w[544]}]\
           [get_ports {ld_w[545]}]\
           [get_ports {ld_w[546]}]\
           [get_ports {ld_w[547]}]\
           [get_ports {ld_w[548]}]\
           [get_ports {ld_w[549]}]\
           [get_ports {ld_w[54]}]\
           [get_ports {ld_w[550]}]\
           [get_ports {ld_w[551]}]\
           [get_ports {ld_w[552]}]\
           [get_ports {ld_w[553]}]\
           [get_ports {ld_w[554]}]\
           [get_ports {ld_w[555]}]\
           [get_ports {ld_w[556]}]\
           [get_ports {ld_w[557]}]\
           [get_ports {ld_w[558]}]\
           [get_ports {ld_w[559]}]\
           [get_ports {ld_w[55]}]\
           [get_ports {ld_w[560]}]\
           [get_ports {ld_w[561]}]\
           [get_ports {ld_w[562]}]\
           [get_ports {ld_w[563]}]\
           [get_ports {ld_w[564]}]\
           [get_ports {ld_w[565]}]\
           [get_ports {ld_w[566]}]\
           [get_ports {ld_w[567]}]\
           [get_ports {ld_w[568]}]\
           [get_ports {ld_w[569]}]\
           [get_ports {ld_w[56]}]\
           [get_ports {ld_w[570]}]\
           [get_ports {ld_w[571]}]\
           [get_ports {ld_w[572]}]\
           [get_ports {ld_w[573]}]\
           [get_ports {ld_w[574]}]\
           [get_ports {ld_w[575]}]\
           [get_ports {ld_w[576]}]\
           [get_ports {ld_w[577]}]\
           [get_ports {ld_w[578]}]\
           [get_ports {ld_w[579]}]\
           [get_ports {ld_w[57]}]\
           [get_ports {ld_w[580]}]\
           [get_ports {ld_w[581]}]\
           [get_ports {ld_w[582]}]\
           [get_ports {ld_w[583]}]\
           [get_ports {ld_w[584]}]\
           [get_ports {ld_w[585]}]\
           [get_ports {ld_w[586]}]\
           [get_ports {ld_w[587]}]\
           [get_ports {ld_w[588]}]\
           [get_ports {ld_w[589]}]\
           [get_ports {ld_w[58]}]\
           [get_ports {ld_w[590]}]\
           [get_ports {ld_w[591]}]\
           [get_ports {ld_w[592]}]\
           [get_ports {ld_w[593]}]\
           [get_ports {ld_w[594]}]\
           [get_ports {ld_w[595]}]\
           [get_ports {ld_w[596]}]\
           [get_ports {ld_w[597]}]\
           [get_ports {ld_w[598]}]\
           [get_ports {ld_w[599]}]\
           [get_ports {ld_w[59]}]\
           [get_ports {ld_w[5]}]\
           [get_ports {ld_w[600]}]\
           [get_ports {ld_w[601]}]\
           [get_ports {ld_w[602]}]\
           [get_ports {ld_w[603]}]\
           [get_ports {ld_w[604]}]\
           [get_ports {ld_w[605]}]\
           [get_ports {ld_w[606]}]\
           [get_ports {ld_w[607]}]\
           [get_ports {ld_w[608]}]\
           [get_ports {ld_w[609]}]\
           [get_ports {ld_w[60]}]\
           [get_ports {ld_w[610]}]\
           [get_ports {ld_w[611]}]\
           [get_ports {ld_w[612]}]\
           [get_ports {ld_w[613]}]\
           [get_ports {ld_w[614]}]\
           [get_ports {ld_w[615]}]\
           [get_ports {ld_w[616]}]\
           [get_ports {ld_w[617]}]\
           [get_ports {ld_w[618]}]\
           [get_ports {ld_w[619]}]\
           [get_ports {ld_w[61]}]\
           [get_ports {ld_w[620]}]\
           [get_ports {ld_w[621]}]\
           [get_ports {ld_w[622]}]\
           [get_ports {ld_w[623]}]\
           [get_ports {ld_w[624]}]\
           [get_ports {ld_w[625]}]\
           [get_ports {ld_w[626]}]\
           [get_ports {ld_w[627]}]\
           [get_ports {ld_w[628]}]\
           [get_ports {ld_w[629]}]\
           [get_ports {ld_w[62]}]\
           [get_ports {ld_w[630]}]\
           [get_ports {ld_w[631]}]\
           [get_ports {ld_w[632]}]\
           [get_ports {ld_w[633]}]\
           [get_ports {ld_w[634]}]\
           [get_ports {ld_w[635]}]\
           [get_ports {ld_w[636]}]\
           [get_ports {ld_w[637]}]\
           [get_ports {ld_w[638]}]\
           [get_ports {ld_w[639]}]\
           [get_ports {ld_w[63]}]\
           [get_ports {ld_w[640]}]\
           [get_ports {ld_w[641]}]\
           [get_ports {ld_w[642]}]\
           [get_ports {ld_w[643]}]\
           [get_ports {ld_w[644]}]\
           [get_ports {ld_w[645]}]\
           [get_ports {ld_w[646]}]\
           [get_ports {ld_w[647]}]\
           [get_ports {ld_w[648]}]\
           [get_ports {ld_w[649]}]\
           [get_ports {ld_w[64]}]\
           [get_ports {ld_w[650]}]\
           [get_ports {ld_w[651]}]\
           [get_ports {ld_w[652]}]\
           [get_ports {ld_w[653]}]\
           [get_ports {ld_w[654]}]\
           [get_ports {ld_w[655]}]\
           [get_ports {ld_w[656]}]\
           [get_ports {ld_w[657]}]\
           [get_ports {ld_w[658]}]\
           [get_ports {ld_w[659]}]\
           [get_ports {ld_w[65]}]\
           [get_ports {ld_w[660]}]\
           [get_ports {ld_w[661]}]\
           [get_ports {ld_w[662]}]\
           [get_ports {ld_w[663]}]\
           [get_ports {ld_w[664]}]\
           [get_ports {ld_w[665]}]\
           [get_ports {ld_w[666]}]\
           [get_ports {ld_w[667]}]\
           [get_ports {ld_w[668]}]\
           [get_ports {ld_w[669]}]\
           [get_ports {ld_w[66]}]\
           [get_ports {ld_w[670]}]\
           [get_ports {ld_w[671]}]\
           [get_ports {ld_w[672]}]\
           [get_ports {ld_w[673]}]\
           [get_ports {ld_w[674]}]\
           [get_ports {ld_w[675]}]\
           [get_ports {ld_w[676]}]\
           [get_ports {ld_w[677]}]\
           [get_ports {ld_w[678]}]\
           [get_ports {ld_w[679]}]\
           [get_ports {ld_w[67]}]\
           [get_ports {ld_w[680]}]\
           [get_ports {ld_w[681]}]\
           [get_ports {ld_w[682]}]\
           [get_ports {ld_w[683]}]\
           [get_ports {ld_w[684]}]\
           [get_ports {ld_w[685]}]\
           [get_ports {ld_w[686]}]\
           [get_ports {ld_w[687]}]\
           [get_ports {ld_w[688]}]\
           [get_ports {ld_w[689]}]\
           [get_ports {ld_w[68]}]\
           [get_ports {ld_w[690]}]\
           [get_ports {ld_w[691]}]\
           [get_ports {ld_w[692]}]\
           [get_ports {ld_w[693]}]\
           [get_ports {ld_w[694]}]\
           [get_ports {ld_w[695]}]\
           [get_ports {ld_w[696]}]\
           [get_ports {ld_w[697]}]\
           [get_ports {ld_w[698]}]\
           [get_ports {ld_w[699]}]\
           [get_ports {ld_w[69]}]\
           [get_ports {ld_w[6]}]\
           [get_ports {ld_w[700]}]\
           [get_ports {ld_w[701]}]\
           [get_ports {ld_w[702]}]\
           [get_ports {ld_w[703]}]\
           [get_ports {ld_w[704]}]\
           [get_ports {ld_w[705]}]\
           [get_ports {ld_w[706]}]\
           [get_ports {ld_w[707]}]\
           [get_ports {ld_w[708]}]\
           [get_ports {ld_w[709]}]\
           [get_ports {ld_w[70]}]\
           [get_ports {ld_w[710]}]\
           [get_ports {ld_w[711]}]\
           [get_ports {ld_w[712]}]\
           [get_ports {ld_w[713]}]\
           [get_ports {ld_w[714]}]\
           [get_ports {ld_w[715]}]\
           [get_ports {ld_w[716]}]\
           [get_ports {ld_w[717]}]\
           [get_ports {ld_w[718]}]\
           [get_ports {ld_w[719]}]\
           [get_ports {ld_w[71]}]\
           [get_ports {ld_w[720]}]\
           [get_ports {ld_w[721]}]\
           [get_ports {ld_w[722]}]\
           [get_ports {ld_w[723]}]\
           [get_ports {ld_w[724]}]\
           [get_ports {ld_w[725]}]\
           [get_ports {ld_w[726]}]\
           [get_ports {ld_w[727]}]\
           [get_ports {ld_w[728]}]\
           [get_ports {ld_w[729]}]\
           [get_ports {ld_w[72]}]\
           [get_ports {ld_w[730]}]\
           [get_ports {ld_w[731]}]\
           [get_ports {ld_w[732]}]\
           [get_ports {ld_w[733]}]\
           [get_ports {ld_w[734]}]\
           [get_ports {ld_w[735]}]\
           [get_ports {ld_w[736]}]\
           [get_ports {ld_w[737]}]\
           [get_ports {ld_w[738]}]\
           [get_ports {ld_w[739]}]\
           [get_ports {ld_w[73]}]\
           [get_ports {ld_w[740]}]\
           [get_ports {ld_w[741]}]\
           [get_ports {ld_w[742]}]\
           [get_ports {ld_w[743]}]\
           [get_ports {ld_w[744]}]\
           [get_ports {ld_w[745]}]\
           [get_ports {ld_w[746]}]\
           [get_ports {ld_w[747]}]\
           [get_ports {ld_w[748]}]\
           [get_ports {ld_w[749]}]\
           [get_ports {ld_w[74]}]\
           [get_ports {ld_w[750]}]\
           [get_ports {ld_w[751]}]\
           [get_ports {ld_w[752]}]\
           [get_ports {ld_w[753]}]\
           [get_ports {ld_w[754]}]\
           [get_ports {ld_w[755]}]\
           [get_ports {ld_w[756]}]\
           [get_ports {ld_w[757]}]\
           [get_ports {ld_w[758]}]\
           [get_ports {ld_w[759]}]\
           [get_ports {ld_w[75]}]\
           [get_ports {ld_w[760]}]\
           [get_ports {ld_w[761]}]\
           [get_ports {ld_w[762]}]\
           [get_ports {ld_w[763]}]\
           [get_ports {ld_w[764]}]\
           [get_ports {ld_w[765]}]\
           [get_ports {ld_w[766]}]\
           [get_ports {ld_w[767]}]\
           [get_ports {ld_w[768]}]\
           [get_ports {ld_w[769]}]\
           [get_ports {ld_w[76]}]\
           [get_ports {ld_w[770]}]\
           [get_ports {ld_w[771]}]\
           [get_ports {ld_w[772]}]\
           [get_ports {ld_w[773]}]\
           [get_ports {ld_w[774]}]\
           [get_ports {ld_w[775]}]\
           [get_ports {ld_w[776]}]\
           [get_ports {ld_w[777]}]\
           [get_ports {ld_w[778]}]\
           [get_ports {ld_w[779]}]\
           [get_ports {ld_w[77]}]\
           [get_ports {ld_w[780]}]\
           [get_ports {ld_w[781]}]\
           [get_ports {ld_w[782]}]\
           [get_ports {ld_w[783]}]\
           [get_ports {ld_w[784]}]\
           [get_ports {ld_w[785]}]\
           [get_ports {ld_w[786]}]\
           [get_ports {ld_w[787]}]\
           [get_ports {ld_w[788]}]\
           [get_ports {ld_w[789]}]\
           [get_ports {ld_w[78]}]\
           [get_ports {ld_w[790]}]\
           [get_ports {ld_w[791]}]\
           [get_ports {ld_w[792]}]\
           [get_ports {ld_w[793]}]\
           [get_ports {ld_w[794]}]\
           [get_ports {ld_w[795]}]\
           [get_ports {ld_w[796]}]\
           [get_ports {ld_w[797]}]\
           [get_ports {ld_w[798]}]\
           [get_ports {ld_w[799]}]\
           [get_ports {ld_w[79]}]\
           [get_ports {ld_w[7]}]\
           [get_ports {ld_w[800]}]\
           [get_ports {ld_w[801]}]\
           [get_ports {ld_w[802]}]\
           [get_ports {ld_w[803]}]\
           [get_ports {ld_w[804]}]\
           [get_ports {ld_w[805]}]\
           [get_ports {ld_w[806]}]\
           [get_ports {ld_w[807]}]\
           [get_ports {ld_w[808]}]\
           [get_ports {ld_w[809]}]\
           [get_ports {ld_w[80]}]\
           [get_ports {ld_w[810]}]\
           [get_ports {ld_w[811]}]\
           [get_ports {ld_w[812]}]\
           [get_ports {ld_w[813]}]\
           [get_ports {ld_w[814]}]\
           [get_ports {ld_w[815]}]\
           [get_ports {ld_w[816]}]\
           [get_ports {ld_w[817]}]\
           [get_ports {ld_w[818]}]\
           [get_ports {ld_w[819]}]\
           [get_ports {ld_w[81]}]\
           [get_ports {ld_w[820]}]\
           [get_ports {ld_w[821]}]\
           [get_ports {ld_w[822]}]\
           [get_ports {ld_w[823]}]\
           [get_ports {ld_w[824]}]\
           [get_ports {ld_w[825]}]\
           [get_ports {ld_w[826]}]\
           [get_ports {ld_w[827]}]\
           [get_ports {ld_w[828]}]\
           [get_ports {ld_w[829]}]\
           [get_ports {ld_w[82]}]\
           [get_ports {ld_w[830]}]\
           [get_ports {ld_w[831]}]\
           [get_ports {ld_w[832]}]\
           [get_ports {ld_w[833]}]\
           [get_ports {ld_w[834]}]\
           [get_ports {ld_w[835]}]\
           [get_ports {ld_w[836]}]\
           [get_ports {ld_w[837]}]\
           [get_ports {ld_w[838]}]\
           [get_ports {ld_w[839]}]\
           [get_ports {ld_w[83]}]\
           [get_ports {ld_w[840]}]\
           [get_ports {ld_w[841]}]\
           [get_ports {ld_w[842]}]\
           [get_ports {ld_w[843]}]\
           [get_ports {ld_w[844]}]\
           [get_ports {ld_w[845]}]\
           [get_ports {ld_w[846]}]\
           [get_ports {ld_w[847]}]\
           [get_ports {ld_w[848]}]\
           [get_ports {ld_w[849]}]\
           [get_ports {ld_w[84]}]\
           [get_ports {ld_w[850]}]\
           [get_ports {ld_w[851]}]\
           [get_ports {ld_w[852]}]\
           [get_ports {ld_w[853]}]\
           [get_ports {ld_w[854]}]\
           [get_ports {ld_w[855]}]\
           [get_ports {ld_w[856]}]\
           [get_ports {ld_w[857]}]\
           [get_ports {ld_w[858]}]\
           [get_ports {ld_w[859]}]\
           [get_ports {ld_w[85]}]\
           [get_ports {ld_w[860]}]\
           [get_ports {ld_w[861]}]\
           [get_ports {ld_w[862]}]\
           [get_ports {ld_w[863]}]\
           [get_ports {ld_w[864]}]\
           [get_ports {ld_w[865]}]\
           [get_ports {ld_w[866]}]\
           [get_ports {ld_w[867]}]\
           [get_ports {ld_w[868]}]\
           [get_ports {ld_w[869]}]\
           [get_ports {ld_w[86]}]\
           [get_ports {ld_w[870]}]\
           [get_ports {ld_w[871]}]\
           [get_ports {ld_w[872]}]\
           [get_ports {ld_w[873]}]\
           [get_ports {ld_w[874]}]\
           [get_ports {ld_w[875]}]\
           [get_ports {ld_w[876]}]\
           [get_ports {ld_w[877]}]\
           [get_ports {ld_w[878]}]\
           [get_ports {ld_w[879]}]\
           [get_ports {ld_w[87]}]\
           [get_ports {ld_w[880]}]\
           [get_ports {ld_w[881]}]\
           [get_ports {ld_w[882]}]\
           [get_ports {ld_w[883]}]\
           [get_ports {ld_w[884]}]\
           [get_ports {ld_w[885]}]\
           [get_ports {ld_w[886]}]\
           [get_ports {ld_w[887]}]\
           [get_ports {ld_w[888]}]\
           [get_ports {ld_w[889]}]\
           [get_ports {ld_w[88]}]\
           [get_ports {ld_w[890]}]\
           [get_ports {ld_w[891]}]\
           [get_ports {ld_w[892]}]\
           [get_ports {ld_w[893]}]\
           [get_ports {ld_w[894]}]\
           [get_ports {ld_w[895]}]\
           [get_ports {ld_w[896]}]\
           [get_ports {ld_w[897]}]\
           [get_ports {ld_w[898]}]\
           [get_ports {ld_w[899]}]\
           [get_ports {ld_w[89]}]\
           [get_ports {ld_w[8]}]\
           [get_ports {ld_w[900]}]\
           [get_ports {ld_w[901]}]\
           [get_ports {ld_w[902]}]\
           [get_ports {ld_w[903]}]\
           [get_ports {ld_w[904]}]\
           [get_ports {ld_w[905]}]\
           [get_ports {ld_w[906]}]\
           [get_ports {ld_w[907]}]\
           [get_ports {ld_w[908]}]\
           [get_ports {ld_w[909]}]\
           [get_ports {ld_w[90]}]\
           [get_ports {ld_w[910]}]\
           [get_ports {ld_w[911]}]\
           [get_ports {ld_w[912]}]\
           [get_ports {ld_w[913]}]\
           [get_ports {ld_w[914]}]\
           [get_ports {ld_w[915]}]\
           [get_ports {ld_w[916]}]\
           [get_ports {ld_w[917]}]\
           [get_ports {ld_w[918]}]\
           [get_ports {ld_w[919]}]\
           [get_ports {ld_w[91]}]\
           [get_ports {ld_w[920]}]\
           [get_ports {ld_w[921]}]\
           [get_ports {ld_w[922]}]\
           [get_ports {ld_w[923]}]\
           [get_ports {ld_w[924]}]\
           [get_ports {ld_w[925]}]\
           [get_ports {ld_w[926]}]\
           [get_ports {ld_w[927]}]\
           [get_ports {ld_w[928]}]\
           [get_ports {ld_w[929]}]\
           [get_ports {ld_w[92]}]\
           [get_ports {ld_w[930]}]\
           [get_ports {ld_w[931]}]\
           [get_ports {ld_w[932]}]\
           [get_ports {ld_w[933]}]\
           [get_ports {ld_w[934]}]\
           [get_ports {ld_w[935]}]\
           [get_ports {ld_w[936]}]\
           [get_ports {ld_w[937]}]\
           [get_ports {ld_w[938]}]\
           [get_ports {ld_w[939]}]\
           [get_ports {ld_w[93]}]\
           [get_ports {ld_w[940]}]\
           [get_ports {ld_w[941]}]\
           [get_ports {ld_w[942]}]\
           [get_ports {ld_w[943]}]\
           [get_ports {ld_w[944]}]\
           [get_ports {ld_w[945]}]\
           [get_ports {ld_w[946]}]\
           [get_ports {ld_w[947]}]\
           [get_ports {ld_w[948]}]\
           [get_ports {ld_w[949]}]\
           [get_ports {ld_w[94]}]\
           [get_ports {ld_w[950]}]\
           [get_ports {ld_w[951]}]\
           [get_ports {ld_w[952]}]\
           [get_ports {ld_w[953]}]\
           [get_ports {ld_w[954]}]\
           [get_ports {ld_w[955]}]\
           [get_ports {ld_w[956]}]\
           [get_ports {ld_w[957]}]\
           [get_ports {ld_w[958]}]\
           [get_ports {ld_w[959]}]\
           [get_ports {ld_w[95]}]\
           [get_ports {ld_w[960]}]\
           [get_ports {ld_w[961]}]\
           [get_ports {ld_w[962]}]\
           [get_ports {ld_w[963]}]\
           [get_ports {ld_w[964]}]\
           [get_ports {ld_w[965]}]\
           [get_ports {ld_w[966]}]\
           [get_ports {ld_w[967]}]\
           [get_ports {ld_w[968]}]\
           [get_ports {ld_w[969]}]\
           [get_ports {ld_w[96]}]\
           [get_ports {ld_w[970]}]\
           [get_ports {ld_w[971]}]\
           [get_ports {ld_w[972]}]\
           [get_ports {ld_w[973]}]\
           [get_ports {ld_w[974]}]\
           [get_ports {ld_w[975]}]\
           [get_ports {ld_w[976]}]\
           [get_ports {ld_w[977]}]\
           [get_ports {ld_w[978]}]\
           [get_ports {ld_w[979]}]\
           [get_ports {ld_w[97]}]\
           [get_ports {ld_w[980]}]\
           [get_ports {ld_w[981]}]\
           [get_ports {ld_w[982]}]\
           [get_ports {ld_w[983]}]\
           [get_ports {ld_w[984]}]\
           [get_ports {ld_w[985]}]\
           [get_ports {ld_w[986]}]\
           [get_ports {ld_w[987]}]\
           [get_ports {ld_w[988]}]\
           [get_ports {ld_w[989]}]\
           [get_ports {ld_w[98]}]\
           [get_ports {ld_w[990]}]\
           [get_ports {ld_w[991]}]\
           [get_ports {ld_w[992]}]\
           [get_ports {ld_w[993]}]\
           [get_ports {ld_w[994]}]\
           [get_ports {ld_w[995]}]\
           [get_ports {ld_w[996]}]\
           [get_ports {ld_w[997]}]\
           [get_ports {ld_w[998]}]\
           [get_ports {ld_w[999]}]\
           [get_ports {ld_w[99]}]\
           [get_ports {ld_w[9]}]\
           [get_ports {rst_n}]]
set_false_path\
    -to [list [get_ports {oflt[0]}]\
           [get_ports {oflt[1]}]\
           [get_ports {oflt[2]}]\
           [get_ports {oflt[3]}]\
           [get_ports {ov}]\
           [get_ports {oy[0]}]\
           [get_ports {oy[100]}]\
           [get_ports {oy[101]}]\
           [get_ports {oy[102]}]\
           [get_ports {oy[103]}]\
           [get_ports {oy[104]}]\
           [get_ports {oy[105]}]\
           [get_ports {oy[106]}]\
           [get_ports {oy[107]}]\
           [get_ports {oy[108]}]\
           [get_ports {oy[109]}]\
           [get_ports {oy[10]}]\
           [get_ports {oy[110]}]\
           [get_ports {oy[111]}]\
           [get_ports {oy[112]}]\
           [get_ports {oy[113]}]\
           [get_ports {oy[114]}]\
           [get_ports {oy[115]}]\
           [get_ports {oy[116]}]\
           [get_ports {oy[117]}]\
           [get_ports {oy[118]}]\
           [get_ports {oy[119]}]\
           [get_ports {oy[11]}]\
           [get_ports {oy[120]}]\
           [get_ports {oy[121]}]\
           [get_ports {oy[122]}]\
           [get_ports {oy[123]}]\
           [get_ports {oy[124]}]\
           [get_ports {oy[125]}]\
           [get_ports {oy[126]}]\
           [get_ports {oy[127]}]\
           [get_ports {oy[12]}]\
           [get_ports {oy[13]}]\
           [get_ports {oy[14]}]\
           [get_ports {oy[15]}]\
           [get_ports {oy[16]}]\
           [get_ports {oy[17]}]\
           [get_ports {oy[18]}]\
           [get_ports {oy[19]}]\
           [get_ports {oy[1]}]\
           [get_ports {oy[20]}]\
           [get_ports {oy[21]}]\
           [get_ports {oy[22]}]\
           [get_ports {oy[23]}]\
           [get_ports {oy[24]}]\
           [get_ports {oy[25]}]\
           [get_ports {oy[26]}]\
           [get_ports {oy[27]}]\
           [get_ports {oy[28]}]\
           [get_ports {oy[29]}]\
           [get_ports {oy[2]}]\
           [get_ports {oy[30]}]\
           [get_ports {oy[31]}]\
           [get_ports {oy[32]}]\
           [get_ports {oy[33]}]\
           [get_ports {oy[34]}]\
           [get_ports {oy[35]}]\
           [get_ports {oy[36]}]\
           [get_ports {oy[37]}]\
           [get_ports {oy[38]}]\
           [get_ports {oy[39]}]\
           [get_ports {oy[3]}]\
           [get_ports {oy[40]}]\
           [get_ports {oy[41]}]\
           [get_ports {oy[42]}]\
           [get_ports {oy[43]}]\
           [get_ports {oy[44]}]\
           [get_ports {oy[45]}]\
           [get_ports {oy[46]}]\
           [get_ports {oy[47]}]\
           [get_ports {oy[48]}]\
           [get_ports {oy[49]}]\
           [get_ports {oy[4]}]\
           [get_ports {oy[50]}]\
           [get_ports {oy[51]}]\
           [get_ports {oy[52]}]\
           [get_ports {oy[53]}]\
           [get_ports {oy[54]}]\
           [get_ports {oy[55]}]\
           [get_ports {oy[56]}]\
           [get_ports {oy[57]}]\
           [get_ports {oy[58]}]\
           [get_ports {oy[59]}]\
           [get_ports {oy[5]}]\
           [get_ports {oy[60]}]\
           [get_ports {oy[61]}]\
           [get_ports {oy[62]}]\
           [get_ports {oy[63]}]\
           [get_ports {oy[64]}]\
           [get_ports {oy[65]}]\
           [get_ports {oy[66]}]\
           [get_ports {oy[67]}]\
           [get_ports {oy[68]}]\
           [get_ports {oy[69]}]\
           [get_ports {oy[6]}]\
           [get_ports {oy[70]}]\
           [get_ports {oy[71]}]\
           [get_ports {oy[72]}]\
           [get_ports {oy[73]}]\
           [get_ports {oy[74]}]\
           [get_ports {oy[75]}]\
           [get_ports {oy[76]}]\
           [get_ports {oy[77]}]\
           [get_ports {oy[78]}]\
           [get_ports {oy[79]}]\
           [get_ports {oy[7]}]\
           [get_ports {oy[80]}]\
           [get_ports {oy[81]}]\
           [get_ports {oy[82]}]\
           [get_ports {oy[83]}]\
           [get_ports {oy[84]}]\
           [get_ports {oy[85]}]\
           [get_ports {oy[86]}]\
           [get_ports {oy[87]}]\
           [get_ports {oy[88]}]\
           [get_ports {oy[89]}]\
           [get_ports {oy[8]}]\
           [get_ports {oy[90]}]\
           [get_ports {oy[91]}]\
           [get_ports {oy[92]}]\
           [get_ports {oy[93]}]\
           [get_ports {oy[94]}]\
           [get_ports {oy[95]}]\
           [get_ports {oy[96]}]\
           [get_ports {oy[97]}]\
           [get_ports {oy[98]}]\
           [get_ports {oy[99]}]\
           [get_ports {oy[9]}]]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 3.8980 [get_ports {ov}]
set_load -pin_load 3.8980 [get_ports {oflt[3]}]
set_load -pin_load 3.8980 [get_ports {oflt[2]}]
set_load -pin_load 3.8980 [get_ports {oflt[1]}]
set_load -pin_load 3.8980 [get_ports {oflt[0]}]
set_load -pin_load 3.8980 [get_ports {oy[127]}]
set_load -pin_load 3.8980 [get_ports {oy[126]}]
set_load -pin_load 3.8980 [get_ports {oy[125]}]
set_load -pin_load 3.8980 [get_ports {oy[124]}]
set_load -pin_load 3.8980 [get_ports {oy[123]}]
set_load -pin_load 3.8980 [get_ports {oy[122]}]
set_load -pin_load 3.8980 [get_ports {oy[121]}]
set_load -pin_load 3.8980 [get_ports {oy[120]}]
set_load -pin_load 3.8980 [get_ports {oy[119]}]
set_load -pin_load 3.8980 [get_ports {oy[118]}]
set_load -pin_load 3.8980 [get_ports {oy[117]}]
set_load -pin_load 3.8980 [get_ports {oy[116]}]
set_load -pin_load 3.8980 [get_ports {oy[115]}]
set_load -pin_load 3.8980 [get_ports {oy[114]}]
set_load -pin_load 3.8980 [get_ports {oy[113]}]
set_load -pin_load 3.8980 [get_ports {oy[112]}]
set_load -pin_load 3.8980 [get_ports {oy[111]}]
set_load -pin_load 3.8980 [get_ports {oy[110]}]
set_load -pin_load 3.8980 [get_ports {oy[109]}]
set_load -pin_load 3.8980 [get_ports {oy[108]}]
set_load -pin_load 3.8980 [get_ports {oy[107]}]
set_load -pin_load 3.8980 [get_ports {oy[106]}]
set_load -pin_load 3.8980 [get_ports {oy[105]}]
set_load -pin_load 3.8980 [get_ports {oy[104]}]
set_load -pin_load 3.8980 [get_ports {oy[103]}]
set_load -pin_load 3.8980 [get_ports {oy[102]}]
set_load -pin_load 3.8980 [get_ports {oy[101]}]
set_load -pin_load 3.8980 [get_ports {oy[100]}]
set_load -pin_load 3.8980 [get_ports {oy[99]}]
set_load -pin_load 3.8980 [get_ports {oy[98]}]
set_load -pin_load 3.8980 [get_ports {oy[97]}]
set_load -pin_load 3.8980 [get_ports {oy[96]}]
set_load -pin_load 3.8980 [get_ports {oy[95]}]
set_load -pin_load 3.8980 [get_ports {oy[94]}]
set_load -pin_load 3.8980 [get_ports {oy[93]}]
set_load -pin_load 3.8980 [get_ports {oy[92]}]
set_load -pin_load 3.8980 [get_ports {oy[91]}]
set_load -pin_load 3.8980 [get_ports {oy[90]}]
set_load -pin_load 3.8980 [get_ports {oy[89]}]
set_load -pin_load 3.8980 [get_ports {oy[88]}]
set_load -pin_load 3.8980 [get_ports {oy[87]}]
set_load -pin_load 3.8980 [get_ports {oy[86]}]
set_load -pin_load 3.8980 [get_ports {oy[85]}]
set_load -pin_load 3.8980 [get_ports {oy[84]}]
set_load -pin_load 3.8980 [get_ports {oy[83]}]
set_load -pin_load 3.8980 [get_ports {oy[82]}]
set_load -pin_load 3.8980 [get_ports {oy[81]}]
set_load -pin_load 3.8980 [get_ports {oy[80]}]
set_load -pin_load 3.8980 [get_ports {oy[79]}]
set_load -pin_load 3.8980 [get_ports {oy[78]}]
set_load -pin_load 3.8980 [get_ports {oy[77]}]
set_load -pin_load 3.8980 [get_ports {oy[76]}]
set_load -pin_load 3.8980 [get_ports {oy[75]}]
set_load -pin_load 3.8980 [get_ports {oy[74]}]
set_load -pin_load 3.8980 [get_ports {oy[73]}]
set_load -pin_load 3.8980 [get_ports {oy[72]}]
set_load -pin_load 3.8980 [get_ports {oy[71]}]
set_load -pin_load 3.8980 [get_ports {oy[70]}]
set_load -pin_load 3.8980 [get_ports {oy[69]}]
set_load -pin_load 3.8980 [get_ports {oy[68]}]
set_load -pin_load 3.8980 [get_ports {oy[67]}]
set_load -pin_load 3.8980 [get_ports {oy[66]}]
set_load -pin_load 3.8980 [get_ports {oy[65]}]
set_load -pin_load 3.8980 [get_ports {oy[64]}]
set_load -pin_load 3.8980 [get_ports {oy[63]}]
set_load -pin_load 3.8980 [get_ports {oy[62]}]
set_load -pin_load 3.8980 [get_ports {oy[61]}]
set_load -pin_load 3.8980 [get_ports {oy[60]}]
set_load -pin_load 3.8980 [get_ports {oy[59]}]
set_load -pin_load 3.8980 [get_ports {oy[58]}]
set_load -pin_load 3.8980 [get_ports {oy[57]}]
set_load -pin_load 3.8980 [get_ports {oy[56]}]
set_load -pin_load 3.8980 [get_ports {oy[55]}]
set_load -pin_load 3.8980 [get_ports {oy[54]}]
set_load -pin_load 3.8980 [get_ports {oy[53]}]
set_load -pin_load 3.8980 [get_ports {oy[52]}]
set_load -pin_load 3.8980 [get_ports {oy[51]}]
set_load -pin_load 3.8980 [get_ports {oy[50]}]
set_load -pin_load 3.8980 [get_ports {oy[49]}]
set_load -pin_load 3.8980 [get_ports {oy[48]}]
set_load -pin_load 3.8980 [get_ports {oy[47]}]
set_load -pin_load 3.8980 [get_ports {oy[46]}]
set_load -pin_load 3.8980 [get_ports {oy[45]}]
set_load -pin_load 3.8980 [get_ports {oy[44]}]
set_load -pin_load 3.8980 [get_ports {oy[43]}]
set_load -pin_load 3.8980 [get_ports {oy[42]}]
set_load -pin_load 3.8980 [get_ports {oy[41]}]
set_load -pin_load 3.8980 [get_ports {oy[40]}]
set_load -pin_load 3.8980 [get_ports {oy[39]}]
set_load -pin_load 3.8980 [get_ports {oy[38]}]
set_load -pin_load 3.8980 [get_ports {oy[37]}]
set_load -pin_load 3.8980 [get_ports {oy[36]}]
set_load -pin_load 3.8980 [get_ports {oy[35]}]
set_load -pin_load 3.8980 [get_ports {oy[34]}]
set_load -pin_load 3.8980 [get_ports {oy[33]}]
set_load -pin_load 3.8980 [get_ports {oy[32]}]
set_load -pin_load 3.8980 [get_ports {oy[31]}]
set_load -pin_load 3.8980 [get_ports {oy[30]}]
set_load -pin_load 3.8980 [get_ports {oy[29]}]
set_load -pin_load 3.8980 [get_ports {oy[28]}]
set_load -pin_load 3.8980 [get_ports {oy[27]}]
set_load -pin_load 3.8980 [get_ports {oy[26]}]
set_load -pin_load 3.8980 [get_ports {oy[25]}]
set_load -pin_load 3.8980 [get_ports {oy[24]}]
set_load -pin_load 3.8980 [get_ports {oy[23]}]
set_load -pin_load 3.8980 [get_ports {oy[22]}]
set_load -pin_load 3.8980 [get_ports {oy[21]}]
set_load -pin_load 3.8980 [get_ports {oy[20]}]
set_load -pin_load 3.8980 [get_ports {oy[19]}]
set_load -pin_load 3.8980 [get_ports {oy[18]}]
set_load -pin_load 3.8980 [get_ports {oy[17]}]
set_load -pin_load 3.8980 [get_ports {oy[16]}]
set_load -pin_load 3.8980 [get_ports {oy[15]}]
set_load -pin_load 3.8980 [get_ports {oy[14]}]
set_load -pin_load 3.8980 [get_ports {oy[13]}]
set_load -pin_load 3.8980 [get_ports {oy[12]}]
set_load -pin_load 3.8980 [get_ports {oy[11]}]
set_load -pin_load 3.8980 [get_ports {oy[10]}]
set_load -pin_load 3.8980 [get_ports {oy[9]}]
set_load -pin_load 3.8980 [get_ports {oy[8]}]
set_load -pin_load 3.8980 [get_ports {oy[7]}]
set_load -pin_load 3.8980 [get_ports {oy[6]}]
set_load -pin_load 3.8980 [get_ports {oy[5]}]
set_load -pin_load 3.8980 [get_ports {oy[4]}]
set_load -pin_load 3.8980 [get_ports {oy[3]}]
set_load -pin_load 3.8980 [get_ports {oy[2]}]
set_load -pin_load 3.8980 [get_ports {oy[1]}]
set_load -pin_load 3.8980 [get_ports {oy[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_fanout 32.0000 [current_design]
