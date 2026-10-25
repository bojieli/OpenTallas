# CP1 GEOM-REVIEW-3 06:34: run inside postcts_gate.tcl after loading ONE TT/FF
# corner and GRT RC. Hard stop before DRT; no physical/source changes.
if {![info exists ::env(OT_POSTCTS_GRT)] || !$::env(OT_POSTCTS_GRT)} { return }
proc cp1_source {net seen} {
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} { return {} }
  dict set seen [$net getName] 1
  foreach it [$net getITerms] {
    if {![$it isOutputSignal]} continue
    set i [$it getInst]; set m [[$i getMaster] getName]
    if {[string match *DFF* $m]} { return $i }
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} $m]} { return {} }
    foreach p [$i getITerms] {
      if {[$p isInputSignal]} { return [cp1_source [$p getNet] $seen] }
    }
  }
  return {}
}
proc cp1_quantile {sorted q} {
  if {![llength $sorted]} { error "CP1 no source distances" }
  return [lindex $sorted [expr {int(ceil($q*([llength $sorted]-1)))}]]
}
proc cp1_conditions {} {
  global c C ot_pg_mode
  if {$ot_pg_mode ne "global_routing"} { error "CP1 requires actual GRT RC" }
  set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set rpt /work/cp1_grt_${c}_slew.rpt
  report_check_types -max_slew -violators -max_count 100000 -digits 3 -no_line_splits > $rpt
  set fh [open $rpt]; set txt [read $fh]; close $fh
  set total_slew [sta::max_slew_violation_count]
  if {$total_slew > 0 && ![string match *slew* $txt]} { error "CP1 slew report missing heading" }
  set nbad 0
  foreach ln [split $txt \n] {
    if {[regexp {u_bout_[^[:space:]]*/D([[:space:]]|$)} $ln]} { incr nbad }
  }
  set dists {}; set missing {}; set n 0
  set of [open /work/cp1_grt_${c}_sources.tsv w]
  puts $of "sink\tsource\tdistance_um"
  foreach i [$blk getInsts] {
    if {![string match u_bout_* [$i getName]] || ![string match *DFF* [[$i getMaster] getName]]} continue
    set d [$i findITerm D]
    if {$d eq "NULL"} continue
    incr n
    set src [cp1_source [$d getNet] {}]
    if {$src eq ""} { lappend missing [$i getName]; continue }
    lassign [$i getLocation] x y; lassign [$src getLocation] sx sy
    set dist [expr {(abs($x-$sx)+abs($y-$sy))/double($dbu)}]
    lappend dists $dist
    puts $of "[$i getName]\t[$src getName]\t$dist"
  }
  close $of
  if {!$n || [llength $missing]} { error "CP1 source census missing: $n bout regs, [lrange $missing 0 9]" }
  set dists [lsort -real $dists]
  # Explicit density definition: physical cell area in 20x20um bins of the
  # top 100um face strip; fillers/decaps/taps excluded, bins clipped to core.
  set core [$blk getCoreArea]
  set x0 [expr {[$core xMin]/double($dbu)}]; set x1 [expr {[$core xMax]/double($dbu)}]
  set y1 [expr {[$core yMax]/double($dbu)}]; set y0 [expr {max([$core yMin]/double($dbu),$y1-100.)}]
  set bins {}; set pitch 20.
  foreach i [$blk getInsts] {
    set m [$i getMaster]; set mn [$m getName]
    if {[$m getType] ne "CORE" || [$m isFiller] || [regexp {^(TAP|DECAP|FILL)} $mn]} continue
    set b [$i getBBox]
    set ax [expr {max($x0,[$b xMin]/double($dbu))}]; set bx [expr {min($x1,[$b xMax]/double($dbu))}]
    set ay [expr {max($y0,[$b yMin]/double($dbu))}]; set by [expr {min($y1,[$b yMax]/double($dbu))}]
    if {$bx <= $ax || $by <= $ay} continue
    for {set ix [expr {int(floor(($ax-$x0)/$pitch))}]} {$x0+$ix*$pitch < $bx} {incr ix} {
      for {set iy [expr {int(floor(($ay-$y0)/$pitch))}]} {$y0+$iy*$pitch < $by} {incr iy} {
        set a [expr {(min($bx,$x0+($ix+1)*$pitch)-max($ax,$x0+$ix*$pitch))*(min($by,$y0+($iy+1)*$pitch)-max($ay,$y0+$iy*$pitch))}]
        set key $ix,$iy
        dict set bins $key [expr {([dict exists $bins $key] ? [dict get $bins $key] : 0)+$a}]
      }
    }
  }
  set density 0
  dict for {key a} $bins {
    lassign [split $key ,] ix iy
    set area [expr {(min($x1,$x0+($ix+1)*$pitch)-($x0+$ix*$pitch))*(min($y1,$y0+($iy+1)*$pitch)-($y0+$iy*$pitch))}]
    set density [expr {max($density,$a/$area)}]
  }
  set p50 [cp1_quantile $dists .5]; set p90 [cp1_quantile $dists .9]; set mx [lindex $dists end]
  set v [expr {!$nbad && $density <= .8 ? "PASS" : "FAIL"}]
  set f [open /work/cp1_grt_${c}_conditions.json w]
  puts $f [format {{"corner":"%s","bout_n":%d,"bout_D_slew_viol":%d,"source_um_p50":%.3f,"source_um_p90":%.3f,"source_um_max":%.3f,"top100um_20um_bin_max_density":%.6f,"verdict":"%s"}} $C $n $nbad $p50 $p90 $mx $density $v]
  close $f
  puts "OT_POSTCTS_GATE CP1 $C bout_D_slew $nbad source_um $p50/$p90/$mx top_density $density $v"
}
if {[catch {cp1_conditions} why]} { puts "OT_POSTCTS_GATE CP1 $C NOT_RUN $why FAIL"; error $why }
