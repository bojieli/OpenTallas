# FABLE-FIX-S81-COLTAP 11-16 (PRE_RESIZE hook, after global placement; opt-in OT_RESET_CHAIN_SPREAD=1, unset = no-op):
# reset_replicate copy_depth chains u_x_r<k>_s0 .. _s<n-1>, u_x_r<k> are 2-pin nets, and GPL puts every chain flop next to
# the region's loads, so the whole way from the common flop u_x is in hop 1 (col_h9_r2: 836..1,174 um, -181 ps at CTS).
# Here the common flop moves to the centroid of its region copies and the chain flops of each region go to the points
# j/(n+1) on the line common -> region copy (outside every hard-core halo); DPL legalizes them.  A hop over
# OT_RESET_CHAIN_MAX_HOP_UM (390) is reported (the plan then needs a deeper copy_depth).  Runs before repair_design, so no
# buffers may already exist: v2 removes only transparent reset DATA buffers before resiting.
uplevel #0 {
if {[info exists ::env(OT_RESET_CHAIN_SPREAD)] && $::env(OT_RESET_CHAIN_SPREAD) eq "1"} {
  set rc_blk [ord::get_db_block]
  set rc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set rc_max [expr {[info exists ::env(OT_RESET_CHAIN_MAX_HOP_UM)] ? $::env(OT_RESET_CHAIN_MAX_HOP_UM) : 390.0}]
  set rc_halo [expr {int(6.48 * $rc_dbu)}]
  set rc_core [$rc_blk getCoreArea]
  set rc_mac {}
  foreach i [$rc_blk getInsts] {
    if {[[$i getMaster] isBlock]} {
      set b [$i getBBox]
      lappend rc_mac [list [expr {[$b xMin]-$rc_halo}] [expr {[$b yMin]-$rc_halo}] [expr {[$b xMax]+$rc_halo}] [expr {[$b yMax]+$rc_halo}]]
    }
  }
  proc rc_free {x y} {
    global rc_mac rc_core rc_halo
    if {$x < [$rc_core xMin] + $rc_halo || $x > [$rc_core xMax] - $rc_halo || $y < [$rc_core yMin] + $rc_halo || $y > [$rc_core yMax] - $rc_halo} { return 0 }
    foreach m $rc_mac { lassign $m a b c d; if {$x > $a && $x < $c && $y > $b && $y < $d} { return 0 } }
    return 1
  }
  # nearest free point on rings of 4.32 um around (x, y)
  proc rc_spot {x y} {
    global rc_dbu
    if {[rc_free $x $y]} { return [list $x $y] }
    set st [expr {int(4.32 * $rc_dbu)}]
    for {set r 1} {$r <= 120} {incr r} {
      foreach d {{1 0} {-1 0} {0 1} {0 -1} {1 1} {-1 1} {1 -1} {-1 -1}} {
        set px [expr {$x + [lindex $d 0] * $r * $st}]; set py [expr {$y + [lindex $d 1] * $r * $st}]
        if {[rc_free $px $py]} { return [list $px $py] }
      }
    }
    return [list $x $y]
  }
  proc rc_xy {i} { set b [$i getBBox]; return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]] }
  proc rc_put {i x y} {
    set b [$i getBBox]
    $i setLocation [expr {int($x - ([$b xMax] - [$b xMin]) / 2)}] [expr {int($y - ([$b yMax] - [$b yMin]) / 2)}]
    $i setPlacementStatus PLACED
  }
  # pass 1: chain flops name the drivers
  set rc_s {}; set rc_ff {}
  foreach i [$rc_blk getInsts] {
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
    set n [string map {\\ {}} [$i getName]]
    lappend rc_ff [list $n $i]
    if {[regexp {^(.+)_r([0-9]+)_s([0-9]+)[./]} $n -> x k j]} { dict set rc_s $x $k $j $i }
  }
  set rc_r {}; set rc_c {}
  foreach e $rc_ff {
    lassign $e n i
    if {[regexp {^(.+)_r([0-9]+)[./][^/.]*$} $n -> x k] && [dict exists $rc_s $x]} { dict set rc_r $x $k $i; continue }
    if {[regexp {^(.+)[./]q[^/.]*$} $n -> x] && [dict exists $rc_s $x]} { dict set rc_c $x $i }
  }
  # PRIVATE CANDIDATE v5: GPL already inserted reset-data buffers. Preserve
  # every polarity inverter and every clock net; prune ONLY reached BUF cells.
  set rc_bufs {}; set rc_invs {}
  set rc_roots {}
  dict for {x root} $rc_c {lappend rc_roots $root}
  dict for {x ks} $rc_s {dict for {k js} $ks {dict for {j root} $js {lappend rc_roots $root}}}
  foreach root $rc_roots {
    set q [$root findITerm QN]
    if {$q eq "NULL"} {set q [$root findITerm Q]}
    if {$q eq "NULL"} continue
    set todo [list [$q getNet]]; set seen {}
    while {[llength $todo]} {
      set net [lindex $todo 0]; set todo [lrange $todo 1 end]
      if {$net eq "NULL" || [dict exists $seen [$net getId]]} continue
      dict set seen [$net getId] 1
      if {[$net getSigType] eq "CLOCK"} {error "RESET v2 unexpectedly reaches CLOCK [$net getName]"}
      foreach it [$net getITerms] {
        if {[[$it getMTerm] getIoType] ne "INPUT"} continue
        set i [$it getInst]; set m [[$i getMaster] getName]
        if {![regexp {^(BUF|INV)} $m]} continue
        if {[string match BUF* $m]} {dict set rc_bufs [$i getName] 1} else {dict set rc_invs [$i getName] $root}
        foreach o [$i getITerms] {if {[[$o getMTerm] getIoType] eq "OUTPUT"} {lappend todo [$o getNet]}}
      }
    }
  }
  # S81-COL-FLOW-1118 (COORD: 27 col kits failed place on d8t): GPL inserted no reset-data buffer, so there is nothing to prune;
  # the resite below still runs (the removal and its count checks are guarded by the set size)
  if {![dict size $rc_bufs]} {puts "OT_RESET_V5 no reset data buffers reached from the chain flops: nothing to prune"}
  set rc_inv_names {}; set rc_clock_nets {}; set rc_clk_pins {}
  foreach i [$rc_blk getInsts] {
    foreach it [$i getITerms] {
      set pn [[$it getMTerm] getName]
      if {$pn ni {CLK CK CP CLK_N GCLK}} continue
      set net [$it getNet]
      dict set rc_clk_pins [$i getName] $pn [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
    }
  }
  foreach i [$rc_blk getInsts] {if {[string match INV* [[$i getMaster] getName]]} {dict set rc_inv_names [$i getName] 1}}
  foreach net [$rc_blk getNets] {if {[$net getSigType] eq "CLOCK"} {dict set rc_clock_nets [$net getName] 1}}
  dict for {name dummy} $rc_bufs {
    set i [$rc_blk findInst $name]
    if {$i eq "NULL" || ![string match BUF* [[$i getMaster] getName]]} {error "RESET v5 non-BUF selection $name"}
    foreach it [$i getITerms] {set net [$it getNet]; if {$net ne "NULL" && [$net getSigType] eq "CLOCK"} {error "RESET v5 clock-related BUF $name"}}
  }
  set rc_before_names {}
  foreach i [$rc_blk getInsts] {if {[string match BUF* [[$i getMaster] getName]]} {dict set rc_before_names [$i getName] 1}}
  if {[dict size $rc_bufs]} {
    set selected [get_cells [dict keys $rc_bufs]]
    if {[llength $selected] != [dict size $rc_bufs]} {error "RESET v5 explicit buffer selection mismatch"}
    foreach cell $selected {set n [get_full_name $cell]; if {![dict exists $rc_bufs $n]} {error "RESET v5 resolved unintended buffer $n"}}
    remove_buffers {*}[dict keys $rc_bufs]
  }
  set rc_removed 0
  dict for {n dummy} $rc_before_names {
    if {[$rc_blk findInst $n] eq "NULL"} {
      if {![dict exists $rc_bufs $n]} {error "RESET v3 removed unrelated buffer $n"}
      incr rc_removed
    }
  }
  if {$rc_removed != [dict size $rc_bufs]} {error "RESET v3 removed count mismatch $rc_removed"}

  dict for {n dummy} $rc_inv_names {if {[$rc_blk findInst $n] eq "NULL"} {error "RESET v5 removed INV $n"}}
  dict for {n dummy} $rc_clock_nets {set net [$rc_blk findNet $n]; if {$net eq "NULL" || [$net getSigType] ne "CLOCK"} {error "RESET v5 changed clock net $n"}}
  dict for {n pins} $rc_clk_pins {
    set i [$rc_blk findInst $n]
    if {$i eq "NULL"} {error "RESET v5 removed clock-pin owner $n"}
    dict for {pn oldnet} $pins {
      set it [$i findITerm $pn]; set net [$it getNet]
      set newnet [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
      if {$newnet ne $oldnet} {error "RESET v5 changed clock connectivity $n/$pn $oldnet -> $newnet"}
    }
  }
  puts "OT_RESET_V5 removed_data_buffers=[dict size $rc_bufs] preserved_inverters=[dict size $rc_invs]"
  proc rc_dist {a b} {expr {abs([lindex $a 0]-[lindex $b 0])+abs([lindex $a 1]-[lindex $b 1])}}
  # Joint coordinate descent on REAL adjacent stage locations, rather than
  # independently projecting an ideal straight line through macro keepouts.
  proc rc_joint {nodes} {
    global rc_dbu
    set st [expr {int(4.32*$rc_dbu)}]
    for {set pass 0} {$pass < 4} {incr pass} {
      for {set j 1} {$j < [llength $nodes]-1} {incr j} {
        set prev [rc_xy [lindex $nodes [expr {$j-1}]]]
        set next [rc_xy [lindex $nodes [expr {$j+1}]]]
        set inst [lindex $nodes $j]; set old [rc_xy $inst]
        set mid [list [expr {([lindex $prev 0]+[lindex $next 0])/2}] [expr {([lindex $prev 1]+[lindex $next 1])/2}]]
        set best {}; set score 1e100
        for {set r 0} {$r <= 120} {incr r} {
          foreach d {{1 0} {-1 0} {0 1} {0 -1} {1 1} {-1 1} {1 -1} {-1 -1}} {
            set x [expr {[lindex $mid 0]+[lindex $d 0]*$r*$st}]
            set y [expr {[lindex $mid 1]+[lindex $d 1]*$r*$st}]
            if {![rc_free $x $y]} continue
            set p [list $x $y]; set a [rc_dist $prev $p]; set b [rc_dist $p $next]
            set cost [expr {max($a,$b)*1000.0 + [rc_dist $old $p]}]
            if {$cost < $score} {set score $cost; set best $p}
          }
        }
        if {$best eq {}} {error "RESET v2 no macro-free point for [$inst getName]"}
        rc_put $inst {*}$best
      }
    }
  }
  set rc_n 0; set rc_worst 0.0; set rc_over 0
  dict for {x ks} $rc_s {
    if {![dict exists $rc_c $x] || ![dict exists $rc_r $x]} { puts "OT_RESET_CHAIN $x: no common flop or no region copies found, left to GPL"; continue }
    set c [dict get $rc_c $x]
    set sx 0; set sy 0; set m 0
    dict for {k i} [dict get $rc_r $x] { lassign [rc_xy $i] a b; set sx [expr {$sx + $a}]; set sy [expr {$sy + $b}]; incr m }
    lassign [rc_xy $c] ox oy
    lassign [rc_spot [expr {$sx / $m}] [expr {$sy / $m}]] cx cy
    rc_put $c $cx $cy
    set far 0.0
    dict for {k js} $ks {
      if {![dict exists $rc_r $x $k]} continue
      lassign [rc_xy [dict get $rc_r $x $k]] rx ry
      set n [dict size $js]
      set hop [expr {(abs($rx - $cx) + abs($ry - $cy)) / double($rc_dbu) / ($n + 1)}]
      if {$hop > $far} { set far $hop }
      if {$hop > $rc_max} { incr rc_over }
      foreach j [lsort -integer [dict keys $js]] {
        set f [expr {double($j + 1) / ($n + 1)}]
        lassign [rc_spot [expr {int($cx + $f * ($rx - $cx))}] [expr {int($cy + $f * ($ry - $cy))}]] px py
        rc_put [dict get $js $j] $px $py
        incr rc_n
      }
    }
    dict for {k js} $ks {
      if {![dict exists $rc_r $x $k]} continue
      set nodes [list $c]
      foreach j [lsort -integer [dict keys $js]] {lappend nodes [dict get $js $j]}
      lappend nodes [dict get $rc_r $x $k]
      rc_joint $nodes
    }
    if {$far > $rc_worst} { set rc_worst $far }
    puts "OT_RESET_CHAIN $x: common flop ([format %.0f [expr {$ox / double($rc_dbu)}]], [format %.0f [expr {$oy / double($rc_dbu)}]]) -> ([format %.0f [expr {$cx / double($rc_dbu)}]], [format %.0f [expr {$cy / double($rc_dbu)}]]), [dict size $ks] regions, longest hop [format %.0f $far] um"
  }
  # Polarity cells follow their TRUE source after final FF joint placement.
  dict for {name root} $rc_invs {
    set i [$rc_blk findInst $name]
    lassign [rc_xy $root] x y
    lassign [rc_spot [expr {$x+int(2.16*$rc_dbu)}] $y] x y
    rc_put $i $x $y
  }
  puts "OT_RESET_V5 candidate requires post-DPL actual Q-to-D hop and clock-profile census"
  puts "OT_RESET_CHAIN done: $rc_n chain flops placed, longest hop [format %.0f $rc_worst] um, $rc_over regions over [format %.0f $rc_max] um"
}
}
