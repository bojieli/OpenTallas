create_clock -name stream -period 833.3333333333334 [get_ports clk_stream]
set_clock_uncertainty -setup 60 [get_clocks stream]
set_clock_uncertainty -hold 25 [get_clocks stream]
set_clock_transition 40 [get_clocks stream]
set_input_transition 40 [get_ports external_reset_n]
set_input_delay -clock stream -min 100 [get_ports external_reset_n]
set_input_delay -clock stream -max 780 [get_ports external_reset_n]
set_input_delay -clock stream -min 50 [get_ports {ib_go parent_domains_ready}]
set_input_delay -clock stream -max 650 [get_ports {ib_go parent_domains_ready}]
set_input_transition 40 [get_ports {ib_go parent_domains_ready}]
# Root pin intervals are requirements at BOTH provider RESETN pins.
# Parent reset fanout/route must preserve them; these are not measured arrivals.
# Low RESETN pulse >=330ps at both provider pins.
# Inputs remain stable until first accepted edge; all grants/tags are owned.
# Complete-tile payload constraints (use in complete constructed context only):
# set_input_delay -clock stream -min 50 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# set_input_delay -clock stream -max 650 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# set_input_transition 40 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# No falsepaths or waived recovery/removal. Loads and wireRC assigned by graph.
