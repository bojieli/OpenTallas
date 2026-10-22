# HC bank rw2: use existing exact macro-pin anchors, without changing shared helpers.
set ot_hcb_wdpins {}
for {set ot_hcb_bit 0} {$ot_hcb_bit < 256} {incr ot_hcb_bit} {
  lappend ot_hcb_wdpins [format {wd_in[%d]} $ot_hcb_bit]
}
set ::env(OT_MPFLOP_PINS) [join $ot_hcb_wdpins ,]
set ::env(OT_MPFLOP_GAP) 5.4
