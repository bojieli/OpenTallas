# Joint legal placement for planned reset control flops and their kept drivers.
# API: ot_reset_pair_place BLOCK SPECS BOXES_UM MAX_OFFSET_UM
# SPECS is {{flop_glob driver_glob x_um y_um} ...}; empty driver_glob = plain
# entry/output flop. Ordinary PLACED logic is movable and is not an obstacle.
# The complete allocation is checked before any database mutation.
namespace eval ::ot_rpp {}
proc ::ot_rpp::hit {a b} {
  lassign $a x0 y0 x1 y1; lassign $b a0 b0 a1 b1
  return [expr {$x0 < $a1 && $x1 > $a0 && $y0 < $b1 && $y1 > $b0}]
}
proc ::ot_rpp::unique {block pattern kind pool} {
  set found {}
  set exact [$block findInst $pattern]
  if {$exact ne "NULL" && $exact ne ""} { set candidates [list $exact] } else { set candidates $pool }
  foreach i $candidates {
    if {![string match $pattern [$i getName]]} continue
    set master [[$i getMaster] getName]
    if {$kind eq "flop" && ![string match "*DFF*" $master]} continue
    if {$kind eq "driver" && ![string match "BUF*" $master]} continue
    lappend found $i
  }
  if {[llength $found] != 1} { error "OT_RESET_PAIR expected one $kind for '$pattern', found [llength $found]" }
  return [lindex $found 0]
}
proc ot_reset_pair_place {block specs boxes max_offset_um} {
  if {![string is double -strict $max_offset_um] || $max_offset_um <= 0} {
    error "OT_RESET_PAIR max_offset_um must be positive"
  }
  set dbu [$block getDbUnitsPerMicron]
  set limit [expr {$max_offset_um*$dbu}]
  set core [$block getCoreArea]
  set corebox [list [$core xMin] [$core yMin] [$core xMax] [$core yMax]]
  set pool {}; foreach i [$block getInsts] {
    set m [[$i getMaster] getName]
    if {[string match "*DFF*" $m] || [string match "BUF*" $m]} { lappend pool $i }
  }
  set selected [dict create]; set work {}
  foreach spec $specs {
    if {[llength $spec] != 4} { error "OT_RESET_PAIR malformed spec '$spec'" }
    lassign $spec fp dp x y
    if {![string is double -strict $x] || ![string is double -strict $y]} { error "OT_RESET_PAIR invalid anchor '$spec'" }
    set f [::ot_rpp::unique $block $fp flop $pool]
    set d ""; if {$dp ne ""} { set d [::ot_rpp::unique $block $dp driver $pool] }
    foreach i [expr {$d eq "" ? [list $f] : [list $f $d]}] {
      set nm [$i getName]
      if {[dict exists $selected $nm]} { error "OT_RESET_PAIR cell '$nm' appears in more than one pair" }
      dict set selected $nm 1
    }
    lappend work [list $f $d [expr {$x*$dbu}] [expr {$y*$dbu}]]
  }
  # Macro halos come from BOXES_UM; hard blockages/macros/fixed cells in the
  # actual database are also hard obstacles. Exclude only the cells being paired.
  set occupied {}
  foreach b $boxes {
    if {[llength $b] != 4} { error "OT_RESET_PAIR malformed blockage '$b'" }
    lappend occupied [lmap x $b {expr {round($x*$dbu)}}]
  }
  foreach b [$block getBlockages] {
    set bb [$b getBBox]
    lappend occupied [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
  }
  foreach i [$block getInsts] {
    if {[dict exists $selected [$i getName]]} continue
    if {![[$i getMaster] isBlock] && [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set b [$i getBBox]
    lappend occupied [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  set rows {}
  foreach r [$block getRows] {
    lassign [$r getOrigin] x y
    set site [$r getSite]; set pitch [$r getSpacing]
    if {$pitch <= 0} { set pitch [$site getWidth] }
    set orient [$r getOrient]
    if {$orient ni {R0 MX MY R180}} continue
    lappend rows [list $x $y $pitch [$r getSiteCount] [$site getHeight] $orient]
  }
  if {![llength $rows]} { error "OT_RESET_PAIR no supported horizontal standard-cell rows" }
  set allocations {}; set locs [dict create]; set orientations [dict create]
  foreach item $work {
    lassign $item f d ax ay
    set fm [$f getMaster]; set fw [$fm getWidth]; set fh [$fm getHeight]
    set dw 0; set dh 0
    if {$d ne ""} { set dm [$d getMaster]; set dw [$dm getWidth]; set dh [$dm getHeight] }
    set best {}; set bestscore 1e100
    foreach row $rows {
      lassign $row rx ry pitch count rh ro
      if {abs($ry-$ay) > $limit || $fh > $rh || $dh > $rh} continue
      set fsites [expr {int(ceil(double($fw)/$pitch))}]
      set dsites [expr {int(ceil(double($dw)/$pitch))}]
      set width [expr {($fsites+$dsites)*$pitch}]
      set low [expr {max(0,int(ceil(($ax-$limit-$rx)/$pitch)))}]
      set high [expr {min($count-$fsites-$dsites,int(floor(($ax+$limit-$rx)/$pitch)))}]
      for {set j $low} {$j <= $high} {incr j} {
        set px [expr {$rx+$j*$pitch}]
        foreach order [expr {$d eq "" ? {right} : {right left}}] {
          set fx $px; set dx [expr {$px+$fsites*$pitch}]
          if {$order eq "left"} { set dx $px; set fx [expr {$px+$dsites*$pitch}] }
          set fd [expr {abs($fx-$ax)+abs($ry-$ay)}]
          set dd [expr {$d eq "" ? 0 : abs($dx-$ax)+abs($ry-$ay)}]
          if {$fd > $limit || $dd > $limit} continue
          set bounds [list $px $ry [expr {$px+$width}] [expr {$ry+max($fh,$dh)}]]
          lassign $bounds x0 y0 x1 y1; lassign $corebox cx0 cy0 cx1 cy1
          if {$x0 < $cx0 || $y0 < $cy0 || $x1 > $cx1 || $y1 > $cy1} continue
          set score [expr {max($fd,$dd)+0.01*($fd+$dd)}]
          if {$score >= $bestscore} continue
          set legal 1
          foreach b $occupied { if {[::ot_rpp::hit $bounds $b]} { set legal 0; break } }
          if {!$legal} continue
          set best [list $fx $dx $ry $ro $bounds]
          set bestscore $score
        }
      }
    }
    if {![llength $best]} { error "OT_RESET_PAIR no joint legal site within ${max_offset_um}um of [$f getName]" }
    lassign $best fx dx y orient bounds
    lappend occupied $bounds
    lappend allocations [list $f $fx $y $orient 0]
    dict set locs [$f getName] [list $fx $y]; dict set orientations [$f getName] $orient
    if {$d ne ""} {
      lappend allocations [list $d $dx $y $orient 1]
      dict set locs [$d getName] [list $dx $y]; dict set orientations [$d getName] $orient
    }
  }
  if {[info exists ::ot_reset_pair_plan_only] && $::ot_reset_pair_plan_only} {
    set ::ot_reset_pair_locs $locs
    set ::ot_reset_pair_orients $orientations
    puts "OT_RESET_PAIR PLAN_ONLY [llength $work] pairs/plain-controls, [dict size $locs] cells, no database mutation"
    return $locs
  }
  foreach a $allocations {
    lassign $a i x y orient driver
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} { $i setPlacementStatus PLACED }
    $i setOrient $orient; $i setLocation $x $y; $i setPlacementStatus FIRM
    # Both cell masters belong to the checked joint footprint. Resizing either
    # one after allocation would invalidate its free-space certificate.
    $i setDoNotTouch true
    set b [$i getBBox]
    if {[$b xMin] != $x || [$b yMin] != $y} { error "OT_RESET_PAIR actual lower-left mismatch for [$i getName]" }
  }
  set ::ot_reset_pair_locs $locs
  set ::ot_reset_pair_orients $orientations
  puts "OT_RESET_PAIR PASS [llength $work] pairs/plain-controls, [dict size $locs] cells FIRM, max anchor offset ${max_offset_um}um"
  return $locs
}
proc ot_reset_pair_check {block} {
  if {![info exists ::ot_reset_pair_locs]} { error "OT_RESET_PAIR no allocation to check" }
  dict for {name xy} $::ot_reset_pair_locs {
    set i [$block findInst $name]
    if {$i eq "NULL" || [$i getPlacementStatus] ne "FIRM"} { error "OT_RESET_PAIR control lost FIRM after DPL: $name" }
    set b [$i getBBox]
    if {[list [$b xMin] [$b yMin]] ne $xy || [$i getOrient] ne [dict get $::ot_reset_pair_orients $name]} {
      error "OT_RESET_PAIR control moved during DPL: $name"
    }
  }
  puts "OT_RESET_PAIR CHECK PASS [dict size $::ot_reset_pair_locs] actual controls unchanged after DPL"
}
# Follow repair buffers and the AND of a gated reset/START tap. An inserted
# combinational cell is not a registered station and must not hide a long hop.
proc ::ot_rpp::launches {net locs seen {depth 0}} {
  if {$depth > 40} { error "OT_RESET_PAIR combinational control cone exceeds 40 levels" }
  if {$net eq "NULL" || $net eq ""} { return {} }
  set key [$net getName]
  if {[dict exists $seen $key]} { error "OT_RESET_PAIR combinational reset loop at $key" }
  dict set seen $key 1
  set sources {}
  foreach p [$net getITerms] { if {[$p isOutputSignal]} { lappend sources $p } }
  if {![llength $sources]} { return {} } ;# external input or constant
  if {[llength $sources] != 1} { error "OT_RESET_PAIR multi-driver reset net $key" }
  set src [lindex $sources 0]; set i [$src getInst]; set m [$i getMaster]
  if {[string match "*DFF*" [$m getName]] ||
      ([dict exists $locs [$i getName]] && [string match "BUF*" [$m getName]])} { return [list $src] }
  if {[$m isBlock]} { return {} } ;# hard-core interface is checked by its own contract
  set out {}
  foreach p [$i getITerms] {
    if {![$p isInputSignal] || [$p getSigType] in {POWER GROUND CLOCK}} continue
    set n [$p getNet]
    if {$n eq "NULL" || $n eq "" || [$n getSigType] eq "CLOCK"} continue
    lappend out {*}[::ot_rpp::launches $n $locs $seen [expr {$depth+1}]]
  }
  return [lsort -unique $out]
}
proc ot_reset_pair_verify_hops {block reach_um} {
  if {[info exists ::ot_reset_pair_locs]} {
    set locs $::ot_reset_pair_locs
  } else {
    # A fresh post-route session has no allocator globals. Discover the actual
    # generated control hierarchy, never unrelated functional datapath flops.
    set locs [dict create]
    foreach i [$block getInsts] {
      set name [$i getName]
      if {![regexp {(^|[./])(u_[rs]rl_[0-9]+(_[rg])?|u_(rst|run)_(in|root))([./]|$)|^pr_(reset|run)_(entry_[0-9]+|u_[rs]rl_[0-9]+(_[rg])?)(_drive)?$} $name]} continue
      set master [[$i getMaster] getName]
      if {![string match "*DFF*" $master] && ![string match "BUF*" $master]} continue
      dict set locs $name 1
    }
    if {![dict size $locs]} { error "OT_RESET_PAIR no generated controls found for hop verification" }
  }
  set dbu [$block getDbUnitsPerMicron]; set maxhop 0; set n 0; set bad {}
  dict for {name xy} $locs {
    set i [$block findInst $name]
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    foreach sink [$i getITerms] {
      if {[[$sink getMTerm] getName] ne "D"} continue
      set net [$sink getNet]; if {$net eq "NULL" || $net eq ""} continue
      foreach src [::ot_rpp::launches $net $locs {}] {
        set a [$src getBBox]; set b [$sink getBBox]
        set d [expr {(abs(([$a xMin]+[$a xMax]-[$b xMin]-[$b xMax])/2.0)+abs(([$a yMin]+[$a yMax]-[$b yMin]-[$b yMax])/2.0))/$dbu}]
        set maxhop [expr {max($maxhop,$d)}]; incr n
        if {$d > $reach_um+1e-6} { lappend bad [list [[$src getInst] getName] $name $d] }
      }
    }
  }
  puts "OT_RESET_PAIR HOPS n $n max $maxhop um over_reach [llength $bad]"
  if {[llength $bad]} { error "OT_RESET_PAIR registered hop exceeds ${reach_um}um: [lrange $bad 0 4]" }
  return [dict create count $n max_um $maxhop over_reach 0]
}
