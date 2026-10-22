# Regional VM glue fences. Existing landing and relay stages retain their edges.
# Read actual pre-CTS clock nets; place each clocked group in its measured band.
set ot_r6_bands {{s 0 0 648 580.1} {core 0 580.1 648 976.0} {n 0 976.0 648 1555.2}}
set ot_r6_default core
set ot_r6_blk [ord::get_db_block]
set ot_r6_dbu [$ot_r6_blk getDbUnitsPerMicron]
set ot_r6_core [$ot_r6_blk getCoreArea]
set ot_r6_reg [dict create]
set ot_r6_un {}
set ot_r6_named 0
set vm_root_counts [dict create s 0 core 0 n 0]
foreach i [$ot_r6_blk getInsts] {
 set m [$i getMaster]
 if {[$m isBlock] || ![string match CORE* [$m getType]] || [$m getType] in {CORE_WELLTAP CORE_SPACER CORE_ANTENNACELL}} continue
 if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
 set region ""
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getSigType] ne "CLOCK"} continue
  set net [$it getNet]
  if {$net eq "NULL"} continue
  foreach bt [$net getBTerms] {
   switch -- [$bt getName] {clk_s {set region s} clk {set region core} clk_n {set region n}}
  }
 }
 if {$region ne ""} {
  dict set ot_r6_reg $i $region
  dict incr vm_root_counts $region
  incr ot_r6_named
 } else {lappend ot_r6_un $i}
}
dict for {root count} $vm_root_counts {
 if {$count == 0} {error "VM_REGIONAL_FENCE: no movable registers found on $root"}
}
puts "VM_REGIONAL_FENCE_CLOCKS $vm_root_counts"
set ot_r6_vote 0
for {set pass 0} {$pass < 60 && [llength $ot_r6_un]} {incr pass} {
  set next {}
  foreach i $ot_r6_un {
    set votes [dict create]
    foreach it [$i getITerms] {
      set net [$it getNet]
      if {$net eq "NULL" || [$net getSigType] in {POWER GROUND CLOCK}} continue
      set its [$net getITerms]
      if {[llength $its] > 48} continue
      foreach jt $its {
        set j [$jt getInst]
        if {[dict exists $ot_r6_reg $j]} { dict incr votes [dict get $ot_r6_reg $j] }
      }
    }
    if {[dict size $votes]} {
      set best ""; set bn -1
      dict for {b c} $votes { if {$c > $bn} { set best $b; set bn $c } }
      dict set ot_r6_reg $i $best; incr ot_r6_vote
    } else { lappend next $i }
  }
  if {[llength $next] == [llength $ot_r6_un]} break
  set ot_r6_un $next
}
set ot_r6_left [llength $ot_r6_un]
foreach i $ot_r6_un { dict set ot_r6_reg $i $ot_r6_default }
puts "VM_REGIONAL_FENCE_ASSIGN named=$ot_r6_named voted=$ot_r6_vote default=$ot_r6_left (band $ot_r6_default)"
set ot_r6_grp [dict create]
set ot_r6_box [dict create]
foreach b $ot_r6_bands {
  lassign $b name x0 y0 x1 y1
  # snap to the row / site grid of the core and clip to the core
  set cx0 [$ot_r6_core xMin]; set cy0 [$ot_r6_core yMin]; set cx1 [$ot_r6_core xMax]; set cy1 [$ot_r6_core yMax]
  set X0 [expr {max($cx0, round($x0 * $ot_r6_dbu))}]; set X1 [expr {min($cx1, round($x1 * $ot_r6_dbu))}]
  set Y0 [expr {max($cy0, round($y0 * $ot_r6_dbu))}]; set Y1 [expr {min($cy1, round($y1 * $ot_r6_dbu))}]
  set X0 [expr {$cx0 + 54 * (($X0 - $cx0) / 54)}]; set X1 [expr {$cx0 + 54 * (($X1 - $cx0) / 54)}]
  set Y0 [expr {$cy0 + 270 * (($Y0 - $cy0) / 270)}]; set Y1 [expr {$cy0 + 270 * (($Y1 - $cy0) / 270)}]
  if {$X1 > $cx1} { set X1 $cx1 }; if {$Y1 > $cy1} { set Y1 $cy1 }
  set r [odb::dbRegion_create $ot_r6_blk r6_$name]
  odb::dbBox_create $r $X0 $Y0 $X1 $Y1
  dict set ot_r6_grp $name [odb::dbGroup_create $r r6_$name]
  dict set ot_r6_box $name [list $X0 $Y0 $X1 $Y1]
}
set ot_r6_area [dict create]
set ot_r6_cnt [dict create]
dict for {i b} $ot_r6_reg {
  if {![dict exists $ot_r6_grp $b]} { error "VM_REGIONAL_FENCE: unknown band $b" }
  [dict get $ot_r6_grp $b] addInst $i
  set m [$i getMaster]
  dict set ot_r6_area $b [expr {([dict exists $ot_r6_area $b] ? [dict get $ot_r6_area $b] : 0.0) + double([$m getWidth]) * [$m getHeight]}]
  dict incr ot_r6_cnt $b
}
foreach b [dict keys $ot_r6_box] {
  lassign [dict get $ot_r6_box $b] X0 Y0 X1 Y1
  set free [expr {double($X1 - $X0) * ($Y1 - $Y0)}]
  foreach i [$ot_r6_blk getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]
    set ox [expr {min($X1, [$bb xMax]) - max($X0, [$bb xMin])}]; set oy [expr {min($Y1, [$bb yMax]) - max($Y0, [$bb yMin])}]
    if {$ox > 0 && $oy > 0} { set free [expr {$free - double($ox) * $oy}] }
  }
  set a [expr {[dict exists $ot_r6_area $b] ? [dict get $ot_r6_area $b] : 0.0}]
  set n [expr {[dict exists $ot_r6_cnt $b] ? [dict get $ot_r6_cnt $b] : 0}]
  puts [format "VM_REGIONAL_FENCE band=%s cells=%d cell_area_um2=%.0f free_um2=%.0f util=%.3f box=%s" $b $n \
      [expr {$a / $ot_r6_dbu / $ot_r6_dbu}] [expr {$free / $ot_r6_dbu / $ot_r6_dbu}] [expr {$free > 0 ? $a / $free : 99}] \
      [list [expr {$X0 / double($ot_r6_dbu)}] [expr {$Y0 / double($ot_r6_dbu)}] [expr {$X1 / double($ot_r6_dbu)}] [expr {$Y1 / double($ot_r6_dbu)}]]]
  if {$n == 0} { error "VM_REGIONAL_FENCE: band $b got no cells" }
  if {$free <= 0 || $a / $free > 0.85} { error "VM_REGIONAL_FENCE: band $b over-full ([expr {$free > 0 ? $a / $free : 99}])" }
}
