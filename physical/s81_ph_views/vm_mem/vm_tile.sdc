# CLAUDE S81-PH vm v2 bank-group tile (dsfd_vm_bg): appended after the calibrated margin IO SDC (core_clk = ck, the
# serial 0.9 GHz clock).  rs = asynchronous reset (synchronised in the tile); grp = static tile index (tie cells, registered).
set_false_path -from [get_ports {rs* grp*}]
# every data port is an abutted chain hop inside one clock region (budget sheet dsfd_vm_bg: skew class intra, 75 ps,
# L 0.2 um): the die clock-arrival term is 75 ps, not the 150 ps inter-region term (OWNER clarification 10-06 ~10:40)
set ot_vi [get_ports -quiet {i_v* i_we* i_row* i_mask* i_d* r_v* r_d* r_f* r_o*}]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 75}] -clock vclk $ot_vi
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 75}] -clock vclk [all_outputs]
