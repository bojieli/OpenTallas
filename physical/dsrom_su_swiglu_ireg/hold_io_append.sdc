# CLAUDE S81-RERUN: die-context HOLD IO constraints for the routed lane, against an IDEAL port clock (core_clk), from the
# measured FF insertion of route lane_esum_m770 (207.56 min / 244.76 max) and the 50 ps hold IO uncertainty:
#   outputs captured <= max insertion + 50 ps later   -> set_output_delay -min -294.76
# so ORFS hold repair (BC = FF corner) closes the boundary hold that die_io_833_ff.sdc checks.  Units: ps.
set_output_delay -min -294.76 -clock core_clk [all_outputs]
# Inputs: no extra constraint.  The die STA (route_esum_m770/io_FF.log) already passes input hold at FF with launch at
# min insertion - 50 ps; on the ideal port clock the same number would be timed at the WC corner too (insertion
# ~350-394 ps) and CTS hold repair ran out of buffers (24,679, RSZ-0060) in the first h770 attempt.
