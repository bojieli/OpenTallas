# Place existing input buffers on legal sites beside their driving ports. No
# RTL, load, transition or timing changes; retain real row orientation/PG rails.
# Global placement put several first buffers >100um from their pin, leaving
# primary-input nets at285ps slew against unchanged260ps even with TT/FF closed.
set hc_block [ord::get_db_block]
set hc_dbu [$hc_block getDbUnitsPerMicron]
set hc_rows [$hc_block getRows]
set hc_busy [dict create]
# Preserve taps, endcaps, macros and other existing fixed objects. Row bounds
# alone include the edge tap sites; they are not free placement locations.
foreach hc_fixed [$hc_block getInsts] {
 if {[$hc_fixed getPlacementStatus] ni {FIRM LOCKED}} {continue}
 set hc_fbb [$hc_fixed getBBox]
 foreach hc_row $hc_rows {
  set hc_rbb [$hc_row getBBox]
  if {[$hc_fbb yMin]<[$hc_rbb yMax] && [$hc_fbb yMax]>[$hc_rbb yMin]} {
   dict lappend hc_busy [$hc_row getName] [list [$hc_fbb xMin] [$hc_fbb xMax]]
  }
 }
}
set hc_moved 0
foreach hc_inst [$hc_block getInsts] {
 if {![string match input* [$hc_inst getName]]} {continue}
 set hc_term [$hc_inst findITerm A]
 if {$hc_term eq "NULL"} {continue}
 set hc_net [$hc_term getNet]
 if {$hc_net eq "NULL" || [llength [$hc_net getBTerms]]!=1} {continue}
 set hc_port [lindex [$hc_net getBTerms] 0]
 if {[$hc_port getIoType] ne "INPUT" || [$hc_port getName] eq "clk"} {continue}
 set hc_shapes {}
 foreach hc_bpin [$hc_port getBPins] {foreach hc_box [$hc_bpin getBoxes] {lappend hc_shapes $hc_box}}
 if {![llength $hc_shapes]} {error "HC input port missing physical shape: [$hc_port getName]"}
 set hc_shape [lindex $hc_shapes 0]
 set hc_px [expr {([$hc_shape xMin]+[$hc_shape xMax])/2}]
 set hc_py [expr {([$hc_shape yMin]+[$hc_shape yMax])/2}]
 set hc_master [$hc_inst getMaster]
 set hc_w [$hc_master getWidth]
 set hc_best {};set hc_best_dist 1e30
 foreach hc_row $hc_rows {
  set hc_bb [$hc_row getBBox];set hc_site [$hc_row getSite]
  if {[$hc_site getHeight] != [$hc_master getHeight]} {continue}
  set hc_pitch [$hc_site getWidth]
  set hc_yy [$hc_bb yMin];set hc_left [$hc_bb xMin];set hc_right [expr {[$hc_bb xMax]-$hc_w}]
  set hc_start [expr {max($hc_left,min($hc_right,$hc_px-$hc_w/2))}]
  set hc_start [expr {$hc_left+int(round(double($hc_start-$hc_left)/$hc_pitch))*$hc_pitch}]
  set hc_occupied {};if {[dict exists $hc_busy [$hc_row getName]]} {set hc_occupied [dict get $hc_busy [$hc_row getName]]}
  # Search a few legal neighbouring slots, retaining same-row rail orientation.
  for {set hc_off 0} {$hc_off<24} {incr hc_off} {
   foreach hc_sign {1 -1} {
    set hc_x [expr {$hc_start+$hc_sign*$hc_off*$hc_pitch}]
    if {$hc_x<$hc_left || $hc_x>$hc_right} {continue}
    set hc_hit 0
    foreach hc_interval $hc_occupied {
     if {$hc_x<[lindex $hc_interval 1] && $hc_x+$hc_w>[lindex $hc_interval 0]} {set hc_hit 1;break}
    }
    if {$hc_hit} {continue}
    set hc_dist [expr {abs($hc_x+$hc_w/2-$hc_px)+abs($hc_yy+[$hc_master getHeight]/2-$hc_py)}]
    if {$hc_dist<$hc_best_dist} {set hc_best_dist $hc_dist;set hc_best [list $hc_row $hc_x $hc_yy]}
   }
  }
 }
 if {![llength $hc_best]} {error "HC no legal row slot for [$hc_inst getName]"}
 set hc_row [lindex $hc_best 0];set hc_x [lindex $hc_best 1];set hc_y [lindex $hc_best 2]
 $hc_inst setOrient [$hc_row getOrient]
 $hc_inst setLocation $hc_x $hc_y
 $hc_inst setPlacementStatus FIRM
 dict lappend hc_busy [$hc_row getName] [list $hc_x [expr {$hc_x+$hc_w}]]
 incr hc_moved
}
puts "HGI_INPUT_ANCHOR moved=$hc_moved existing buffers, matching actual row rails; timing/electrical limits unchanged"
# Other cells may move around the now-fixed input buffers; no macro placement.
detailed_placement
check_placement -verbose
