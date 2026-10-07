# HBM SU reducer vehicles (top1024 / slice64) route constraints with the CALIBRATED die IO budget (OWNER rules
# 2026-10-06): appended after the driver SDC (route period 770).  Every data port 0.2T + 150 ps against vclk at the
# planning insertion (measured on the previous route: top 566, slice 831 ps), resets false-pathed.
# Route-time hold over-constraint on inputs (-60 ps); sign-off (signoff_833_io150.sdc) uses -min 0 at the measured
# per-corner insertion.
set ot_L 831
set ot_T [get_property [get_clocks core_clk] period]
create_clock -name vclk -period $ot_T
set_clock_latency $ot_L [get_clocks {core_clk vclk}]
catch {unset_input_delay -clock core_clk [all_inputs -no_clocks]}
catch {unset_output_delay -clock core_clk [all_outputs]}
set ot_d [expr {0.2 * 833.333 + 150}]
set ot_in [all_inputs -no_clocks]
set_input_delay -max $ot_d -clock vclk $ot_in
set_input_delay -min -60 -clock vclk $ot_in
set_output_delay -max $ot_d -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set ot_rst [get_ports -quiet {rst* *rst_n* por_n}]
if {[llength $ot_rst]} { set_false_path -from $ot_rst }
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_in
