# strip-protect 2026-10-09: second clock of the standalone ot_s81_ingest_visibility_fence (clk_h, the host link user
# clock, 1 GHz as physical/rom_host_ingest/sdc/hing_clocks_div2.sdc).  core_clk = ck (ack_n counting) comes from the
# route.  The domains cross only through the toggle/ack MCP snapshot handshake (req/ack two-flop synchronisers):
# asynchronous groups.  Host-face ports are timed against clk_h at 20 %, ack_n keeps the core-clock IO budget.
create_clock -name clk_h -period 1000 [get_ports clk_h]
set_clock_uncertainty -setup 60 [get_clocks clk_h]
set_clock_uncertainty -hold 25 [get_clocks clk_h]
set_clock_groups -asynchronous -group [get_clocks clk_h] -group [get_clocks -quiet {core_clk vclk}]
catch {unset_input_delay [get_ports clk_h]}
set ot_fh_in [get_ports {in_v in_d[*] out_cr}]
set ot_fh_out [get_ports {in_cr out_v out_d[*] fault landed_debug[*]}]
catch {unset_input_delay $ot_fh_in}
catch {unset_output_delay $ot_fh_out}
set_input_delay 200 -clock clk_h $ot_fh_in
set_output_delay 200 -clock clk_h $ot_fh_out
set_false_path -from [get_ports rst_n]
