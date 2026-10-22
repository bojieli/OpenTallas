# HBM-HCROOT8 10-20: declared multicycle of the HC tail child's Sinkhorn step (ot_hbm_hc_tail_child_static SKCE 1).
# RTL: the Sinkhorn (ot_hdc_sinkhorn_ce) runs on the core clock; every one of its registers updates only on an edge where
# its enable ce = sclk is 1, and sclk is ONE flop that is high one core cycle in SDIV = 7 (free-running divider, reset to 0).
# So a path that starts AND ends at a Sinkhorn register has exactly SDIV core periods (one normalisation step per enable,
# the ot_hdc_sinkhorn header's multicycle; priced in the tail calendar since 10-15: L = 198 + SDIV + CAP + 2).  Every other
# path (into the Sinkhorn from the clk-domain tail, out of it to the capture, the enable itself) is single-period.
# The gate-level cloned netlist names exactly the Sinkhorn cells sk_c<i> (tools/hbm_hc/bound_fanout_clone.py --tag
# sk_=u_tail.g_skce.sink.); the flow may wrap the netlist (reset landing -> u_ot_pr_core.*), so match by suffix.
set ot_skc [get_cells -quiet {sk_c* *.sk_c* */sk_c*}]
if {[llength $ot_skc] == 0} { set ot_skc [get_cells -quiet -hierarchical {*sk_c*}] }
set ot_skr {}
foreach ot_c $ot_skc { if {[string match DFF* [get_property $ot_c ref_name]]} { lappend ot_skr $ot_c } }   ;# OpenSTA: a collection is a Tcl list
puts "OT_TAILC_SKMCP sinkhorn cells [llength $ot_skc] registers [llength $ot_skr]"
if {[llength $ot_skr] < 1000} { error "tailc_skmcp.sdc: expected >= 1000 Sinkhorn registers sk_c*, found [llength $ot_skr]" }
set_multicycle_path -setup 7 -from $ot_skr -to $ot_skr
set_multicycle_path -hold 6 -from $ot_skr -to $ot_skr
