# Existing HEAD payload/control stages placed along legal macro corridors.
# Input targets come from head_tile_relay_plan.py's exact combinational-neighbour
# census. No RTL, pin, clock topology or stage count changes. Placement-only trial
# until the full post-legalization census and the independent geometry review pass.
if {![info exists ::env(HEAD_TILE_RELAY_TARGETS)]} {
  error "HEAD_TILE_RELAY_TARGETS must name the reviewed target table"
}
set htr_b [ord::get_db_block]
set htr_u [[ord::get_db_tech] getDbUnitsPerMicron]
set htr_rows [$htr_b getRows]
set htr_site [[[lindex $htr_rows 0] getSite] getWidth]
set htr_rh [[[lindex $htr_rows 0] getSite] getHeight]
set htr_targets [dict create]
set htr_file [open $::env(HEAD_TILE_RELAY_TARGETS) r]
while {[gets $htr_file ln]>=0} {
  if {$ln eq "" || [string index $ln 0] eq "#"} continue
  lassign [split $ln "\t"] name x y
  dict set htr_targets $name [list $x $y]
}
close $htr_file
set htr_occupied [dict create]
proc htr_occupy {x0 y0 x1 y1} {
  global htr_occupied htr_rh
  for {set ry [expr {int(floor($y0/double($htr_rh)))}]} {$ry<int(ceil($y1/double($htr_rh)))} {incr ry} {
    dict lappend htr_occupied $ry [list $x0 $x1]
  }
}
# Reserved die-clock/reset island rows are placement blockages even where the
# underlying dbRow is still present. A legal row/site alone is insufficient.
foreach blockage [$htr_b getBlockages] {
  # Partial density and soft blockages constrain movable placement, not the
  # exact FIRM relay sites. Keep every hard reserved island excluded.
  if {[$blockage isSoft] || [$blockage getMaxDensity] > 0} continue
  set b [$blockage getBBox]
  htr_occupy [$b xMin] [$b yMin] [$b xMax] [$b yMax]
}
foreach inst [$htr_b getInsts] {
  if {[dict exists $htr_targets [$inst getName]]} continue
  if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] in {FIRM LOCKED COVER}} {
    set b [$inst getBBox]
    htr_occupy [$b xMin] [$b yMin] [$b xMax] [$b yMax]
  }
}
set htr_done 0
dict for {name target} $htr_targets {
  set inst [$htr_b findInst $name]
  if {$inst eq "NULL"} {error "HEAD_TILE_RELAY missing exact cell $name"}
  set master [$inst getMaster]
  if {![string match DFF* [$master getName]]} {error "HEAD_TILE_RELAY non-flop $name"}
  lassign $target cx cy
  set iw [$master getWidth]; set ih [$master getHeight]
  set candidates {}
  foreach row $htr_rows {
    lassign [$row getOrigin] rx ry
    if {abs(($ry+$ih/2.0)/$htr_u-$cy)>6.0} continue
    set lo [expr {max($rx,int(($cx-6)*$htr_u-$iw/2))}]
    set hi [expr {min($rx+[$row getSiteCount]*$htr_site-$iw,int(($cx+6)*$htr_u-$iw/2))}]
    set xx [expr {$rx+int(ceil(($lo-$rx)/double($htr_site)))*$htr_site}]
    for {} {$xx<=$hi} {incr xx $htr_site} {
      set d [expr {abs(($xx+$iw/2.0)/$htr_u-$cx)+abs(($ry+$ih/2.0)/$htr_u-$cy)}]
      lappend candidates [list $d $xx $ry [$row getOrient]]
    }
  }
  set found 0
  foreach cand [lsort -real -index 0 $candidates] {
    lassign $cand d xx yy orient
    set free 1
    for {set ky [expr {int(floor($yy/double($htr_rh)))}]} {$ky<int(ceil(($yy+$ih)/double($htr_rh)))} {incr ky} {
      if {[dict exists $htr_occupied $ky]} {
        foreach box [dict get $htr_occupied $ky] {
          lassign $box x0 x1
          if {$xx<$x1 && $xx+$iw>$x0} {set free 0;break}
        }
      }
      if {!$free} break
    }
    if {!$free} continue
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    $inst setLocation $xx $yy
    $inst setPlacementStatus FIRM
    htr_occupy $xx $yy [expr {$xx+$iw}] [expr {$yy+$ih}]
    incr htr_done;set found 1;break
  }
  if {!$found} {error "HEAD_TILE_RELAY no legal site within6um of $target for $name"}
}
puts "HEAD_TILE_RELAY fixed=$htr_done expected=[dict size $htr_targets] added_cycles=0"
