# CLAUDE S81-RERUN die-context IO sign-off of ot_dsrom_su_swiglu_lane (IREG = 1), route lane_esum_m770, SS corner.
# Sign-off period 0.833333 ns (route over-constrained at 0.770).  OWNER MARGIN-FIRST IO rule: the die clock-arrival
# difference (150 ps, another clock region) + 50 ps wire to the nearest die station, budgeted AGAINST THE BLOCK'S
# MEASURED INSERTION: the IO clock is a virtual clock whose latency is the routed tree's measured insertion
# (report_clock_latency, this corner: min 345.19 / max 394.36 SS, 207.56 / 244.76 FF), taken on the pessimistic side
# per direction.  Setup: 200 ps IO delays.  Hold: 50 ps hold IO uncertainty.  (-reference_pin crashes this OpenROAD
# build in Sim::findDisabledEdges.)  Units: ps.
create_clock -name core_clk -period 833.333 [get_ports {clk}]
set_clock_uncertainty -setup 60.0 core_clk
set_clock_uncertainty -hold 25.0 core_clk
set_propagated_clock [get_clocks core_clk]
create_clock -name io_in -period 833.333
create_clock -name io_out -period 833.333
set_clock_latency 394.36 [get_clocks io_in]
set_clock_latency 345.19 [get_clocks io_out]
set_clock_uncertainty -setup 60.0 [get_clocks {io_in io_out}]
set_clock_uncertainty -hold 25.0 [get_clocks {io_in io_out}]
set ins [get_ports {v g[*] u[*] w[*] lim[*]}]
set outs [all_outputs]
set_input_delay -max 200.0 -clock io_in $ins
set_input_delay -min -50.0 -clock io_in $ins
set_output_delay -max 200.0 -clock io_out $outs
set_output_delay -min -50.0 -clock io_out $outs
