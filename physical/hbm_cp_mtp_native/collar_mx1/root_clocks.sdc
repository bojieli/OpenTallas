# MX1 TILECLK=1: related die leaves, separate roots, physical propagation kept.
# The die delivers each face leaf at the measured interior insertion. This is
# option1 source latency; local face-tree insertion and cross-root lockup timing
# are real obligations, not subtracted from either path or clock uncertainty.
set ot_mx1_period [get_property [get_clocks core_clk] period]
foreach {port name} {cks[0] mx1_s ckn[0] mx1_n cke0[0] mx1_e0 cke1[0] mx1_e1 ckw0[0] mx1_w0 ckw1[0] mx1_w1} {
    if {[llength [get_ports -quiet $port]]} {
        create_generated_clock -name $name -source [get_ports {ck[0]}] -master_clock core_clk -divide_by 1 [get_ports $port]
        set_clock_uncertainty -setup 123 [get_clocks $name]
        set_clock_uncertainty -hold 25 [get_clocks $name]
    }
}
# fclat.sdc is generated from this candidate's core_clk calibration, separately
# for TT and FF. It supplies source latency on these port leaves. It does not
# alter the generated-clock relationship or idealize any physical tree.
