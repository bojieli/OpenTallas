# S81-DV 276-b lane relays (dsfd_dvrly_276_*), sdc_extra (re-applied after every io_ref switch and at sign-off).
# ck_o is the lane's forwarded CLOCK output (ck through two kept inverters, non-inverted; DIE-CLOCK F1: the next
# station's ck is this station's ck_o on a single-sink hop net), not a data pin.  As a data pin the io_ref output budget
# would time ck -> ck_o as an I2O path (the stnh/stnv fo0 10:09 lesson: FF hold "pin register missing").
# -> generated clock ck_o_fwd (divide_by 1, non-inverted), no output delay on it.  o[] / i[] keep the common-clock
# boundary budget of the tile: every bit is launched / captured on the ck posedge, and the next station captures on the
# same-phase forwarded edge one cycle later; the forwarded-clock vs data skew over the die wire is the die's hop check.
if {[llength [get_ports -quiet ck_o]] && [llength [get_ports -quiet ck]]} {
  unset_output_delay [get_ports ck_o]
  if {![llength [get_clocks -quiet ck_o_fwd]]} {
    create_generated_clock -name ck_o_fwd -source [get_ports ck] -divide_by 1 [get_ports ck_o]
  }
  puts "OT_FWD_CK_O: ck_o = generated clock ck_o_fwd (non-inverted ck), no data budget"
}
