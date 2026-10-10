# MX1 TILECLK=1: related die leaves (port clocks, core_clk period, default waveform as core_clk), separate roots, physical propagation kept.
# The die delivers each face leaf so that its SINKS land at the measured interior insertion (fclat.sdc from
# mx1_fclat.py: source = reference - local leaf insertion; option-1 balanced at the sinks). Local face trees and
# cross-root lockup hops stay propagated and timed; nothing is subtracted from paths or uncertainty.
set ot_mx1_period [get_property [get_clocks core_clk] period]
foreach {port name} {cks[0] mx1_s ckn[0] mx1_n cke0[0] mx1_e0 cke1[0] mx1_e1 ckw0[0] mx1_w0 ckw1[0] mx1_w1} {
    if {[llength [get_ports -quiet $port]]} {
        # Port-sourced die leaf with core_clk's period and waveform (FT6 calibrate died on a generated clock: no
        # master->port path exists, STA-1062, and link_budget_consistent.sdc cannot map it to a master). Same-period
        # clocks are related in STA: every cross-root path stays timed; no clock groups.
        create_clock -name $name -period $ot_mx1_period [get_ports $port]
        # The base SDC set data input delays on [all_inputs -no_clocks] before this leaf became a clock (FT8: vclk
        # 316.6 on cke1 -> timed the forwarded-clock inverter as a data path from an input delay). A clock port has none.
        foreach ot_c {vclk core_clk} { if {[llength [get_clocks -quiet $ot_c]]} { unset_input_delay -clock [get_clocks $ot_c] [get_ports $port] } }
        set_clock_uncertainty -setup 123 [get_clocks $name]
        set_clock_uncertainty -hold 25 [get_clocks $name]
    }
}
# fclat.sdc / fclat_ff.sdc (mx1_fclat.py, this job's calibrate) supply the leaf source latencies per corner; no
# physical tree is idealised.
# Forwarded clocks (ot_fwd_clk_inv u_fclk_0..3 = ~face leaf onto cSE/cSW[824:825], RTL hfd_cmdproc_s_fc.sv): these four
# ports carry a clock that the AR station captures its bus on (half a period after the launching edge), so they are
# defined as the clocks they are (generated, inverted, from their face leaf) instead of being timed as data outputs
# against vclk (FT8: clock-as-data -74 ps). The fclk/data relation belongs to the receiving station's source-synchronous
# check; nothing else changes and no path is cut.
foreach {port src name} {cSE[824] cke1[0] mx1_fwd_e0 cSE[825] cke1[0] mx1_fwd_e1 cSW[824] ckw1[0] mx1_fwd_w0 cSW[825] ckw1[0] mx1_fwd_w1} {
    if {[llength [get_ports -quiet $port]] && [llength [get_ports -quiet $src]]} {
        create_generated_clock -name $name -source [get_ports $src] -divide_by 1 -invert [get_ports $port]
        foreach ot_c {vclk core_clk} { if {[llength [get_clocks -quiet $ot_c]]} { unset_output_delay -clock [get_clocks $ot_c] [get_ports $port] } }
    }
}
