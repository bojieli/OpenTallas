# block constraints (tools/hbm_accel_smh_physical.py); clock 770 ps (sign-off 833: run.sh rewrites the
# period of the routed SDC), 60 / 25 ps uncertainty
set clk_period 770
create_clock -name core_clk -period $clk_period [get_ports clk]
create_clock -name nbr_clk -period $clk_period
# the neighbour's flop sits at this block's own clock insertion, in each corner.  One SDC serves both corners
# and STA reads -min / -max latency as early / late (a setup check captures an output at the EARLY latency),
# so nbr_clk carries the SS insertion alone; the FF hold check at an output port, where the neighbour
# captures 329 - 269 ps earlier than SS, takes that difference in the output min delay (dlo below).
# At SS the output hold holds by construction (same insertion both sides); input hold at FF is checked by
# the parent on the real pair.
set_clock_latency -source 329 [get_clocks nbr_clk]
# setup-triage 2026-10-07: the latency above is a PLANNING insertion; sign-off must re-reference nbr_clk to the routed
# block's measured insertion with physical/common_flow/nbr_clk_measured.sdc as a post-SDC (front_n: planning
# 688 vs measured 506..600 cost the element inputs 135 ps: SS in2reg -53.6 -> +81.4 on re-STA).
set dlo 60
# (margin rule, clarified 2026-10-06) setup: abutting ports between pieces of one element (one clock region)
# budget the region pair skew + 25 (skew); the element pins cross a die wire to another region (die_skew).
# Hold: FF-corner insertion (dlo) and a 50 ps IO uncertainty (hold_io) on the SENDER output min only (rule H1,
# h1-verify 2026-10-08: the receiver input min carried it too), closed by hold repair.
set skew 90
set die_skew 150
set hold_io 50
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
set nbr_in [get_ports {gin* qin* cgi}]
set nbr_out [all_outputs]
# abutting ports: 300 ps of the neighbour's flop / wire outside, its clock insertion carried by nbr_clk
set_input_delay -max [expr 300 + $skew] -clock nbr_clk $nbr_in
set_input_delay -min 30 -clock nbr_clk $nbr_in   ;# RULE H1: hold_io on the sender output min only
set_output_delay -max [expr 300 + $skew] -clock nbr_clk $nbr_out
set_output_delay -min [expr 50 + $dlo - $hold_io] -clock nbr_clk $nbr_out   ;# the neighbour lands it >= 50 ps inside (top STA checks the real pair)
set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
