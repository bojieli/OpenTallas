# phys-intake 2026-10-09: second clock of ot_hbm_tu_retry_phy_port (PHY/FEC side, pclk), 833.333 ps like the core clock.
# The two domains cross only through the gray/pulse CDCs of ot_hbm_retry_pop_cdc / ot_hbm_retry_phy_ingress: async groups.
# PHY-side ports are timed against pclk with the same 0.2 T budget the core-side ports get against vclk (io_vclk_m).
create_clock -name pclk -period 833.333 [get_ports pclk]
set_clock_uncertainty -setup 60 [get_clocks pclk]
set_clock_uncertainty -hold 25 [get_clocks pclk]
set_clock_groups -asynchronous -group [get_clocks pclk] -group [get_clocks -quiet {core_clk vclk}]
set ot_pp [get_ports -quiet {phy_link_up phy_session* fec_tx_ready fec_rx_v fec_rx_ue fec_rx_data* fec_rx_seq* fec_rx_session* fb_valid fb_good fb_nak fb_seq* fb_session* fb_pop*}]
set ot_po [get_ports -quiet {fec_tx_v fec_tx_data* fec_tx_seq* fec_tx_session* fec_rx_ready ack_seq* ack_nak ack_session* ack_pop*}]
if {[llength $ot_pp]} { set_input_delay [expr 833.333 * 0.2] -clock pclk $ot_pp }
if {[llength $ot_po]} { set_output_delay [expr 833.333 * 0.2] -clock pclk $ot_po }
set_false_path -from [get_ports -quiet {prst_n rst_n}]
