# ot_rom_host_ingest block SDC append (stream ingest 2026-10-08).  Time unit = the library's (ps on ASAP7).
# core_clk (ck, the die clock) comes from run_abi3_physical; clk_i = the ingest core clock = ck / 2 (own root);
# clk_h = the host link user clock (1 GHz).  The three domains cross only through Gray-pointer async FIFOs and a
# toggle-qualified static CSR, so they are asynchronous groups.  Host-face IO is timed against clk_h at 20 %.
# struct-close 2026-10-09: clk_period exists only in the ORFS SDC; the sign-off corner_sta session reads this file as a
# --post-sdc where it is undefined (Tcl error -> null metrics -> hing_dsfd_A/B, hing_hfd_A "verdict inputs missing").
if {![info exists clk_period]} { set clk_period [get_property [get_clocks core_clk] period] }
create_clock -name clk_i -period [expr $clk_period * 2] [get_ports clk_i]
create_clock -name clk_h -period 1000 [get_ports clk_h]
set_clock_uncertainty -setup 60 [get_clocks {clk_i clk_h}]
set_clock_uncertainty -hold 25 [get_clocks {clk_i clk_h}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks clk_i] -group [get_clocks clk_h]
set ot_hing_ck [get_ports {clk_i clk_h}]
catch {unset_input_delay $ot_hing_ck}
set ot_hing_in [get_ports {h_v h_cls[*] h_d[*] t_cr}]
set ot_hing_out [get_ports {h_crn[*] t_v t_d[*]}]
catch {unset_input_delay $ot_hing_in}
catch {unset_output_delay $ot_hing_out}
set_input_delay 200 -clock clk_h $ot_hing_in
set_output_delay 200 -clock clk_h $ot_hing_out
set_false_path -from [get_ports rst_n]
puts "OT_HING clocks: clk_i = ck / 2, clk_h 1000, async groups"
