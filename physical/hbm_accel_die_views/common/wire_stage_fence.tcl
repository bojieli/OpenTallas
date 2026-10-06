# POST_FLOORPLAN hook (CLAUDE HBM-ABSTRACTS svcidx): spread the wire stages of every ot_svc_vpipe chain evenly along
# the line between the terminals that feed the chain and the terminals it drives.
# Why: a view outline is the r16g die slot (svc 8.5 mm x 0.26 mm, index quarter 0.93 x 5.53 mm) and its long paths
# carry N wire-stage registers sized at <= 430 um a stage.  Global placement does not spread a register chain between
# two far terminals: it clumps the chain (index_q idx_p55: u_kp stages 1..13 within y 1936..2924 while t_vm sits at
# y 5430, routed WNS -5.2 ns).  This hook puts stage k of an N-stage chain in an INCLUSIVE region centred at
# A + (k+1)/(N+1) * (B - A), A / B = centroids of the nearest terminals reached backwards from stage 0 / forwards
# from stage N-1 (breadth-first over cells, sequential cells included, nets with more than OT_WS_FANOUT loads
# skipped), so every hop carries 1/(N+1) of the distance.  Region area = stage cell area / OT_WS_DENSITY (0.12),
# square, clipped to the core; a box that would overlap an earlier one moves along the chain direction.
# Membership: flops named <chain>.gn.r[k][*] and <chain>.gn.rv[k] (synthesis keeps register names).
# Terminal positions come from the IO constraint file (ORFS erases IO_CONSTRAINTS in the floorplan stage, so the
# route passes the same file as OT_IO_FILE).
global ws_pin ws_chain ws_fan ws_tok ws_n ws_seeds
set ws_seeds [expr {[info exists ::env(OT_WS_SEEDS)] ? $::env(OT_WS_SEEDS) : 8}]
set ws_dens [expr {[info exists ::env(OT_WS_DENSITY)] ? $::env(OT_WS_DENSITY) : 0.12}]
set ws_depth [expr {[info exists ::env(OT_WS_DEPTH)] ? $::env(OT_WS_DEPTH) : 24}]
set ws_fan [expr {[info exists ::env(OT_WS_FANOUT)] ? $::env(OT_WS_FANOUT) : 64}]
set ws_blk [ord::get_db_block]
set ws_dbu [$ws_blk getDbUnitsPerMicron]
set ws_core [$ws_blk getCoreArea]
set cx0 [$ws_core xMin]; set cy0 [$ws_core yMin]; set cx1 [$ws_core xMax]; set cy1 [$ws_core yMax]
array set ws_pin {}
set ws_iof [expr {[info exists ::env(OT_IO_FILE)] ? $::env(OT_IO_FILE) : ""}]
if {$ws_iof eq "" || ![file exists $ws_iof]} { error "OT_WS fence: no IO file (OT_IO_FILE '$ws_iof')" }
set fh [open $ws_iof]; set txt [read $fh]; close $fh
foreach {m nm x y} [regexp -all -inline {place_pin -pin_name \{([^\}]+)\} -layer \S+ -location \{(\S+) (\S+)\}} $txt] {
  set ws_pin($nm) [list [expr {round($x*$ws_dbu)}] [expr {round($y*$ws_dbu)}]]
}
if {![array size ws_pin]} { error "OT_WS fence: no terminal positions in $ws_iof" }
# chain stages
array set ws_st {}; array set ws_n {}; array set ws_chain {}
foreach i [$ws_blk getInsts] {
  set n [string map {"\\" ""} [$i getName]]
  if {[regexp {^(.+)\.gn\.rv?\[([0-9]+)\]} $n -> c k]} {
    lappend ws_st($c,$k) $i
    set ws_chain([$i getName]) $c
    if {![info exists ws_n($c)] || $k + 1 > $ws_n($c)} { set ws_n($c) [expr {$k + 1}] }
  }
}
proc ws_skip {n} {
  global ws_fan
  return [expr {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK RESET} || [llength [$n getITerms]] > $ws_fan + 1}]
}
# breadth-first search from a set of instances: dir "back" follows input pins to drivers, "fwd" output pins to loads;
# returns the terminal positions found at the first level that reaches any terminal
proc ws_bfs {all dir depth} {
  global ws_pin ws_chain ws_seeds
  # a sample of the stage's bits (evenly spaced) is enough for the terminal centroid and keeps the search cheap
  set seeds {}; set m [llength $all]; set st [expr {max(1, $m / $ws_seeds)}]
  for {set q 0} {$q < $m} {incr q $st} { lappend seeds [lindex $all $q] }
  array set seen {}
  foreach i $seeds { set seen([$i getName]) 1 }
  set front $seeds
  for {set d 0} {$d < $depth && [llength $front]} {incr d} {
    set pins {}; set next {}
    foreach i $front {
      foreach it [$i getITerms] {
        if {$dir eq "back"} { if {[$it isOutputSignal]} continue } else { if {![$it isOutputSignal]} continue }
        set n [$it getNet]; if {[ws_skip $n]} continue
        foreach bt [$n getBTerms] { if {[info exists ws_pin([$bt getName])]} { lappend pins $ws_pin([$bt getName]) } }
        foreach o [$n getITerms] {
          if {$dir eq "back"} { if {![$o isOutputSignal]} continue } else { if {[$o isOutputSignal]} continue }
          set oi [$o getInst]; set on [$oi getName]
          if {[info exists seen($on)]} continue
          set seen($on) 1
          if {[info exists ws_chain($on)]} continue
          lappend next $oi
        }
      }
    }
    if {[llength $pins]} { return $pins }
    set front $next
  }
  return {}
}
proc ws_cent {l} {
  set sx 0.0; set sy 0.0
  foreach p $l { set sx [expr {$sx+[lindex $p 0]}]; set sy [expr {$sy+[lindex $p 1]}] }
  return [list [expr {$sx/[llength $l]}] [expr {$sy/[llength $l]}]]
}
set boxes {}
proc ws_ovl {b boxes} {
  foreach o $boxes {
    if {[lindex $b 0] < [lindex $o 2] && [lindex $o 0] < [lindex $b 2] && [lindex $b 1] < [lindex $o 3] && [lindex $o 1] < [lindex $b 3]} { return 1 }
  }
  return 0
}
set nreg 0
# 1-bit return-token chains (u_dn / u_wdn / u_tb / u_eb) run against a data chain of the same depth in the same scope:
# token stage k shares the region of data stage N-1-k
array set ws_tok {u_dn {u_bp u_p} u_wdn u_wp u_tb u_rq u_eb u_ep}
array set ws_box {}
proc ws_partner {c} {
  global ws_tok ws_n
  set leaf [lindex [split $c .] end]; set sc [join [lrange [split $c .] 0 end-1] .]
  if {![info exists ws_tok($leaf)]} { return "" }
  foreach pl $ws_tok($leaf) {
    set pc [expr {$sc eq "" ? $pl : "$sc.$pl"}]
    if {[info exists ws_n($pc)] && $ws_n($pc) == $ws_n($c)} { return $pc }
  }
  return "-"
}
foreach c [lsort -dictionary [array names ws_n]] {
  set N $ws_n($c)
  if {[ws_partner $c] ne ""} continue
  if {![info exists ws_st($c,0)] || ![info exists ws_st($c,[expr {$N-1}])]} continue
  set A [ws_bfs $ws_st($c,0) back $ws_depth]
  set B [ws_bfs $ws_st($c,[expr {$N-1}]) fwd $ws_depth]
  if {![llength $A] || ![llength $B]} {
    puts "OT_WS: chain $c N=$N: no terminal on one side ([llength $A] in / [llength $B] out), left unfenced"
    continue
  }
  set a [ws_cent $A]; set b [ws_cent $B]
  set dx [expr {[lindex $b 0]-[lindex $a 0]}]; set dy [expr {[lindex $b 1]-[lindex $a 1]}]
  set len [expr {hypot($dx,$dy)}]
  set ux [expr {$len > 0 ? $dx/$len : 1.0}]; set uy [expr {$len > 0 ? $dy/$len : 0.0}]
  puts [format "OT_WS: chain %s N=%d from (%.1f %.1f) to (%.1f %.1f) um, %.1f um Manhattan, %.1f um a hop" $c $N \
        [expr {[lindex $a 0]/$ws_dbu}] [expr {[lindex $a 1]/$ws_dbu}] [expr {[lindex $b 0]/$ws_dbu}] \
        [expr {[lindex $b 1]/$ws_dbu}] [expr {(abs($dx)+abs($dy))/$ws_dbu}] [expr {(abs($dx)+abs($dy))/$ws_dbu/($N+1)}]]
  if {[info exists ::env(OT_WS_REPORT)]} {
    # report mode (no regions): the placed hop lengths (stage centroids) of a placed database
    set prev $a; set worst 0.0; set hops {}
    for {set k 0} {$k <= $N} {incr k} {
      if {$k < $N} {
        if {![info exists ws_st($c,$k)]} continue
        set pts {}; foreach i $ws_st($c,$k) { lappend pts [$i getLocation] }
        set p [ws_cent $pts]
      } else { set p $b }
      set h [expr {(abs([lindex $p 0]-[lindex $prev 0])+abs([lindex $p 1]-[lindex $prev 1]))/$ws_dbu}]
      lappend hops [format %.0f $h]; set worst [expr {max($worst,$h)}]; set prev $p
    }
    puts [format "OT_WS_REPORT: %s worst hop %.0f um: %s" $c $worst [join $hops " "]]
    continue
  }
  for {set k 0} {$k < $N} {incr k} {
    if {![info exists ws_st($c,$k)]} continue
    set area 0.0
    foreach i $ws_st($c,$k) { set area [expr {$area + double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]}] }
    set s [expr {sqrt($area / $ws_dens)}]
    set rw [expr {min($s, $cx1-$cx0)}]; set rh [expr {min($cy1-$cy0, max($s, $area / $ws_dens / $rw))}]
    set f [expr {double($k+1)/($N+1)}]
    set mx [expr {[lindex $a 0]+$f*$dx}]; set my [expr {[lindex $a 1]+$f*$dy}]
    for {set t 0} {$t < 40} {incr t} {
      set rx0 [expr {round(max($cx0, min($cx1-$rw, $mx-$rw/2)))}]; set ry0 [expr {round(max($cy0, min($cy1-$rh, $my-$rh/2)))}]
      set bx [list $rx0 $ry0 [expr {round($rx0+$rw)}] [expr {round($ry0+$rh)}]]
      if {![ws_ovl $bx $boxes]} break
      set step [expr {($t % 2 ? -1 : 1) * (($t/2)+1) * max($rw,$rh)}]
      set mx [expr {[lindex $a 0]+$f*$dx + $step*$ux}]; set my [expr {[lindex $a 1]+$f*$dy + $step*$uy}]
    }
    lappend boxes $bx
    set r [odb::dbRegion_create $ws_blk "ot_ws_[string map {. _ [ _ ] _} $c]_$k"]
    odb::dbBox_create $r {*}$bx
    $r setRegionType INCLUSIVE
    foreach i $ws_st($c,$k) { $r addInst $i }
    set ws_box($c,$k) $r
    incr nreg
  }
}
set ntok 0
foreach c [lsort -dictionary [array names ws_n]] {
  set pc [ws_partner $c]
  if {$pc eq ""} continue
  if {$pc eq "-"} { puts "OT_WS: token chain $c N=$ws_n($c): no data chain of the same depth, left unfenced"; continue }
  set N $ws_n($c)
  for {set k 0} {$k < $N} {incr k} {
    set j [expr {$N-1-$k}]
    if {![info exists ws_st($c,$k)] || ![info exists ws_box($pc,$j)]} continue
    foreach i $ws_st($c,$k) { $ws_box($pc,$j) addInst $i }
    incr ntok
  }
}
puts "OT_WS: $ntok token stages placed with their data stage"
puts "OT_WS: $nreg stage regions over [array size ws_n] chains (density $ws_dens)"
