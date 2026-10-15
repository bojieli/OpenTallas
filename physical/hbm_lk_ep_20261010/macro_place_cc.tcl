# el1011-hbm-lkep 2026-10-11 (MPL=macro_place_cc.tcl): CENTRE-CHANNEL floorplan, macro order follows the data flow.
# Why (textbook audit, class 6): the retry macro pins are all on its E edge (2,400 pins / 460 um).  macro_place.tcl puts
# macros 0 / 1 in the W column (pin faces at x 798) and macro 2 R0 at x 948 -- so 0 / 1 face macro 2's pinless back and
# their 2 x ~2,300-signal buses detour around it to the shared logic at the E face (> 1,000 um).  Here the W column moves
# to x 21.6 (pin faces at x 711.6) and macro 2 is MIRRORED (MY: pins on its W edge at x 948.24): all three pin faces open
# onto one 236-um channel that holds the shared logic (TX queues, grant / CRC, merge, gearbox); the E-face die / phy
# buses cross to it through the bands above / below macro 2 on pin flop + 2 relays (hfd_lk_ep.sv, XR = 2).
set ot_dh [expr {double([[[ord::get_db_block] getDieArea] dy]) / [[ord::get_db_tech] getDbUnitsPerMicron]}]
if {$ot_dh >= 1300.0} {
  set pos {{21.6 64.8 R0} {21.6 870.48 R0} {948.24 470.88 MY}}
} else {
  set pos {{21.6 21.6 R0} {21.6 524.88 R0} {948.24 267.84 MY}}
}
set n 0
foreach inst [lsort [lmap i [[ord::get_db_block] getInsts] {expr {[[$i getMaster] getName] eq "ot_hbm_link_retry_pipeline" ? [$i getName] : [continue]}}]] {
  set p [lindex $pos $n]
  place_macro -macro_name $inst -location [lrange $p 0 1] -orientation [lindex $p 2]
  incr n
}
puts "OT_LKEP_CC macros placed: $n (die height $ot_dh)"
