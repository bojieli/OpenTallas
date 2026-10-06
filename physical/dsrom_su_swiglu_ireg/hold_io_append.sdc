# CLAUDE S81-RERUN: die-context HOLD IO constraints for the routed lane, against an IDEAL port clock (core_clk), from the
# measured FF insertion of route lane_esum_m770 (207.56 min / 244.76 max) and the 50 ps hold IO uncertainty:
#   inputs  launch >= min insertion - 50 ps           -> set_input_delay  -min 157.56
#   outputs captured <= max insertion + 50 ps later   -> set_output_delay -min -294.76
# so ORFS hold repair (BC = FF corner) closes the boundary hold that die_io_833_ff.sdc checks.  Units: ps.
set_input_delay -min 157.56 -clock core_clk [get_ports {v g[*] u[*] w[*] lim[*]}]
set_output_delay -min -294.76 -clock core_clk [all_outputs]
