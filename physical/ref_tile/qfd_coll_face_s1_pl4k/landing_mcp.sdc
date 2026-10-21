# QW-COLLIO2 10-21: PHY landing rings (ot_coll_meso_ring D=4, K=2) of qfd_coll_face_s1_pl4f: slot written at edge j is read
# at j+K and overwritten at j+D -> ring slot -> read capture paths: -setup K(2) -hold D-1(3).  Slots feed only the read side.
set ot_pl_from [get_cells -quiet {*u_rx_land*sl_q* *u_tx_land*sl_q*}]
if {[llength $ot_pl_from] > 0} {
  set_multicycle_path -setup 2 -from $ot_pl_from
  set_multicycle_path -hold 3 -from $ot_pl_from
}
puts "OT_PHYLAND_SDC [llength $ot_pl_from] slot cells multicycled (setup 2 hold 3)"
