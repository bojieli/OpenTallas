# HEAD native pass-through pipeline: the existing stages follow the W landing
# bank, the horizontal channel, and the E output bank. No RTL/cycle change.
set htb [ord::get_db_block]
set htu [[ord::get_db_tech] getDbUnitsPerMicron]
set htr [$htb getRows]
set hts [[[lindex $htr 0] getSite] getWidth]
set hth [[[lindex $htr 0] getSite] getHeight]
set htkeep [dict create]
proc htb_occupy {x0 y0 x1 y1} {
  global htkeep hth
  for {set yy [expr {int(floor($y0/double($hth)))}]} {$yy<int(ceil($y1/double($hth)))} {incr yy} {
    dict lappend htkeep $yy [list $x0 $x1]
  }
}
foreach htinst [$htb getInsts] {
  if {[[$htinst getMaster] isBlock] || [$htinst getPlacementStatus] in {FIRM LOCKED COVER}} {
    set b [$htinst getBBox]
    htb_occupy [$b xMin] [$b yMin] [$b xMax] [$b yMax]
  }
}
set htcount 0
foreach spec {{^u_core[.]x_q 354 717 24 16} {^u_core[.]xo_q 690 717 24 16}} {
  lassign $spec re cx cy halfx halfy
  set banks {}
  foreach inst [$htb getInsts] {
    set nm [string map {\\ {}} [$inst getName]]
    set hit [regexp $re $nm]
    # Yosys shares xo_q[511] with this pre-existing identical D/Q stage.
    if {$re eq {^u_core[.]xo_q} && $nm eq {u_core.u_b.u_x.genblk1.g_line.line[255]$_DFF_P_}} {set hit 1}
    if {$hit && [string match DFF* [[$inst getMaster] getName]]} {lappend banks $inst}
  }
  set candidates {}
  foreach row $htr {
    lassign [$row getOrigin] rx ry
    if {abs($ry/double($htu)-$cy)>$halfy} continue
    set lo [expr {max($rx,int(($cx-$halfx)*$htu))}]
    set hi [expr {min($rx+[$row getSiteCount]*$hts,int(($cx+$halfx)*$htu))}]
    set xx [expr {$rx+int(ceil(($lo-$rx)/double($hts)))*$hts}]
    for {} {$xx<$hi} {incr xx $hts} {
      set d [expr {abs($xx/double($htu)-$cx)+abs($ry/double($htu)-$cy)}]
      lappend candidates [list $d $xx $ry [$row getOrient]]
    }
  }
  set candidates [lsort -real -index 0 $candidates]
  set ni 0
  foreach inst [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $banks] {
    set master [$inst getMaster];set iw [$master getWidth];set ih [$master getHeight]
    set found 0
    foreach cand $candidates {
      lassign $cand d xx yy ori
      set free 1
      set rowkey [expr {int(floor($yy/double($hth)))}]
      if {[dict exists $htkeep $rowkey]} {
        foreach box [dict get $htkeep $rowkey] {
          lassign $box x0 x1
          if {$xx<$x1 && $xx+$iw>$x0} {set free 0;break}
        }
      }
      if {!$free} continue
      $inst setPlacementStatus PLACED
      $inst setOrient $ori
      $inst setLocation $xx $yy
      $inst setPlacementStatus FIRM
      htb_occupy $xx $yy [expr {$xx+$iw}] [expr {$yy+$ih}]
      incr ni;incr htcount;set found 1;break
    }
    if {!$found} {error "HEAD_TILE_BANK no legal site for [$inst getName] in $spec"}
  }
  if {$ni!=512} {error "HEAD_TILE_BANK expected512 got$ni for $re"}
  puts "HEAD_TILE_BANK re=$re fixed=$ni centre=$cx,$cy"
}
puts "HEAD_TILE_BANK total=$htcount existing_stages=1 added_cycles=0"
