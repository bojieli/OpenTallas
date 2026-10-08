# CLAUDE S81-PH coll v2 clock tile (dsfd_coll_ck): the v1 slab clock definitions (coll_clocks.sdc) without the lane outputs.
# CLAUDE S81-PH collective view clocks (appended after common/io_vclk_m_770.sdc).  The slab's clock is generated
# INSIDE it by the die PLL (ot_s81_pll_bb, hard IP): core_clk is redefined at the PLL's ck_stream pin (1.2 GHz);
# refclk (100 MHz reference, reset sequencer) and the pass-through serial / HBM clocks are separate, asynchronous to
# core_clk inside this view (the reset outputs are asynchronous assertions whose release every consumer synchronises).
set ot_per [get_property [get_clocks core_clk] period]
create_clock -name core_clk -period $ot_per [get_pins u_pll/ck_stream]
create_clock -name ref_clk -period 10000 [get_ports refclk]
create_clock -name ser_clk -period 1111.111 [get_pins u_pll/ck_serial]
create_clock -name hbm_clk -period 1024 [get_pins u_pll/ck_hbm]
set_clock_groups -asynchronous -group {core_clk vclk} -group {ref_clk} -group {ser_clk} -group {hbm_clk}
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk vclk}]
set_clock_latency 770 [get_clocks {core_clk vclk}]
# clock / forwarded-clock / reset outputs and the asynchronous por input are not data paths of this view
set_false_path -to [get_ports {pll_stream* pll_serial* pll_hbm* rst_stream* rst_serial* rst_hbm*}]
set_false_path -from [get_ports {por*}]
