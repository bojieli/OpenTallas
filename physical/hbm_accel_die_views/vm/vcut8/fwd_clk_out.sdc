# vcut8 outer halves (hfd_vm_{sw,nw}_w, hfd_vm_{se,ne}_e): forwarded-clock output bits q<Q>[581:580] and x<Q>[2067:2063]
# carry ~tap leaf through a kept ot_fwd_clk_inv (make_vm_vcut8.py out(fclk=...)); they are the capture clocks of the
# receiving die block for the q / x buses launched on the SAME tap leaf, not data of this view.  Timed as data against
# vclk they were the only I2O hold class of every outer half (hbm_vm8bfq_{nee,see,nww}_328df2a09: 7 endpoints, -30..-43
# ps FF, cke<t> -> ot_fclk_root_buf -> u_fclk -> port, "route hold repair stalled") and also failed TT setup as data
# (-19 / -11 ps).  Same treatment as hfd_router fclk_ports_signoff.sdc and s81_ph_views/common/fwd_clk_out.sdc: the
# fclk-vs-data relation is checked in die context (receiver captures on this clock), not in the view's vclk IO check.
set ot_fc [list]
foreach ot_q {SW NW SE NE} {
    foreach ot_b {580 581} { set ot_p [get_ports -quiet "q${ot_q}\[$ot_b\]"]; if {[llength $ot_p]} { lappend ot_fc $ot_p } }
    foreach ot_b {2063 2064 2065 2066 2067} { set ot_p [get_ports -quiet "x${ot_q}\[$ot_b\]"]; if {[llength $ot_p]} { lappend ot_fc $ot_p } }
}
if {[llength $ot_fc]} { set_false_path -to $ot_fc; puts "OT_FWDCLK vcut8 fwd_clk_out: [llength $ot_fc] forwarded-clock output(s) out of the vclk IO check" }
