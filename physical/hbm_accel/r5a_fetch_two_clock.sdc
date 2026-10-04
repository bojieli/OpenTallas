# HA4 R5a element (ot_hbm_accel_expert_fetch_stream_sram): second clock and its ports, appended to the
# driver's SDC (core_clk = clk, 0.833 ns, the 1.2 GHz SM/streaming domain).  hclk is the HBM
# controller CK/2 (976.6 MHz).  The two domains meet only in ot_hbm_accel_cdc_fifo (Gray pointers,
# two-flop synchronisers), so they are asynchronous groups.  Units: ps (ASAP7 liberty).
create_clock -name h_clk -period 1024 [get_ports hclk]
set_clock_uncertainty -setup 60 [get_clocks h_clk]
set_clock_uncertainty -hold 25 [get_clocks h_clk]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks h_clk]
set h_inputs [get_ports {notice rd_v[*] rd_data[*]}]
set_input_delay [expr 1024 * 0.2] -clock h_clk $h_inputs
set h_outputs [get_ports {row_v[*] row_op[*] row_bank[*] row_row[*] col_v[*] col_bank[*] col_col[*]}]
set_output_delay [expr 1024 * 0.2] -clock h_clk $h_outputs
set_false_path -from [get_ports hrst_n]
