# DIE-QC-75 11-05 (QC coll_s FF hold -320 ps): PHY-edge clock ports (plan clock.edge_clocks: clk_coll, clk_serdes, ...)
# have one port each, so clock_taps.tcl (the clk family only) leaves them one deep tree: coll_s clk_serdes 12,984 + 12
# macro sinks, capture 496-632 ps against clk taps 172-280.  No port or plan change: register sinks of an edge port over
# OT_EDGE_SPLIT_MAX_SINKS (default 1500) or wider than OT_EDGE_SPLIT_SPAN_UM (default 300) split by median bisection on
# the longer axis; each group gets one root buffer at its centroid and its own CTS tree under the port.  Macro clock pins
# get root buffers of their own (ot_edge_root_<port>_m<k>).  clock_edge_balance.tcl (POST_CTS) reports every root and pads a short
# one to the plan insertion.  Ports with one group are left alone.
# Sourced from pre_cts.tcl after clock_taps.tcl.  OT_EDGE_SPLIT=0 turns it off.
if {[info exists ::env(OT_EDGE_SPLIT_PORTS)] && !([info exists ::env(OT_EDGE_SPLIT)] && $::env(OT_EDGE_SPLIT) eq "0")} {
  set es_blk [ord::get_db_block]
  set es_dbu [expr {double([$es_blk getDbUnitsPerMicron])}]
  set es_cap [expr {[info exists ::env(OT_EDGE_SPLIT_MAX_SINKS)] ? $::env(OT_EDGE_SPLIT_MAX_SINKS) : 1500}]
  set es_span [expr {([info exists ::env(OT_EDGE_SPLIT_SPAN_UM)] ? $::env(OT_EDGE_SPLIT_SPAN_UM) : 300) * $es_dbu}]
  set es_mname [expr {[info exists ::env(OT_EDGE_SPLIT_BUF)] ? $::env(OT_EDGE_SPLIT_BUF) : "BUFx24_ASAP7_75t_R"}]
  set es_master [[ord::get_db] findMaster $es_mname]
  if {$es_master eq "NULL"} { error "OT_EDGE_SPLIT: buffer master $es_mname missing" }
  # one placed buffer from net src to a new clock net; returns the new net
  proc es_cell {blk master iname src nname x y} {
    set inst [odb::dbInst_create $blk $master $iname]
    set net [odb::dbNet_create $blk $nname]
    $net setSigType CLOCK
    foreach m [$master getMTerms] {
      if {[$m getSigType] ne "SIGNAL"} continue
      if {[$m getIoType] eq "INPUT"} { [$inst findITerm [$m getName]] connect $src } else { [$inst findITerm [$m getName]] connect $net }
    }
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
    return $net
  }
  # [list x y iterm] rows -> groups by median bisection; a group stops at <= cap sinks and <= span on both axes
  proc es_split {rows cap span} {
    set xs {}; set ys {}
    foreach r $rows { lappend xs [lindex $r 0]; lappend ys [lindex $r 1] }
    set sx [lsort -integer $xs]; set sy [lsort -integer $ys]
    set dx [expr {[lindex $sx end] - [lindex $sx 0]}]; set dy [expr {[lindex $sy end] - [lindex $sy 0]}]
    if {[llength $rows] <= $cap && $dx <= $span && $dy <= $span} { return [list $rows] }
    if {[llength $rows] < 2 || ($dx == 0 && $dy == 0)} { return [list $rows] }
    set ax [expr {$dx >= $dy ? 0 : 1}]
    set s [lsort -integer -index $ax $rows]
    set m [expr {[llength $s] / 2}]
    return [concat [es_split [lrange $s 0 [expr {$m - 1}]] $cap $span] [es_split [lrange $s $m end] $cap $span]]
  }
  # repeater chain port -> group root (one L path per group): CTS skips one-sink nets, so the port's own tree only spans the
  # chain heads beside the pin.  Without it the CTS H-tree over the whole type cost ~400 ps at 30 ps a level (coll_s probe).
  set es_seg [expr {([info exists ::env(OT_EDGE_SPLIT_SEG_UM)] ? $::env(OT_EDGE_SPLIT_SEG_UM) : 200) * $es_dbu}]
  set es_blocks {}
  foreach i [$es_blk getInsts] {
    if {[$i isBlock]} { set bb [$i getBBox]; lappend es_blocks [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] }
  }
  proc es_inside {x y blocks} {
    foreach b $blocks { lassign $b x0 y0 x1 y1; if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} { return 1 } }
    return 0
  }
  # points on the L path (sx,sy) -> (ex,ey), every seg, excluding the end; of the two L orders the one with fewer inside macros
  proc es_path {sx sy ex ey seg blocks} {
    set len [expr {abs($ex - $sx) + abs($ey - $sy)}]
    set n [expr {int(ceil(double($len) / $seg))}]
    set best {}; set bb 1e9
    foreach order {xy yx} {
      set pts {}; set bad 0
      for {set p 0} {$p < $n} {incr p} {
        set d [expr {double($p) * $len / $n}]
        set dx [expr {abs($ex - $sx)}]; set dy [expr {abs($ey - $sy)}]
        set ux [expr {$ex >= $sx ? 1 : -1}]; set uy [expr {$ey >= $sy ? 1 : -1}]
        if {$order eq "xy"} {
          set x [expr {$sx + $ux * min($d, $dx)}]; set y [expr {$sy + $uy * max(0.0, $d - $dx)}]
        } else {
          set y [expr {$sy + $uy * min($d, $dy)}]; set x [expr {$sx + $ux * max(0.0, $d - $dy)}]
        }
        lappend pts [list [expr {int($x)}] [expr {int($y)}]]
        incr bad [es_inside $x $y $blocks]
      }
      if {$bad < $bb} { set bb $bad; set best $pts }
    }
    return $best
  }
  foreach es_port $::env(OT_EDGE_SPLIT_PORTS) {
    set bt [$es_blk findBTerm $es_port]
    # a one-bit bus port reads clk_coll[0] in the netlist
    if {$bt eq "NULL" || $bt eq ""} { set bt [$es_blk findBTerm "${es_port}\[0\]"] }
    if {$bt eq "NULL" || $bt eq ""} { puts "OT_EDGE_SPLIT $es_port: no port"; continue }
    set root [$bt getNet]
    if {$root eq "NULL" || $root eq ""} { puts "OT_EDGE_SPLIT $es_port: no net"; continue }
    set pb [$bt getBBox]
    set es_px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set es_py [expr {([$pb yMin] + [$pb yMax]) / 2}]
    set rows {}; set mrows {}
    foreach it [$root getITerms] {
      if {![$it isInputSignal]} continue
      set inst [$it getInst]
      lassign [$inst getLocation] x y
      if {[$inst isBlock]} { lappend mrows [list $x $y $it] } else { lappend rows [list $x $y $it] }
    }
    set nm [llength $mrows]
    if {[llength $rows] == 0} { puts "OT_EDGE_SPLIT $es_port: no register sinks ($nm macro)"; continue }
    set groups [es_split $rows $es_cap $es_span]
    if {[llength $groups] < 2} { puts "OT_EDGE_SPLIT $es_port: [llength $rows] sinks, one group, left alone"; continue }
    set all {}
    set k 0; foreach g $groups { lappend all $k $g; incr k }
    if {$nm} { set j 0; foreach g [es_split $mrows 8 $es_span] { lappend all "m$j" $g; incr j } }
    set report {}; set es_nhead 0
    foreach {k g} $all {
      set sx 0.0; set sy 0.0
      foreach r $g { set sx [expr {$sx + [lindex $r 0]}]; set sy [expr {$sy + [lindex $r 1]}] }
      set cx [expr {int($sx / [llength $g])}]; set cy [expr {int($sy / [llength $g])}]
      # chain heads sit at the port; the last cell of the chain is the group root at the centroid
      # (distinct head sites: CTS keys sinks by location and loses the connection of a second sink at the same point)
      set src $root; set sn 0
      foreach pt [es_path $es_px $es_py $cx $cy $es_seg $es_blocks] {
        set hx [lindex $pt 0]
        if {$sn == 0} { incr hx [expr {$es_nhead * int($es_dbu)}]; incr es_nhead }
        set src [es_cell $es_blk $es_master "ot_edge_chain_${es_port}_${k}_$sn" $src "ot_edge_chain_${es_port}_${k}_n$sn" $hx [lindex $pt 1]]
        incr sn
      }
      set net [es_cell $es_blk $es_master "ot_edge_root_${es_port}_$k" $src "ot_edge_${es_port}_$k" $cx $cy]
      foreach r $g { set it [lindex $r 2]; $it disconnect; $it connect $net }
      lappend report [format "%s:%d@(%.0f,%.0f)" $k [llength $g] [expr {$cx / $es_dbu}] [expr {$cy / $es_dbu}]]
    }
    set k [expr {[llength $all] / 2}]
    puts "OT_EDGE_SPLIT $es_port: [llength $rows] register sinks + $nm macro -> $k roots: [join $report { }]"
  }
}
