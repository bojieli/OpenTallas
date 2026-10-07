# CLAUDE S81-PH ctrl v2 TILE (dsfd_ctrl_pc): appended after the calibrated margin IO SDC (core_clk = cks).  As
# ctrl_two_clock.sdc (the v1 slab) with the PHY-side ports of the tile timed against vclk_h.
create_clock -name hbm_clk -period 900 [get_ports ckh]
unset_input_delay [get_ports ckh]
set_clock_uncertainty -setup 123 [get_clocks hbm_clk]
set_clock_uncertainty -hold 25 [get_clocks hbm_clk]
create_clock -name vclk_h -period 900
set_clock_uncertainty -setup 123 [get_clocks vclk_h]
set_clock_uncertainty -hold 25 [get_clocks vclk_h]
set_clock_latency 770 [get_clocks {hbm_clk vclk_h}]
# the two roots are asynchronous: every cks <-> ckh arc is a Gray-pointer -> synchroniser or storage-mux -> capture
# datapath budget (as the closed Qwen stream4 CDC, physical/qwen_stream4_cdc/cdc_pc.sdc), here the faster period minus
# the MARGIN-FIRST 123 ps (710.333 ps) both ways; hold needs only a non-negative datapath delay.
set_max_delay -ignore_clock_latency 710.333 -from [get_clocks core_clk] -to [get_clocks hbm_clk]
set_max_delay -ignore_clock_latency 710.333 -from [get_clocks hbm_clk] -to [get_clocks core_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks hbm_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks hbm_clk] -to [get_clocks core_clk]
set ot_phy [get_ports {k_v* k_rdy* k_addr* k_len* k_tag* k_we* k_wdata* k_wstrb* k_wr_done* kr_v* kr_rdy* kr_tag* kr_beat* kr_data*}]
unset_input_delay -clock vclk $ot_phy
unset_output_delay -clock vclk $ot_phy
set_input_delay [expr {900 * 0.2 + 150}] -clock vclk_h $ot_phy
set_output_delay [expr {900 * 0.2 + 150}] -clock vclk_h $ot_phy
set_input_delay -min 0 -clock vclk_h $ot_phy
set_output_delay -min 0 -clock vclk_h $ot_phy
# rst is the asynchronous die reset: every column synchronises it locally (2-flop async-assert / sync-release
# synchronisers in both domains), so the pin -> synchroniser arcs are not timed (assertion is asynchronous by design,
# release is resolved by the synchronisers); the synchronised resets are timed normally inside each column.
set_false_path -from [get_ports rst]
