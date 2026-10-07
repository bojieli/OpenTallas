# m3 (2026-10-06): the S1 die-context skew boundary of io_lat_skew.sdc, CORNER-EXACT for the multi-corner ORFS stages,
# written with -reference_pin res_q[0]/CLK (the propagated arrival at the reference register in each corner):
#   input  max = 0.2 T + L + sk      input  min = L - hk
#   output max = 0.2 T - L + sk      output min = -L - hk         (as io_lat_skew.sdc, one L per corner)
# Checked on the m3 CTS ODB with WC + BC corners defined: WC setup and BC hold launch/capture at that corner's arrival.
# This OpenSTA reports no WC min path from a -reference_pin input (the "io_ref drops input paths" note): the input hold
# is checked at BC, the hold sign-off corner (FF), which is exact; the WC input hold is not a sign-off check.
# Rejected alternatives: io_wc_skew.sdc (WC scalar: BC/FF input hold never repaired, m2 FF -109 ps); a generated clock
# at the reference pin (OpenSTA takes the MIN latency over corners for every hold check: fake WC input hold -445 ps).
# Post-CTS only; read after load_design.  sk = OT_IO_SKEW (90 intra-region), hk = OT_IO_HOLD_SKEW (50).
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
set qss_ref [get_pins {res_q\[0\]$_DFF_P_/CLK}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qss_in  [get_ports {rst_n p_* res_in*}]
set qss_out [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
set_input_delay  [expr {0.2 * 833.333 + $ot_sk}] -max -clock clk -reference_pin $qss_ref $qss_in
set_input_delay  [expr {-$ot_hk}]                -min -clock clk -reference_pin $qss_ref $qss_in
set_output_delay [expr {0.2 * 833.333 + $ot_sk}] -max -clock clk -reference_pin $qss_ref $qss_out
set_output_delay [expr {-$ot_hk}]                -min -clock clk -reference_pin $qss_ref $qss_out
puts "QSS S1 boundary: -reference_pin res_q\[0\]/CLK, skew $ot_sk hold $ot_hk"
