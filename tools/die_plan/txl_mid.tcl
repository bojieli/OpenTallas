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
# Comb sink (FAM-S81-SERDES-R7 11-23, serdes__t1__clfe1f0815 -312 ps): a bit whose first non-buffer load after q is LOGIC
# (the 9 RCK4 AM partial bits 545..553 feed the u_syn.g_ampipe am_a cone) used that gate's GPL spot as the endpoint, so all
# 4 rows sat within 400 um of the AM face and the 19-level cone carried 1,288 um to am_a.  Such a bit now walks forward
# through the logic (<= 40 levels) to the registers it feeds: the endpoint is their centroid, and the cone cells move
# evenly onto the last-row -> endpoint leg (each cell once).  No register reached = the old endpoint (same moves, same log).
# Kit use: copy to the kit and add "export OT_TXL_MID = 1" and "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl".
# OT_TXL_MID_CHAINS (default "u_txl"): space-separated ot_pl_pad instance paths (rows <C>.g_reg.r[k][b], last <C>.q[b]) to
# space the same way, e.g. "u_txl u_dec.u_rck_transport4" (DIE-S81-85 11-10: vC t14 GRT rck_transport4 r0 -> r1 1850 um,
# TT -412.5 ps at W=180).  Unset = u_txl only, same moves and same log line as before.
# OT_TXL_MID_FACE=1 (SERDES-TXPIPE 11-14, forms OT_S81_SERDES_TXPIPE / RXPIPE): a chain whose sink (or source) is a HARD
# MACRO pin keeps that end's row AT the pin (nearest free point to the pin, i.e. just outside the macro halo) and spaces the
# other rows evenly on the remaining span: sink macro -> rows at k/N (k=1..N-1) of src->pin, last row at the pin; source
# macro -> first row at the pin, the rest at k/N toward the sink.  serdes__t14: the PMA TX data face (2246 um wide, behind
# the RX PMA band) and the RX PMA q face are both one register away from their macro.  Unset / 0 = the even rule above
# for every chain (same moves, same log line).
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
  # OT_TXL_MID_FACE: n row targets with the macro end's row at that end (end: snk | src | {} = even)
  proc face_targets {ax ay bx by n end} {
    if {$end eq "snk"} { return [concat [targets $ax $ay $bx $by [expr {$n-1}]] [list [list $bx $by]]] }
    if {$end eq "src"} { return [concat [list [list $ax $ay]] [targets $ax $ay $bx $by [expr {$n-1}]]] }
    return [targets $ax $ay $bx $by $n]
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
  proc is_reg {inst} { return [regexp {DFF|^DHL|^DLL|^SDF|^ICG} [[$inst getMaster] getName]] }
  # logic cells from an output iterm forward to the registers / macros they feed (<= maxd levels, nearest q first):
  # {cells terminal_iterms}
  proc fwd_cone {it maxd} {
    set cells {}; set seen [dict create]; set terms {}; set front [list $it]
    for {set l 0} {$l < $maxd && [llength $front] && [llength $cells] < 4000} {incr l} {
      set next {}
      foreach o $front {
        set n [$o getNet]; if {$n eq "NULL"} continue
        foreach t [$n getITerms] {
          if {[[$t getMTerm] getIoType] ne "INPUT"} continue
          set i [$t getInst]
          if {[[$i getMaster] isBlock] || [is_reg $i]} { lappend terms $t; continue }
          if {[dict exists $seen [$i getName]]} continue
          dict set seen [$i getName] 1; lappend cells $i
          foreach u [$i getITerms] { if {[[$u getMTerm] getIoType] eq "OUTPUT"} { lappend next $u } }
        }
      }
      set front $next
    }
    return [list $cells $terms]
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
        # RXNEG uses a named falling-edge register vector C_q rather than
        # an ot_pl_pad instance C.q.  It is the same one-row face station.
        set cp [string map {. {\.}} $C]
        set pad [expr {[string first "$C.q" $nm]>=0 && [regexp [string cat $cp {\.q\\?\[[0-9]+\\?\]}] $nm]}]
        set reg [expr {[string first [string cat $C _q] $nm]>=0 && [regexp [string cat $cp {_q\\?\[[0-9]+\\?\]}] $nm]}]
        # Yosys scalarises the one-bit valid pad: C.q$_DFF_P_, no [0].
        set scalar [expr {[string first "$C.q" $nm]>=0 && [regexp [string cat $cp {\.q(\$|$)}] $nm]}]
        if {$pad || $reg || $scalar} { dict lappend lasts $C $i }
      }
    }
    set ret {}
    foreach C $chains {
    set clasts [expr {[dict exists $lasts $C] ? [dict get $lasts $C] : {}}]
    if {![llength $clasts]} {error "OT_TXL_MID requested chain $C has no register endpoints"}
    if {$C eq "u_rxf"} {
      set bits {};set rxneg 0
      foreach i $clasts {
        set name [$i getName]
        if {[string first "u_rxf_q" $name]>=0} {set rxneg 1}
        if {[regexp {\\?\[([0-9]+)\\?\]} $name _ bit]} {dict set bits $bit 1}
      }
      if {$rxneg && [dict size $bits] != 545} {error "OT_TXL_MID RXNEG face width [dict size $bits], expected 545 data/valid bits"}
    }
    set moved 0; set rows 0; set skip 0; set nofree 0; set hmax 0.0; set hcells 0; set nface 0
    set nreg 0; set ncone 0; set conedone [dict create]
    set face [expr {[info exists ::env(OT_TXL_MID_FACE)] && $::env(OT_TXL_MID_FACE) eq "1"}]
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
      set cone {}
      set si [$snk getInst]
      if {![[$si getMaster] isBlock] && ![is_reg $si] && ![is_buf $si]} {
        lassign [fwd_cone $qo 40] cone terms
        if {[llength $terms]} {
          set sx 0.0; set sy 0.0
          foreach t $terms { lassign [ctr $t] tx ty; set sx [expr {$sx+$tx}]; set sy [expr {$sy+$ty}] }
          set bx [expr {$sx/[llength $terms]}]; set by [expr {$sy/[llength $terms]}]
          incr nreg
        } else { set cone {} }
      }
      set n [llength $chain]
      set end {}
      if {$face} {
        set sb [[[$snk getInst] getMaster] isBlock]; set ab [[[$src getInst] getMaster] isBlock]
        if {$sb && !$ab} { set end snk } elseif {$ab && !$sb} { set end src }
        if {$end ne ""} { incr nface }
      }
      # RXNEG launches on the falling edge; face_p_[dv] captures the next
      # rising edge. Put this half-cycle pair together, leaving the long
      # decoder span on the following full-cycle leg. Default off.
      set rxpair [expr {[info exists ::env(OT_TXL_MID_RXNEG_PAIR)] && $::env(OT_TXL_MID_RXNEG_PAIR) eq "1" &&
                       [string match "u_dec.u_face_p_*" $C] &&
                       [string first "u_rxf_q" [[$src getInst] getName]]>=0 &&
                       [string match "DFFL*" [[[$src getInst] getMaster] getName]]}]
      # The valid bit has a register source (rn_r), not a PMA macro.
      # Its positive -> negative edge hop also has only half a cycle.
      set rxvalid [expr {[info exists ::env(OT_TXL_MID_RXNEG_PAIR)] && $::env(OT_TXL_MID_RXNEG_PAIR) eq "1" &&
                        $C eq "u_rxf" &&
                        [string match "DFFL*" [[$q getMaster] getName]] &&
                        [string match "DFF*" [[[$src getInst] getMaster] getName]] &&
                        ![string match "DFFL*" [[[$src getInst] getMaster] getName]]}]
      if {$rxpair || $rxvalid} {
        if {$n != 1} {error "OT_TXL_MID RXNEG half-cycle pair expects exactly one face row"}
        # Adjacent row below the source; nearest_free also clears the macro halo.
        set pts [list [list $ax [expr {$ay-2.16*$dbu}]]]
      } else {
        set pts [face_targets $ax $ay $bx $by $n $end]
      }
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
      if {[llength $cone]} {
        set todo {}
        foreach c $cone { if {![dict exists $conedone [$c getName]]} { dict set conedone [$c getName] 1; lappend todo $c } }
        incr ncone [place_hop [lreverse $todo] $px $py $bx $by $macs $core $step $maxr]
      }
      set h [expr {(abs($bx-$px)+abs($by-$py))/$dbu}]
      if {$h > $hmax} { set hmax $h }
      incr moved
    }
    set tag [expr {$chains eq "u_txl" ? "" : " chain $C"}]
    puts "OT_TXL_MID$tag bits moved $moved of [llength $clasts], rows $rows, skipped (no enc/PMA endpoint) $skip, no free point $nofree, hop cells moved $hcells, max hop [format %.0f $hmax] um[expr {$face ? ", macro-face anchored $nface" : ""}][expr {$nreg ? ", comb-sink bits to registers $nreg, cone cells moved $ncone" : ""}]"
    lappend ret [list $moved [llength $clasts] $hmax]
    }
    return [expr {[llength $ret] == 1 ? [lindex $ret 0] : $ret}]
  }
}
if {[info exists ::env(OT_TXL_MID)] && $::env(OT_TXL_MID) eq "1"} { ot_txl_mid::run }
