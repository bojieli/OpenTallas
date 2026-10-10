# PRE_GLOBAL_PLACE hook (CLAUDE HBM-ABSTRACTS svcidx): spread the wire stages of every ot_svc_vpipe chain evenly along
# the line between the terminals that feed the chain and the terminals it drives.
# Why: a view outline is the r16g die slot (svc 8.5 mm x 0.26 mm, index quarter 0.93 x 5.53 mm) and its long paths
# carry N wire-stage registers sized at <= 430 um a stage.  Global placement does not spread a register chain between
# two far terminals: it clumps the chain (index_q idx_p55: u_kp stages 1..13 within y 1936..2924 while t_vm sits at
# y 5430, routed WNS -5.2 ns).  This hook puts stage k of an N-stage chain at
# A + (k+1)/(N+1) * (B - A), A / B = centroids of the nearest terminals reached backwards from stage 0 / forwards
# from stage N-1 (breadth-first over cells, sequential cells included, nets with more than OT_WS_FANOUT loads
# skipped), so every hop carries 1/(N+1) of the distance.  Stage k's flops are packed into free legal sites around that
# point (pitch = cell width / OT_WS_DENSITY, default 0.12) and fixed (FIRM): see the placement section.
# Membership: flops named <chain>.gn.st[k].r[*] and <chain>.gn.rv[k] (synthesis keeps register names).
# Terminal positions come from the IO constraint file (ORFS erases IO_CONSTRAINTS in the floorplan stage, so the
# route passes the same file as OT_IO_FILE).
global ws_pin ws_chain ws_fan ws_tok ws_n ws_seeds occ
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
  if {[regexp {^(.+)\.gn\.(?:st\[([0-9]+)\]\.r|rv\[([0-9]+)\])} $n -> c k1 k2]} {
    set k [expr {$k1 ne "" ? $k1 : $k2}]
    lappend ws_st($c,$k) $i
    set ws_chain([$i getName]) $c
    if {![info exists ws_n($c)] || $k + 1 > $ws_n($c)} { set ws_n($c) [expr {$k + 1}] }
  }
}
# hbm-forks 2026-10-09: a one-stage chain's register drives the module output directly and synthesis names it after
# that output (<chain>.q[*], <chain>.qv): those chains were never fenced (svc PS: the W/E cross-bus input stage of
# c_sd / c_dd / c_wd chains sat at the destination unit, routed TT -47 .. -84 ps from the face pin).  Treat them as
# the chain's LAST stage: N - 1 with N from its rv[] / st[] names (rv is one vector, every bit kept), stage 0 when the
# chain has no other register (N = 1, rv itself renamed qv).
array set ws_q {}
foreach i [$ws_blk getInsts] {
  set n [string map {"\\" ""} [$i getName]]
  if {[regexp {^(c_[a-z]+[0-9]+_[0-9]+)\.(?:q\[[0-9]+\]|qv)} $n -> c] && [[$i getMaster] isSequential]} {
    lappend ws_q($c) $i
  }
}
foreach c [array names ws_q] {
  set k [expr {[info exists ws_n($c)] ? $ws_n($c) - 1 : 0}]
  foreach i $ws_q($c) { lappend ws_st($c,$k) $i; set ws_chain([$i getName]) $c }
  set ws_n($c) [expr {$k + 1}]
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
      set sq [[$i getMaster] isSequential]
      foreach it [$i getITerms] {
        if {$dir eq "back"} { if {[$it isOutputSignal]} continue } else { if {![$it isOutputSignal]} continue }
        # backwards through a flop only along its data input (an async reset / set pin leads to the reset port:
        # hfd_index_q_b0 u_kp found rst before the k pins through the FIFO's write-domain reset)
        if {$dir eq "back" && $sq && [[$it getMTerm] getName] ne "D"} continue
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
    if {[llength $pins]} { set ::ws_lastd $d; return $pins }
    set front $next
  }
  set ::ws_lastd -1
  return {}
}
proc ws_cent {l} {
  set sx 0.0; set sy 0.0
  foreach p $l { set sx [expr {$sx+[lindex $p 0]}]; set sy [expr {$sy+[lindex $p 1]}] }
  return [list [expr {$sx/[llength $l]}] [expr {$sy/[llength $l]}]]
}
# 1-bit return-token chains (u_dn / u_wdn / u_tb / u_eb) run against a data chain of the same depth in the same scope:
# token stage k is packed with data stage N-1-k
array set ws_tok {u_dn {u_bp u_p} u_wdn u_wp u_tb u_rq u_eb u_ep}
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
array set ws_tgt {}; array set ws_cells {}
# OT_WS_FILE (optional): explicit chain endpoints, `set ws_ab(<chain>) {ax ay bx by anA anB}` in um of this block (a
# generated view whose chains run between internal units rather than terminals); a listed chain skips the search
global ws_ab
array set ws_ab {}
if {[info exists ::env(OT_WS_FILE)] && $::env(OT_WS_FILE) ne ""} { source $::env(OT_WS_FILE) }
foreach c [lsort -dictionary [array names ws_n]] {
  set N $ws_n($c)
  if {[ws_partner $c] ne ""} continue
  if {![info exists ws_st($c,0)] || ![info exists ws_st($c,[expr {$N-1}])]} continue
  if {[info exists ws_ab($c)]} {
    lassign $ws_ab($c) ax ay bx by anA anB
    set A [list [list [expr {round($ax*$ws_dbu)}] [expr {round($ay*$ws_dbu)}]]]
    set B [list [list [expr {round($bx*$ws_dbu)}] [expr {round($by*$ws_dbu)}]]]
  } else {
  set A [ws_bfs $ws_st($c,0) back $ws_depth]; set dA $::ws_lastd
  set B [ws_bfs $ws_st($c,[expr {$N-1}]) fwd $ws_depth]; set dB $::ws_lastd
  # a chain end whose terminal is reached within one cell (pin -> flop, flop QN -> inverter -> pin) is a FACE register:
  # it is anchored at that pin; otherwise the end sits one hop in from its terminal
  set anA [expr {$dA >= 0 && $dA <= 1}]; set anB [expr {$dB >= 0 && $dB <= 1}]
  }
  if {![llength $A] || ![llength $B]} {
    puts "OT_WS: chain $c N=$N: no terminal on one side ([llength $A] in / [llength $B] out), left unfenced"
    continue
  }
  set a [ws_cent $A]; set b [ws_cent $B]
  set dx [expr {[lindex $b 0]-[lindex $a 0]}]; set dy [expr {[lindex $b 1]-[lindex $a 1]}]
  set len [expr {hypot($dx,$dy)}]
  set ux [expr {$len > 0 ? $dx/$len : 1.0}]; set uy [expr {$len > 0 ? $dy/$len : 0.0}]
  puts [format "OT_WS: chain %s N=%d anchored %d/%d from (%.1f %.1f) to (%.1f %.1f) um, %.1f um Manhattan, %.1f um a hop" $c $N $anA $anB \
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
    if {$anA && $anB} { set f [expr {$N > 1 ? double($k)/($N-1) : 0.5}] } \
    elseif {$anA} { set f [expr {double($k)/$N}] } elseif {$anB} { set f [expr {double($k+1)/$N}] } \
    else {
      # OT_WS_END (views agent 2026-10-07, index_q b5 r22 kin -> st[0] -28 ps / b1 a0i -0.6: the pin hop carries only the
      # relay-budgeted ~517 ps while inner hops get the full period): the two end hops are OT_WS_END of an inner hop
      # (default 1 = the even spread above).  f = (e + k) / (N - 1 + 2e).
      set e [expr {[info exists ::env(OT_WS_END)] ? double($::env(OT_WS_END)) : 1.0}]
      set f [expr {($e + $k) / ($N - 1 + 2.0 * $e)}]
    }
    set ws_tgt($c,$k) [list [expr {[lindex $a 0]+$f*$dx}] [expr {[lindex $a 1]+$f*$dy}]]
    set ws_cells($c,$k) $ws_st($c,$k)
  }
}
# return tokens join the cell list of their mirrored data stage
set ntok 0
foreach c [lsort -dictionary [array names ws_n]] {
  set pc [ws_partner $c]
  if {$pc eq ""} continue
  if {$pc eq "-"} { puts "OT_WS: token chain $c N=$ws_n($c): no data chain of the same depth, left free"; continue }
  set N $ws_n($c)
  for {set k 0} {$k < $N} {incr k} {
    set j [expr {$N-1-$k}]
    if {![info exists ws_st($c,$k)] || ![info exists ws_cells($pc,$j)]} continue
    set ws_cells($pc,$j) [concat $ws_cells($pc,$j) $ws_st($c,$k)]
    incr ntok
  }
}
if {[info exists ::env(OT_WS_REPORT)]} { return }
# ---------------------------------------------------------------- explicit legal placement (FIRM)
# Regions are NOT honoured by this OpenROAD's global or detailed placement (m1_idx: 0/514 and 7/514 stage cells inside
# their boxes after GP / DP), so each stage is packed into free legal sites around its target point and fixed.
# Cell pitch inside a stage block = cell width / OT_WS_DENSITY (snapped to sites): room for the resizer's buffers and
# for the stage's bus to escape and for the resizer to upsize a flop in place (no instance do-not-touch: it blocks
# buffering the stage's input nets, RSZ-3006); the block is roughly square.  Runs at PRE_GLOBAL_PLACE (tapcells and pins placed).
set rows {}
foreach r [$ws_blk getRows] {
  set o [$r getOrigin]; set st [$r getSite]
  lappend rows [list [lindex $o 1] [lindex $o 0] [expr {[lindex $o 0] + [$r getSiteCount]*[$st getWidth]}] [$st getWidth] [$st getHeight] [$r getOrient]]
}
set rows [lsort -integer -index 0 $rows]
set nrows [llength $rows]
set rowy0 [lindex $rows 0 0]; set rowh [lindex $rows 0 4]; set sitew [lindex $rows 0 3]
# occupancy: per row, list of {x0 x1} of fixed instances (tapcells, endcaps) and of what this hook places
array set occ {}
foreach i [$ws_blk getInsts] {
  if {![$i isFixed]} continue
  set bb [$i getBBox]
  for {set ri [expr {max(0, ([$bb yMin]-$rowy0)/$rowh)}]} {$ri < $nrows && [lindex $rows $ri 0] < [$bb yMax]} {incr ri} {
    lappend occ($ri) [list [$bb xMin] [$bb xMax]]
  }
}
proc ws_free {ri x0 x1} {
  global occ
  if {![info exists occ($ri)]} { return 1 }
  foreach iv $occ($ri) { if {$x0 < [lindex $iv 1] && [lindex $iv 0] < $x1} { return 0 } }
  return 1
}
set nplaced 0; set nfail 0; set nst 0
foreach key [lsort -dictionary [array names ws_tgt]] {
  set cells $ws_cells($key); set m [llength $cells]
  set wsum 0; foreach i $cells { incr wsum [[$i getMaster] getWidth] }
  set pitch [expr {max($sitew, int(ceil(double($wsum)/$m/$ws_dens/$sitew))*$sitew)}]
  set K [expr {max(1, int(ceil(sqrt(double($m)*$rowh/$pitch))))}]
  set tx [lindex $ws_tgt($key) 0]; set ty [lindex $ws_tgt($key) 1]
  set r0 [expr {max(0, min($nrows-1, int(($ty-$rowy0)/$rowh)))}]
  set q 0; set K0 $K
  # hbm-forks 2026-10-09: when every row's window around the target is taken (many one-stage chains now anchored at
  # the same face pins: svc PS SW_s1, 101 cells unplaced), widen the window 2x / 4x / 8x / 16x around the same point
  foreach ws_wf {1 2 4 8 16} {
  if {$q >= $m} break
  set K [expr {$K0 * $ws_wf}]; set dr 0; set tries 0
  # rows alternate around the target row; in each row up to K slots centred on the target x, sliding past occupancy
  while {$q < $m && $tries < 4*$nrows} {
    set ri [expr {$r0 + (($dr % 2) ? -(($dr+1)/2) : ($dr/2))}]; incr dr; incr tries
    if {$ri < 0 || $ri >= $nrows} continue
    set row [lindex $rows $ri]
    set ry [lindex $row 0]; set rx0 [lindex $row 1]; set rx1 [lindex $row 2]
    set x [expr {$rx0 + int((($tx - $K*$pitch/2.0) - $rx0)/$sitew)*$sitew}]
    set x [expr {max($rx0, min($rx1 - $K*$pitch, $x))}]
    set placed_row 0; set guard 0
    while {$placed_row < $K && $q < $m && $guard < 4*$K} {
      incr guard
      set i [lindex $cells $q]; set w [[$i getMaster] getWidth]
      # footprint reserved for the resizer: FIRM flops are still resized in place (repair_design upsized
      # DFFHQNx1 -> x2 into a tapcell, s1_b2 DPL-0033), so keep 3 sites free right of every placed cell
      set wr [expr {$w + 3*$sitew}]
      if {$x + $wr > $rx1} break
      if {[ws_free $ri $x [expr {$x+$wr}]]} {
        $i setOrient [lindex $row 5]
        $i setLocation $x $ry
        $i setPlacementStatus FIRM
        lappend occ($ri) [list $x [expr {$x+$wr}]]
        incr q; incr placed_row
      }
      set x [expr {$x + $pitch}]
    }
  }
  }
  incr nplaced $q; incr nfail [expr {$m - $q}]; incr nst
}
puts "OT_WS: $ntok token stages joined their data stage; $nst stages, $nplaced cells placed FIRM, $nfail not placed (density $ws_dens)"
if {$nfail > 0} { error "OT_WS: $nfail stage cells could not be placed" }
# ---------------------------------------------------------------- pin registers (OT_WS_PINREG=1)
# hbm-forks 2026-10-09 (svc SW_s7: wi -> c_wl stage 0 -41 ps / q7 -> u_sp7.loc.d_r -65 ps at the routed reference, the
# input-pin -> first-register wire alone 120-130 ps): every flop whose D is driven straight from ONE input pin (the
# first register of a face chain, an SM port's local input register) is moved, bit by bit, to the free site nearest
# ITS OWN pin (a chain's stage block is packed around the chain's centre, up to ~100 um from a bit's pin) and fixed.
# For faces whose inputs fail SETUP; it shortens the input min path too (hold-side faces use the --fc clock taps).
if {[info exists ::env(OT_WS_PINREG)] && $::env(OT_WS_PINREG) eq "1"} {
  set npr 0; set nprf 0
  set rx0_all [lindex $rows 0 1]; set rx1_all [lindex $rows 0 2]
  foreach i [$ws_blk getInsts] {
    if {![[$i getMaster] isSequential]} continue
    set dit [$i findITerm D]
    if {$dit eq "NULL"} continue
    set dn [$dit getNet]
    if {$dn eq "NULL"} continue
    set bts [$dn getBTerms]
    if {[llength $bts] != 1} continue
    set bt [lindex $bts 0]
    if {[$bt getIoType] ne "INPUT"} continue
    set bn [$bt getName]
    if {![info exists ws_pin($bn)]} continue
    lassign $ws_pin($bn) px py
    set w [[$i getMaster] getWidth]; set wr [expr {$w + 3*$sitew}]
    # nearest row to the pin, then outward; in each row the free slot nearest the pin x (sliding both ways)
    set r0 [expr {max(0, min($nrows-1, int(($py-$rowy0)/$rowh)))}]
    set done 0
    for {set dr 0} {$dr < 200 && !$done} {incr dr} {
      foreach ri [list [expr {$r0 - $dr}] [expr {$r0 + $dr}]] {
        if {$done || $ri < 0 || $ri >= $nrows} continue
        set row [lindex $rows $ri]; set ry [lindex $row 0]; set rx0 [lindex $row 1]; set rx1 [lindex $row 2]
        set xb [expr {$rx0 + int((max($rx0, min($rx1 - $wr, $px)) - $rx0)/$sitew)*$sitew}]
        for {set s 0} {$s < 400 && !$done} {incr s} {
          foreach x [list [expr {$xb + $s*$sitew}] [expr {$xb - $s*$sitew}]] {
            if {$done || $x < $rx0 || $x + $wr > $rx1} continue
            if {[ws_free $ri $x [expr {$x+$wr}]]} {
              $i setPlacementStatus PLACED     ;# a fenced stage flop is FIRM: unfix before moving (ODB-0359)
              $i setOrient [lindex $row 5]; $i setLocation $x $ry; $i setPlacementStatus FIRM
              lappend occ($ri) [list $x [expr {$x+$wr}]]
              set done 1
            }
          }
        }
      }
    }
    if {$done} { incr npr } else { incr nprf }
  }
  puts "OT_WS_PINREG: $npr pin registers placed beside their pins, $nprf not placed"
}
