# CLAUDE S81-PH dsfd_ctrl: appended after common/io_vclk_m_770.sdc (core_clk = cks 833.333 ps, vclk at the measured
# insertion, IO 0.2 T + 150 ps, setup uncertainty 123 = MARGIN-FIRST 770 ps effective).
# Second root: ckh, the HBM-domain clock the ctrl supplies to the PHY (PHY abstract min_period 900 ps: timed at 900, the
# fastest legal HBM clock), same margin (setup uncertainty 123, hold 25).  The PHY bundle phy[*] is timed against a
# virtual HBM clock vclk_h at the measured hbm_clk insertion, 0.2 T + 150 ps budgets.
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
set ot_phy [get_ports {phy[*]}]
unset_input_delay -clock vclk $ot_phy
unset_output_delay -clock vclk $ot_phy
set_input_delay [expr {900 * 0.2 + 150}] -clock vclk_h $ot_phy
set_output_delay [expr {900 * 0.2 + 150}] -clock vclk_h $ot_phy
set_input_delay -min 0 -clock vclk_h $ot_phy
set_output_delay -min 0 -clock vclk_h $ot_phy
# phy[12808] is the PHY clk pin: ckh fed through (the PHY's clock), not a data output
set_false_path -to [get_ports {phy[12808]}]
