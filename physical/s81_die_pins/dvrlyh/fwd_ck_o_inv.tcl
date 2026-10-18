# S81-LAND2 half-cycle lane relays (dsfd_dvrlyh_*, ot_dvrly_st HC=1), sdc_extra (re-applied after every io_ref switch
# and at sign-off).  ck_o is the lane's forwarded CLOCK output, ck through ONE kept inverter (ck_o = ~ck): the next
# station captures on the opposite edge, half a period after this one (LANDING-CONTRACT H3 fix (a)).  As a data pin the
# io_ref output budget would time ck -> ck_o as an I2O path -> generated clock ck_o_fwd (divide_by 1, INVERTED), no
# output delay on it.  o[] / i[] keep the common-clock boundary budget of the tile (launch / capture on the ck posedge);
# the half-cycle forwarded-clock vs data skew over the die wire is the die's hop check.
if {[llength [get_ports -quiet ck_o]] && [llength [get_ports -quiet ck]]} {
  unset_output_delay [get_ports ck_o]
  if {![llength [get_clocks -quiet ck_o_fwd]]} {
    create_generated_clock -name ck_o_fwd -source [get_ports ck] -divide_by 1 -invert [get_ports ck_o]
  }
  puts "OT_FWD_CK_O: ck_o = generated clock ck_o_fwd (INVERTED ck, half-cycle hop), no data budget"
}
