create_clock -name clk_stream -period 833.333 [get_pins root_clk_stream/Y]
create_clock -name clk_serial -period 833.333 [get_pins root_clk_serial/Y]
create_clock -name clk_hbm -period 833.333 [get_pins root_clk_hbm/Y]
create_clock -name clk_link -period 833.333 [get_pins root_clk_link/Y]
