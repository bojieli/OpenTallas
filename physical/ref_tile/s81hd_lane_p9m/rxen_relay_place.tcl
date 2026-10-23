# PRE_GLOBAL_PLACE(_SKIP_IO) hook (STW-S81c-DIE4-LANE3 10-22): the rxen -> u_ln/rx[0] landed relay chain (RTL
# ot_s81hd_lane_sc6/sc4.sv: rxen beside r_misc at the adapter column, rxen_m, rxen_w) placed FIRM at its stations through
# global placement, released before DPL (rxen_relay_release.tcl).  Why: wirelength-driven GPL is indifferent to where
# the stages of a collinear register chain sit (same HPWL) and stacked rxen_m / rxen_w beside rxen at x~776 (gate
# 412ac948a: rx[0] still -380 / -346 ps over the 1.05-mm route).  Route = down the lane's E channel to the S ring
# (y 20 um, below the lane's 5.4-um halo), W along the ring to the lane's W-face pin rx[0] (43.2, 45.65); stations at
# 1/3 and 2/3 of its ~1.09 mm (~360-um hops, reach 405).
set ot_rx_blk [ord::get_db_block]
set ot_rx_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_rx_plan {rxen_m {743.0 20.0} rxen_w {380.0 20.0}}
set ot_rx_rows [$ot_rx_blk getRows]
set ot_rx_done {}
foreach i [$ot_rx_blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {![string match DFF* [[$i getMaster] getName]] || ![regexp {^u_ot_pr_core[./](rxen_[mw])(\$|$)} $n -> k]} continue
  set xy [dict get $ot_rx_plan $k]
  set tx [expr {round([lindex $xy 0] * $ot_rx_dbu)}]; set ty [expr {round([lindex $xy 1] * $ot_rx_dbu)}]
  # snap to the nearest row origin / site
  set best ""; set bd 1e18
  foreach r $ot_rx_rows {
    set o [$r getOrigin]; set d [expr {abs([lindex $o 1] - $ty)}]
    if {$d < $bd} { set bd $d; set best $r }
  }
  set o [$best getOrigin]; set sw [[$best getSite] getWidth]
  set x [expr {[lindex $o 0] + (($tx - [lindex $o 0]) / $sw) * $sw}]
  $i setOrient [$best getOrient]
  $i setLocation $x [lindex $o 1]
  $i setPlacementStatus FIRM
  lappend ot_rx_done $n
  puts "OT_RXEN_RELAY place $n at [expr {$x / double($ot_rx_dbu)}] [expr {[lindex $o 1] / double($ot_rx_dbu)}] FIRM"
}
if {[llength $ot_rx_done] != 2} { error "OT_RXEN_RELAY: expected rxen_m + rxen_w, found [llength $ot_rx_done]: $ot_rx_done" }
set fh [open $::env(RESULTS_DIR)/ot_rxen_relay_place.txt w]; puts $fh [join $ot_rx_done "\n"]; close $fh
