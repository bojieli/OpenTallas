# H-HARDEN 10-15: hfd_ckgen clock tile (PLL hard core ot_hbm_pll_bb + four real reset-release synchronisers).
# The four domain clocks are generated INSIDE the tile at the PLL output pins (analog hard IP; the die tree roots);
# refclk is the reference only (no register of this tile is clocked by it).  The pll_* outputs are clock forwards into
# the die tree and the por_* outputs asynchronous assert / domain-synchronous release resets: not data paths here.
# core_clk (the flow's boundary-reference clock) is redefined at the PLL stream output, as the S81 clock tile does;
# refclk becomes the separate 100 MHz reference clock ref_clk.
create_clock -name core_clk -period 833.333 [get_pins u_pll/clk_stream]
create_clock -name ref_clk -period 10000 [get_ports refclk]
create_clock -name ck_serial -period 1111.111 [get_pins u_pll/clk_serial]
create_clock -name ck_hbm -period 1024 [get_pins u_pll/clk_hbm]
create_clock -name ck_link -period 833.333 [get_pins u_pll/clk_link]
if {!$::ot_ref_pre_cts} { set_propagated_clock [all_clocks] }
set_clock_groups -asynchronous -group {core_clk} -group {ref_clk} -group {ck_serial} -group {ck_hbm} -group {ck_link}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -to [get_ports {pll_* por_stream por_serial por_hbm por_link}]
set_false_path -from [get_ports por_n]
