# Replace the driver primary clock and its default all-port delays.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
delete_clock [all_clocks]
# ASAP7 liberty time unit is ps: numeric SDC values below are ps.
# Isolated digital-body pathfinding; analog PLL insertion and die reset loads pending.
create_clock -name stream -period 833.333333 [get_ports clk_stream]
create_clock -name serial -period 1111.111111 [get_ports clk_serial]
create_clock -name hbm -period 1024 [get_ports clk_hbm]
create_clock -name link -period 833.333333 [get_ports clk_link]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Reset intents are asynchronous AON inputs. Recovery/removal is not waived.
# Provisional arrival range keeps their checks visible until AON timing is bound.
set_input_delay -min 25 -clock hbm [get_ports {por_n pll_reset_n pll_lock phy_reset_intent_n*}]
set_input_delay -max 100 -clock hbm [get_ports {por_n pll_reset_n pll_lock phy_reset_intent_n*}]
set_input_delay -min 25 -clock link [get_ports {link_reset_intent_n*}]
set_input_delay -max 100 -clock link [get_ports {link_reset_intent_n*}]
set_input_delay -min 25 -clock stream [get_ports {coll_reset_intent_n cmd_reset_intent_n}]
set_input_delay -max 100 -clock stream [get_ports {coll_reset_intent_n cmd_reset_intent_n}]
set_output_delay -min 25 -clock hbm [get_ports phy_reset_n*]
set_output_delay -max 100 -clock hbm [get_ports phy_reset_n*]
set_output_delay -min 25 -clock link [get_ports link_reset_n*]
set_output_delay -max 100 -clock link [get_ports link_reset_n*]
set_output_delay -min 25 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -max 100 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -min 25 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set_output_delay -max 100 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
