create_clock -name coupon_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks coupon_clk]
set_clock_uncertainty -hold 25 [get_clocks coupon_clk]
set_input_delay -max 30 -clock coupon_clk [get_ports {lane_v* payload*}]
set_input_delay -min 30 -clock coupon_clk [get_ports {lane_v* payload*}]
set_output_delay -max 0 -clock coupon_clk [get_ports {compacted* pair_select* quad_select*}]
set_output_delay -min -30 -clock coupon_clk [get_ports {compacted* pair_select* quad_select*}]
set_load 80 [get_ports {compacted* pair_select* quad_select*}]
# Explicit native source-cell timing model; actual parent driver/wire qualification OPEN.
set_driving_cell -lib_cell BUFx8_ASAP7_75t_R -pin Y [get_ports {lane_v* payload*}]
# Ideal-wire source coupon only. Actual wire RC/CQ/clock insertion/neighbor OPEN.
