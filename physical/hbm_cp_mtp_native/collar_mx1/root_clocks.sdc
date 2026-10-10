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
        set_clock_uncertainty -setup 123 [get_clocks $name]
        set_clock_uncertainty -hold 25 [get_clocks $name]
    }
}
# fclat.sdc is generated from this candidate's core_clk calibration, separately
# for TT and FF. It supplies source latency on these port leaves. It does not
# alter the generated-clock relationship or idealize any physical tree.
