# Full PWT545 collective SRAM capture placement, PRE_GLOBAL_PLACE after real macro placement.
# Reserve legal row sites beside the actual rd_out pins, at 55% local density.
# Fail closed if a capture D pin has a combinational predecessor or cannot fit
# within 100 um. This does not establish timing; routed SS/FF/TT still qualify.
set hc_block [ord::get_db_block]
set hc_dbu [$hc_block getDbUnitsPerMicron]
set hc_rows {}
foreach row [$hc_block getRows] {
  set o [$row getOrigin]; set site [$row getSite]
  lappend hc_rows [list [lindex $o 1] [lindex $o 0] [expr {[lindex $o 0]+[$row getSiteCount]*[$site getWidth]}] [$site getWidth] [$site getHeight] [$row getOrient]]
}
set hc_rows [lsort -integer -index 0 $hc_rows]
array set hc_occ {}
foreach inst [$hc_block getInsts] {
  if {![$inst isFixed] && ![[$inst getMaster] isBlock]} continue
  set b [$inst getBBox]
  for {set r 0} {$r<[llength $hc_rows]} {incr r} {
    set row [lindex $hc_rows $r]; set y [lindex $row 0]
    if {$y<[$b yMax] && $y+[lindex $row 4]>[$b yMin]} {lappend hc_occ($r) [list [$b xMin] [$b xMax]]}
  }
}
set hc_n 0; set hc_max 0; set hc_area 0; set hc_reserve_area 0
foreach mac [$hc_block getInsts] {
  if {![regexp {^ot_sram_1r1w_128x256_m1_r2c2$} [[$mac getMaster] getName]]} continue
  foreach pin [$mac getITerms] {
    if {![regexp {^rd_out\[} [[$pin getMTerm] getName]]} continue
    set net [$pin getNet]; if {$net eq "NULL"} continue
    set pb [$pin getBBox]; set px [expr {([$pb xMin]+[$pb xMax])/2}]; set py [expr {([$pb yMin]+[$pb yMax])/2}]
    foreach load [$net getITerms] {
      if {[$load isOutputSignal]} continue
      set inst [$load getInst]; set master [$inst getMaster]
      if {![$master isSequential] || [[$load getMTerm] getName] ne "D"} {
        error "HBM_CAPTURE_NONREGISTER [$mac getName]/[[$pin getMTerm] getName] -> [$inst getName]/[[$load getMTerm] getName]"
      }
      set width [$master getWidth]; set height [$master getHeight]
      set candidates {}
      for {set r 0} {$r<[llength $hc_rows]} {incr r} {
        set row [lindex $hc_rows $r]; set y [lindex $row 0]
        if {$height>[lindex $row 4] || abs($y-$py)>100*$hc_dbu} continue
        lappend candidates [list [expr {abs($y-$py)}] $r]
      }
      set placed 0
      foreach candidate [lsort -integer -index 0 $candidates] {
        set r [lindex $candidate 1]; set row [lindex $hc_rows $r]; lassign $row y x0 x1 sitew rowh orient
        set reserve [expr {int(ceil(double($width)/0.55/$sitew))*$sitew}]
        set center [expr {$x0+int(round(double($px-$x0)/$sitew))*$sitew}]
        for {set step 0} {$step<2*int(100*$hc_dbu/$sitew)+1} {incr step} {
          set delta [expr {($step%2) ? -(($step+1)/2) : $step/2}]
          set x [expr {$center+$delta*$sitew}]
          if {$x<$x0 || $x+$reserve>$x1} continue
          set distance [expr {abs($x+$width/2-$px)+abs($y+$height/2-$py)}]
          if {$distance>100*$hc_dbu} continue
          set free 1
          if {[info exists hc_occ($r)]} {
            foreach occupied $hc_occ($r) {if {$x<[lindex $occupied 1] && [lindex $occupied 0]<$x+$reserve} {set free 0; break}}
          }
          if {!$free} continue
          $inst setOrient $orient; $inst setLocation $x $y; $inst setPlacementStatus FIRM
          lappend hc_occ($r) [list $x [expr {$x+$reserve}]]
          set hc_area [expr {$hc_area+$width*$height}]; set hc_reserve_area [expr {$hc_reserve_area+$reserve*$height}];
          set hc_max [expr {max($hc_max,$distance)}]; incr hc_n; set placed 1; break
        }
        if {$placed} break
      }
      if {!$placed} {error "HBM_CAPTURE_NO_LEGAL_SITE [$inst getName] within 100um of [$mac getName]/[[$pin getMTerm] getName]"}
    }
  }
}
if {$hc_n==0} {error "HBM_CAPTURE_MISSING: no direct macro output capture registers found"}
puts "HBM_CAPTURE_PLACED count=$hc_n max_pin_to_cell_center_um=[expr {double($hc_max)/$hc_dbu}] local_density=0.55"

puts "HBM_CAPTURE_AREA cell_um2=[expr {double($hc_area)/$hc_dbu/$hc_dbu}] reservation_um2=[expr {double($hc_reserve_area)/$hc_dbu/$hc_dbu}]"
