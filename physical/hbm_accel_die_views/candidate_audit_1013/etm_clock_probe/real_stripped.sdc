###############################################################################
# Created by write_sdc
# Wed Oct 14 02:43:52 2026
###############################################################################
current_design realmini
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk_stream -period 0.8333 \
    [list [get_pins {a/ck}]\
          [get_pins {d/ck}]]
set_clock_uncertainty -setup 0.1500 clk_stream
set_clock_uncertainty -hold 0.0250 clk_stream
set_propagated_clock [get_clocks {clk_stream}]
create_clock -name clk_stream__early_tap -period 0.8333 [get_pins {b/ck}]
set_clock_uncertainty -setup 0.1500 clk_stream__early_tap
set_clock_uncertainty -hold 0.0250 clk_stream__early_tap
set_propagated_clock [get_clocks {clk_stream__early_tap}]
create_clock -name clk_serial -period 1.1111 [get_pins {c/ck}]
set_clock_uncertainty -setup 0.1500 clk_serial
set_clock_uncertainty -hold 0.0250 clk_serial
set_propagated_clock [get_clocks {clk_serial}]
set_clock_latency -source 0.1500  -clock [get_clocks {clk_stream}] [get_pins {a/ck}]
set_clock_latency -source 0.1500  -clock [get_clocks {clk_stream}] [get_pins {d/ck}]
set_clock_latency -source 0.1500  -clock [get_clocks {clk_stream__early_tap}] [get_pins {b/ck}]
set_clock_latency -source 0.1500  -clock [get_clocks {clk_serial}] [get_pins {c/ck}]
set_clock_uncertainty -rise_from [get_clocks {clk_stream}] -rise_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -rise_from [get_clocks {clk_stream}] -fall_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream}] -rise_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream}] -fall_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -rise_from [get_clocks {clk_stream__early_tap}] -rise_to [get_clocks {clk_stream}]  -setup 0.2100
set_clock_uncertainty -rise_from [get_clocks {clk_stream__early_tap}] -fall_to [get_clocks {clk_stream}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream__early_tap}] -rise_to [get_clocks {clk_stream}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream__early_tap}] -fall_to [get_clocks {clk_stream}]  -setup 0.2100
set_clock_uncertainty -rise_from [get_clocks {clk_stream__early_tap}] -rise_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -rise_from [get_clocks {clk_stream__early_tap}] -fall_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream__early_tap}] -rise_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_clock_uncertainty -fall_from [get_clocks {clk_stream__early_tap}] -fall_to [get_clocks {clk_stream__early_tap}]  -setup 0.2100
set_false_path\
    -from [get_clocks {clk_serial}]\
    -to [list [get_clocks {clk_stream}]\
           [get_clocks {clk_stream__early_tap}]]
set_false_path\
    -from [list [get_clocks {clk_stream}]\
           [get_clocks {clk_stream__early_tap}]]\
    -to [get_clocks {clk_serial}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
