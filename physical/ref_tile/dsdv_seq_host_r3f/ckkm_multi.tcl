# STW-S81c-COLLA 10-22 seq r3e/r3f: per-root 2-D k-means leaf clusters (physical/common_flow/clock_split_km.tcl logic,
# one call per clock port, hard-child clock pins excluded so clock_entries/child_centre_tap keep the child entries).
# r3c/r3d measured boundary pin-flop spread 101-165 ps on each root (pin flops strung along the 1,425-um faces).
# Knob: ::ot_ckkm_ports = {port K ...}.  Same ports, flops, cycles.
proc ot_ckkm_port {port K iters} {
  set ot_ckkm_blk [ord::get_db_block]
  if {[$ot_ckkm_blk findInst ot_ckkm_${port}_0] ne "NULL"} return
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set bt [$ot_ckkm_blk findBTerm $port]
  if {$bt eq "NULL"} { error "CLOCK_SPLIT_KM: no $port port" }
  set pnet [$bt getNet]
  set xs {}; set ys {}; set its {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    if {[[[$it getInst] getMaster] isBlock]} continue  ;# hard-child clock pins stay on the entry (child_centre_tap)
    set l [[$it getInst] getLocation]
    lappend xs [expr {[lindex $l 0] / double($u)}]; lappend ys [expr {[lindex $l 1] / double($u)}]; lappend its $it
  }
  set N [llength $its]
  if {$N < 2 * $K} { error "CLOCK_SPLIT_KM: only $N sinks for $K clusters" }
  set mx 0.0; set my 0.0
  foreach x $xs y $ys { set mx [expr {$mx + $x}]; set my [expr {$my + $y}] }
  set mx [expr {$mx / $N}]; set my [expr {$my / $N}]
  # seeds: equal-count groups in angle order around the sink centroid
  set ang {}
  for {set i 0} {$i < $N} {incr i} { lappend ang [list [expr {atan2([lindex $ys $i] - $my, [lindex $xs $i] - $mx)}] $i] }
  set ang [lsort -real -index 0 $ang]
  set cx {}; set cy {}
  for {set k 0} {$k < $K} {incr k} {
    set lo [expr {($N * $k) / $K}]; set hi [expr {($N * ($k + 1)) / $K - 1}]
    set sx 0.0; set sy 0.0
    foreach e [lrange $ang $lo $hi] { set i [lindex $e 1]; set sx [expr {$sx + [lindex $xs $i]}]; set sy [expr {$sy + [lindex $ys $i]}] }
    set n [expr {$hi - $lo + 1}]
    lappend cx [expr {$sx / $n}]; lappend cy [expr {$sy / $n}]
  }
  set asg [lrepeat $N 0]
  for {set r 0} {$r < $iters} {incr r} {
    set moved 0
    for {set i 0} {$i < $N} {incr i} {
      set x [lindex $xs $i]; set y [lindex $ys $i]; set best 0; set bd 1e30
      for {set k 0} {$k < $K} {incr k} {
        set d [expr {abs($x - [lindex $cx $k]) + abs($y - [lindex $cy $k])}]
        if {$d < $bd} { set bd $d; set best $k }
      }
      if {[lindex $asg $i] != $best} { lset asg $i $best; incr moved }
    }
    set sx [lrepeat $K 0.0]; set sy [lrepeat $K 0.0]; set sn [lrepeat $K 0]
    for {set i 0} {$i < $N} {incr i} {
      set k [lindex $asg $i]
      lset sx $k [expr {[lindex $sx $k] + [lindex $xs $i]}]; lset sy $k [expr {[lindex $sy $k] + [lindex $ys $i]}]
      lset sn $k [expr {[lindex $sn $k] + 1}]
    }
    for {set k 0} {$k < $K} {incr k} {
      if {[lindex $sn $k] > 0} { lset cx $k [expr {[lindex $sx $k] / [lindex $sn $k]}]; lset cy $k [expr {[lindex $sy $k] / [lindex $sn $k]}] }
    }
    if {$r > 0 && $moved == 0} break
  }
  set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set nets {}
  for {set k 0} {$k < $K} {incr k} {
    if {[lindex $sn $k] == 0} { lappend nets "" ; continue }
    set b [odb::dbInst_create $ot_ckkm_blk $m ot_ckkm_${port}_$k]
    $b setLocation [expr {int([lindex $cx $k] * $u)}] [expr {int([lindex $cy $k] * $u)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $ot_ckkm_blk ot_ckkm_${port}_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $pnet; [$b findITerm Y] connect $net
    lappend nets $net
  }
  for {set i 0} {$i < $N} {incr i} {
    set it [lindex $its $i]; $it disconnect; $it connect [lindex $nets [lindex $asg $i]]
  }
  array unset ot_ckkm_bx; array unset ot_ckkm_by
  for {set i 0} {$i < $N} {incr i} {
    set k [lindex $asg $i]; lappend ot_ckkm_bx($k) [lindex $xs $i]; lappend ot_ckkm_by($k) [lindex $ys $i]
  }
  for {set k 0} {$k < $K} {incr k} {
    if {[lindex $sn $k] == 0} continue
    set xl [lsort -real $ot_ckkm_bx($k)]; set yl [lsort -real $ot_ckkm_by($k)]
    puts [format "CLOCK_SPLIT_KM: $port cluster %d %d sinks x %.1f..%.1f y %.1f..%.1f buffer at (%.1f, %.1f)" $k [lindex $sn $k] \
      [lindex $xl 0] [lindex $xl end] [lindex $yl 0] [lindex $yl end] [lindex $cx $k] [lindex $cy $k]]
  }
}

foreach {p k} $::ot_ckkm_ports { ot_ckkm_port $p $k 25 }
detailed_placement
