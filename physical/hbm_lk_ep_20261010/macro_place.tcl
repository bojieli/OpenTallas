# [link] 2026-10-10 hfd_lk_ep: 3 closed retry macros (ot_hbm_link_retry_pipeline view_wpin_hm10, 690 x 460, R0 ONLY:
# tools/check_macro_track_alignment.py allows no mirrored orientation for this abstract).  R0 faces: W = in_data /
# tx_data (681 pins), S = in_data / tx_data (383), N = out_data / rx_data (918), E = out / rx (137).  All die pins are on
# the EAST face (phy y 0.6-188, f_lk y 783-993).  Origins on the 2.16 um (y) / 0.432 um (x) grid = the M4 / M5 48-nm
# tracks AND the 0.27 row / 0.054 site grid.
# 304cd8c93 preroute: the two west macros had their W faces (681 pins) 19.44 um from the die edge, so every in_data /
# tx_data net ran around the macro (u.wsel -> u_rp/in_data 3.4 ns of wire).  Now the west column stands 108 / 151 um off
# the west edge (a W channel for its A faces), the east macro has a 150-160 um W channel between the columns.
#  die height >= 1300 (taller slot, the [link] -> [fp] ask): column (M0 bottom, M1 top) with a 345-um middle band (M0's
#     N face + M1's S face + the RX / TX shared logic), 65 / 73 um bottom / top bands; M2 mid-height in the east column
#     between phy (below) and f_lk (above).
#  else (R25GQ slot 1,728 x 1,015.2): the same arrangement squeezed: bands 21.6 / 43.3 / 30.3 um.
set ot_dh [expr {double([[[ord::get_db_block] getDieArea] dy]) / [[ord::get_db_tech] getDbUnitsPerMicron]}]
if {$ot_dh >= 1300.0} {
  set pos {{151.2 64.8} {151.2 870.48} {1004.4 250.56}}
} else {
  set pos {{108.0 21.6} {108.0 524.88} {948.24 267.84}}
}
set n 0
foreach inst [lsort [lmap i [[ord::get_db_block] getInsts] {expr {[[$i getMaster] getName] eq "ot_hbm_link_retry_pipeline" ? [$i getName] : [continue]}}]] {
  place_macro -macro_name $inst -location [lindex $pos $n] -orientation R0
  incr n
}
puts "OT_LKEP macros placed: $n (die height $ot_dh)"
