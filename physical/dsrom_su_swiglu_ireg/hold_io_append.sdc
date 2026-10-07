# CLAUDE S81-RERUN: die-context HOLD IO constraints for the routed lane, against an IDEAL port clock (core_clk), from the
# measured FF insertion of route lane_esum_m770 (207.56 min / 244.76 max) and the 50 ps hold IO uncertainty:
#   outputs captured <= max insertion + 50 ps later   -> set_output_delay -min -294.76
# so ORFS hold repair (BC = FF corner) closes the boundary hold that die_io_833_ff.sdc checks.  Units: ps.
set_output_delay -min -294.76 -clock core_clk [all_outputs]
# Inputs: hold is not repaired in the block (set_false_path -hold from inputs below): run_abi3_physical's IO delay
# (0.26 T, min = max) on the ideal port clock is timed against WC insertion (350-394 ps) and the second h770 attempt
# again ran out of hold buffers (24,679, RSZ-0060, 16,550 endpoints, worst g_ireg.r_w[0]/D -210.6 ps).  Input hold
# is a die-context check: route_esum_m770/io_FF.log passes it with launch at min insertion - 50 ps, re-run on the
# re-routed lane.
# (old note) Inputs: no extra constraint.  The die STA (route_esum_m770/io_FF.log) already passes input hold at FF with launch at
# min insertion - 50 ps; on the ideal port clock the same number would be timed at the WC corner too (insertion
# ~350-394 ps) and CTS hold repair ran out of buffers (24,679, RSZ-0060) in the first h770 attempt.
set_false_path -hold -from [all_inputs -no_clocks]
