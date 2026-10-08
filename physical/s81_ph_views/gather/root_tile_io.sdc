# CLAUDE S81-PH root tile: every data port is an abutted chain hop inside one clock region (budget sheet
# ot_s81ph_root_tile: skew class intra, 69 ps, L <= 1.1 um): die clock-arrival term 69 ps, not 150 ps.
set ot_ri [get_ports -quiet {ci* fi* li_e* li_w* lt_ei* lt_wi* sel*}]
set ot_ro [get_ports -quiet {co* fo* lt_eo* lt_wo* rso*}]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 69}] -clock vclk $ot_ri
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 69}] -clock vclk $ot_ro
