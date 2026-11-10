# POST_GLOBAL_PLACE hook (opt-in, OT_TXL_MID=1; DIE-S81-85 2026-11-09, form OT_S81_SERDES_TXL4): even stations for the
# serdes u_txl relay rows.
# Why: on the serdes kits wirelength-driven GPL leaves row 0 at the encoder and the last row near the PMA, so every bit
# puts its whole enc -> PMA span on one register hop (4_cts census: r0 -> q up to 2355 um, data delay above the 833 ps
# period, while enc -> r0 is 45-126 um median).  HPWL does not care where a 2-pin chain register sits on the line, so more
# rows alone do not help.  For every bit this hook walks the chain enc driver -> r[0] .. r[N-2] -> q -> PMA pin (through
# buffers and inverters) and moves the N rows to (k+1)/(N+1) of the straight line from the enc driver to the PMA pin.
# It runs after 3_3 global place and before 3_4 resize, so repair_design buffers the new hops and DPL legalises the rows;
# rows stay PLACED, nothing is fixed.  A station inside a macro halo moves to the nearest free point (Manhattan rings); a bit
# with no free point or an unresolved endpoint keeps its GPL location (logged).  FIRM/LOCKED rows are left alone.
# The buffers / inverters of each hop (the QN polarity inverter of every row is one) move with it, evenly spaced on the
# hop: pilot 11-10 moved rows only and left those cells at their GPL spot, so r[2] -> q ran 1136 -> 2170 -> 107 -> 587 um
# through a 49-cell chain (TT -1326 ps at GRT, W=180).
# Kit use: copy to the kit and add "export OT_TXL_MID = 1" and "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl".
# OT_TXL_MID_CHAINS (default "u_txl"): space-separated ot_pl_pad instance paths (rows <C>.g_reg.r[k][b], last <C>.q[b]) to
# space the same way, e.g. "u_txl u_dec.u_rck_transport4" (DIE-S81-85 11-10: vC t14 GRT rck_transport4 r0 -> r1 1850 um,
# TT -412.5 ps at W=180).  Unset = u_txl only, same moves and same log line as before.
namespace eval ot_txl_mid {
  # n points at (k+1)/(n+1) of the segment a->b
  proc targets {ax ay bx by n} {
    set out {}
    for {set k 1} {$k <= $n} {incr k} {
      set f [expr {double($k)/($n+1)}]
      lappend out [list [expr {$ax+($bx-$ax)*$f}] [expr {$ay+($by-$ay)*$f}]]
    }
    return $out
  }
  # macs: list of {x0 y0 x1 y1} halo boxes
  proc in_halo {x y macs} {
    foreach m $macs {
      lassign $m x0 y0 x1 y1
      if {$x >= $x0 && $x <= $x1 && $y >= $y0 && $y <= $y1} { return 1 }
    }
    return 0
  }
  # nearest free point to the target by Manhattan rings (step dbu, up to maxr dbu), inside core {cx0 cy0 cx1 cy1}; {} if none.
  # A macro wall (PMA band, decoder macros) blocks the straight line, so a station moves off the line, not along it.
  proc nearest_free {tx ty macs core step maxr} {
    lassign $core cx0 cy0 cx1 cy1
    set free [expr {$tx >= $cx0 && $tx <= $cx1 && $ty >= $cy0 && $ty <= $cy1 && ![in_halo $tx $ty $macs]}]
    if {$free} { return [list $tx $ty] }
    set n [expr {int($maxr/$step)}]
    for {set k 1} {$k <= $n} {incr k} {
      set r [expr {$k*$step}]
      set cand {}
      for {set i 0} {$i <= $k} {incr i} {
        set dx [expr {$i*$step}]; set dy [expr {$r-$dx}]
        foreach {sx sy} {1 1 1 -1 -1 1 -1 -1} { lappend cand [list [expr {$tx+$sx*$dx}] [expr {$ty+$sy*$dy}]] }
      }
      # prefer the smallest y move (keep the x station along the row)
      foreach c [lsort -real -command [list apply {{ty a b} {expr {abs([lindex $a 1]-$ty) < abs([lindex $b 1]-$ty) ? -1 : abs([lindex $a 1]-$ty) > abs([lindex $b 1]-$ty) ? 1 : 0}}} $ty] $cand] {
        lassign $c x y
        if {$x >= $cx0 && $x <= $cx1 && $y >= $cy0 && $y <= $cy1 && ![in_halo $x $y $macs]} { return [list $x $y] }
      }
    }
    return {}
  }
  proc is_buf {inst} { return [regexp {^(BUF|INV|HB[0-9])} [[$inst getMaster] getName]] }
  proc iterm_of {inst names} {
    foreach t [$inst getITerms] { if {[[$t getMTerm] getName] in $names} { return $t } }
    return ""
  }
  proc ctr {t} {
    set b [$t getBBox]
    return [list [expr {([$b xMin]+[$b xMax])/2.0}] [expr {([$b yMin]+[$b yMax])/2.0}]]
  }
  # driver of an input iterm through buffers: {inst iterm} or {}
  proc up {it} {
    for {set l 0} {$l < 40} {incr l} {
      set n [$it getNet]; if {$n eq "NULL"} { return {} }
      set o ""
      foreach t [$n getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { set o $t } }
      if {$o eq ""} { return {} }
      set i [$o getInst]
      if {![is_buf $i]} { return [list $i $o] }
      set it ""
      foreach t [$i getITerms] { if {[[$t getMTerm] getIoType] eq "INPUT" && [$t getNet] ne "NULL" && [[$t getNet] getSigType] ni {POWER GROUND}} { set it $t } }
      if {$it eq ""} { return {} }
    }
    return {}
  }
  # buffer / inverter cells from a D input up to its non-buffer driver, nearest the D first
  proc up_cells {it} {
    set out {}
    for {set l 0} {$l < 40} {incr l} {
      set n [$it getNet]; if {$n eq "NULL"} { return $out }
      set o ""
      foreach t [$n getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { set o $t } }
      if {$o eq ""} { return $out }
      set i [$o getInst]
      if {![is_buf $i]} { return $out }
      lappend out $i
      set it ""
      foreach t [$i getITerms] { if {[[$t getMTerm] getIoType] eq "INPUT" && [$t getNet] ne "NULL" && [[$t getNet] getSigType] ni {POWER GROUND}} { set it $t } }
      if {$it eq ""} { return $out }
    }
    return $out
  }
  # move hop cells (nearest the receiver first) evenly onto the segment a->b; returns cells moved
  proc place_hop {cells ax ay bx by macs core step maxr} {
    set n [llength $cells]; if {!$n} { return 0 }
    set k 0
    foreach c [lreverse $cells] p [targets $ax $ay $bx $by $n] {
      if {[$c getPlacementStatus] in {FIRM LOCKED COVER}} continue
      lassign $p tx ty
      set s [nearest_free $tx $ty $macs $core $step $maxr]
      if {![llength $s]} continue
      $c setLocation [expr {int([lindex $s 0])}] [expr {int([lindex $s 1])}]
      $c setPlacementStatus PLACED
      incr k
    }
    return $k
  }
  # first non-buffer load of an output iterm: iterm or {}
  proc down {it} {
    for {set l 0} {$l < 40} {incr l} {
      set n [$it getNet]; if {$n eq "NULL"} { return {} }
      set nxt ""
      foreach t [$n getITerms] {
        if {[[$t getMTerm] getIoType] ne "INPUT"} continue
        set i [$t getInst]
        if {![is_buf $i]} { return $t }
        set nxt $i
      }
      if {$nxt eq ""} { return {} }
      set it ""
      foreach t [$nxt getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { set it $t } }
      if {$it eq ""} { return {} }
    }
    return {}
  }
  proc run {} {
    set blk [ord::get_db_block]
    set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
    set halo [expr {8.64*$dbu}]
    set macs {}; set lasts [dict create]
    set chains [expr {[info exists ::env(OT_TXL_MID_CHAINS)] && [string trim $::env(OT_TXL_MID_CHAINS)] ne "" ? $::env(OT_TXL_MID_CHAINS) : "u_txl"}]
    set ca [$blk getCoreArea]; set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
    set step [expr {5.0*$dbu}]; set maxr [expr {400.0*$dbu}]
    foreach i [$blk getInsts] {
      if {[[$i getMaster] isBlock]} {
        set b [$i getBBox]
        lappend macs [list [expr {[$b xMin]-$halo}] [expr {[$b yMin]-$halo}] [expr {[$b xMax]+$halo}] [expr {[$b yMax]+$halo}]]
      }
      set nm [$i getName]
      foreach C $chains {
        if {[string first "$C.q" $nm] >= 0 && [regexp [string cat [string map {. {\.}} $C] {\.q\\?\[[0-9]+\\?\]}] $nm]} { dict lappend lasts $C $i }
      }
    }
    set ret {}
    foreach C $chains {
    set clasts [expr {[dict exists $lasts $C] ? [dict get $lasts $C] : {}}]
    set moved 0; set rows 0; set skip 0; set nofree 0; set hmax 0.0; set hcells 0
    foreach q $clasts {
      # rows oldest first, ending with q; src = enc driver output iterm
      set chain [list $q]; set src ""
      for {set cur $q} {[llength $chain] < 16} {} {
        set d [iterm_of $cur {D}]; if {$d eq ""} break
        set u [up $d]; if {![llength $u]} break
        lassign $u di dt
        if {[string first "$C.g_reg.r" [$di getName]] >= 0} { set chain [linsert $chain 0 $di]; set cur $di } else { set src $dt; break }
      }
      set qo [iterm_of $q {QN Q}]
      set snk [expr {$qo eq "" ? "" : [down $qo]}]
      if {$src eq "" || $snk eq ""} { incr skip; continue }
      lassign [ctr $src] ax ay; lassign [ctr $snk] bx by
      set n [llength $chain]
      set pts [targets $ax $ay $bx $by $n]
      set ok 1; set places {}
      foreach p $pts {
        lassign $p tx ty
        set s [nearest_free $tx $ty $macs $core $step $maxr]
        if {![llength $s]} { set ok 0; break }
        lappend places $s
      }
      if {!$ok} { incr nofree; continue }
      # hop cells first (walked on the netlist, independent of where the rows sit), then the rows
      set hops {}
      foreach r $chain { lappend hops [up_cells [iterm_of $r {D}]] }
      set snkcells [up_cells $snk]
      set px $ax; set py $ay
      foreach r $chain s $places hc $hops {
        lassign $s x y
        incr hcells [place_hop $hc $px $py $x $y $macs $core $step $maxr]
        if {[$r getPlacementStatus] in {FIRM LOCKED COVER}} { set px $x; set py $y; continue }
        $r setLocation [expr {int($x)}] [expr {int($y)}]
        $r setPlacementStatus PLACED
        incr rows
        set h [expr {(abs($x-$px)+abs($y-$py))/$dbu}]
        if {$h > $hmax} { set hmax $h }
        set px $x; set py $y
      }
      incr hcells [place_hop $snkcells $px $py $bx $by $macs $core $step $maxr]
      set h [expr {(abs($bx-$px)+abs($by-$py))/$dbu}]
      if {$h > $hmax} { set hmax $h }
      incr moved
    }
    set tag [expr {$chains eq "u_txl" ? "" : " chain $C"}]
    puts "OT_TXL_MID$tag bits moved $moved of [llength $clasts], rows $rows, skipped (no enc/PMA endpoint) $skip, no free point $nofree, hop cells moved $hcells, max hop [format %.0f $hmax] um"
    lappend ret [list $moved [llength $clasts] $hmax]
    }
    return [expr {[llength $ret] == 1 ? [lindex $ret 0] : $ret}]
  }
}
if {[info exists ::env(OT_TXL_MID)] && $::env(OT_TXL_MID) eq "1"} { ot_txl_mid::run }
