# m3 (2026-10-06): the S1 die-context skew boundary of io_lat_skew.sdc, made CORNER-EXACT for the multi-corner ORFS
# stages.  io_wc_skew.sdc wrote the reference arrival as a WC scalar, so BC/FF input hold was never repaired (m2 FF
# -109 ps); -reference_pin (io_ref.sdc) drops input paths in this OpenSTA.  Here the boundary clock is a generated
# clock defined at the reference register's CLK pin: with propagated clocks its source latency is the propagated
# arrival at that pin IN EACH CORNER, so every corner sees
#   input  max = 0.2 T + L + sk      input  min = L - hk
#   output max = 0.2 T - L + sk      output min = -L - hk        (L = arrival at res_q[0]/CLK, that corner)
# Post-CTS only (the tree must exist).  sk = OT_IO_SKEW (90 intra-region), hk = OT_IO_HOLD_SKEW (50).
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
set qss_refpin [get_pins {res_q\[0\]$_DFF_P_/CLK}]
if {[llength [get_clocks -quiet clk_io]] == 0} {
  create_generated_clock -name clk_io -source [get_ports clk] -divide_by 1 $qss_refpin
}
set_propagated_clock [get_clocks clk_io]
# the boundary checks carry the sign-off uncertainty (60 setup / 25 hold) and no CRPR credit through this block's
# own tree (the far register sits in another block): with both, every IO slack equals io_lat_skew.sdc's at sign-off
# (checked on the m2 final ODB: SS res_in -56.44 / FF -109.31 both ways).  CRPR off is flow-only (reg -> reg loses a
# few ps of credit in the flow: conservative); sign-off (tools/w18/corner_sta.py + io_lat_skew90.sdc) is unchanged.
set_clock_uncertainty -setup 60 [get_clocks clk_io]
set_clock_uncertainty -hold 25 [get_clocks clk_io]
set sta_crpr_enabled 0
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qss_in  [get_ports {rst_n p_* res_in*}]
set qss_out [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
set qss_T [get_property [get_clocks clk] period]
set_input_delay  [expr {0.2 * 833.333 + $ot_sk}] -max -clock clk_io $qss_in
set_input_delay  [expr {-$ot_hk}]                -min -clock clk_io $qss_in
set_output_delay [expr {0.2 * 833.333 + $ot_sk}] -max -clock clk_io $qss_out
set_output_delay [expr {-$ot_hk}]                -min -clock clk_io $qss_out
puts "QSS S1 boundary: generated clock clk_io at res_q[0]/CLK, skew $ot_sk hold $ot_hk"
