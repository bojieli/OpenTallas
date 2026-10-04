# Gated stage clock spine with synchronised crossings (2026-10-04).  aon_clk is the always-on island's branch of the
# same stage clock (a separate port so clock-tree synthesis builds the spine and the AO branch as separate trees, as
# the die does); same period and 60 ps setup / 25 ps hold uncertainty, including inter-clock paths.
unset_input_delay -clock core_clk [get_ports aon_clk]
create_clock -name aon_clk -period $clk_period [get_ports aon_clk]
set_clock_uncertainty -setup 60 [get_clocks aon_clk]
set_clock_uncertainty -hold 25 [get_clocks aon_clk]
set_clock_uncertainty -setup 60 -from [get_clocks core_clk] -to [get_clocks aon_clk]
set_clock_uncertainty -setup 60 -from [get_clocks aon_clk] -to [get_clocks core_clk]
set_clock_uncertainty -hold 25 -from [get_clocks core_clk] -to [get_clocks aon_clk]
set_clock_uncertainty -hold 25 -from [get_clocks aon_clk] -to [get_clocks core_clk]
# Clock-domain crossings (ot_v41_rom_stage_pg_cdc.sv): the first flop of every 2-flop synchroniser and the reset
# synchroniser (asynchronous assert, synchronised release) are not timed; the replay address/data are quasi-static
# (held from the request toggle until the ack returns through two synchronisers), bounded to one period datapath-only.
set_false_path -to [get_cells -hierarchical {*cdc_bs1* *cdc_rr1* *cdc_ak1* *cdc_ra1* *cdc_rq1* *cdc_rd1* *cdc_dr1* *cdc_dr2*}]
set_max_delay 833 -ignore_clock_latency -from [get_cells -hierarchical {*cdc_rp_a* *cdc_rp_d*}]
set_false_path -hold -from [get_cells -hierarchical {*cdc_rp_a* *cdc_rp_d*}]
