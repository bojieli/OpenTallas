# LOCKUP-STATION-1130 (FABLE-CLOSURE-1515 (1)(2), OT_HOP_LATCH_LEAF=1): hop lockup latches ride their LAUNCH flop's clock
# LEAF.  clock_taps.tcl (PRE_CTS) parks every u_fl_* DLL/DHL latch it can trace to a launch flop (CLK disconnected) and
# lists "latch<TAB>launch" in /work/hop_latch_leaf.tsv, so the tap solve, the cap passes and TritonCTS see exactly the
# sinks of the kit without latches (t39 proof without parking: 26,592 latch pins on their launch taps, 10 taps over cap,
# clk_t6 15,062 sinks, CTS setup tns -400k vs -37k).  This POST_CTS step (cts_post.tcl, first, and again after
# leaf_affinity.tcl so a moved launch flop takes its latches along) connects each latch CLK to the net on its launch flop's
# CLK pin: launch -> latch shares the whole tree (CRPR to the leaf), latch -> capture keeps ~T/2 of hold.  The tap
# balance, leaf repeat and every later stage then see the latch loads.  Unless OT_HOP_LATCH_LEAF_SITE=keep, a latch
# placed more than OT_HOP_LATCH_LEAF_UM (default 20) from its launch flop moves next to it (the leaf wire stays short;
# the hop wire is on the latch -> capture leg, inside its T/2 window); the next legalisation places it.
# LOCKUP-STATION-R2 (t39 proof4): the resizer may swap a hop lockup latch (DLLx*) for a DFFLQx* falling-edge FLOP with the
# same pins (3_place: 988 of 28,649 u_fl_nl latches).  That is a function change LEC on 1_synth never sees, and the hop-latch
# passes skip the cell.  ot_latch_restore puts every u_fl_* / u_lk_nk_* cell that is not a latch back on a DLLx2 of its Vt
# (u_fx_* hop flops are flops by design and stay).  dont_touch is not used: ODB then refuses the CLK / D edits of CTS and repair.
proc ot_latch_restore {tag} {
  set blk [ord::get_db_block]; set db [ord::get_db]; set n 0; set miss 0
  foreach i [$blk getInsts] {
    set nm [$i getName]
    if {![regexp {(^|[./])(u_fl_|u_lk_nk_)} $nm] || [regexp {(^|[./])u_fx_} $nm]} continue
    set m [[$i getMaster] getName]
    if {[regexp {^(DLL|DHL)} $m] || ![regexp {^DFFL} $m]} continue
    set vt R; regexp {_75t_([RLS])$} $m -> vt
    set nm2 ""
    foreach lib [$db getLibs] { set c [$lib findMaster "DLLx2_ASAP7_75t_$vt"]; if {$c ne "NULL"} { set nm2 $c; break } }
    if {$nm2 eq "" || [catch {$i swapMaster $nm2}]} { incr miss; continue }
    incr n
  }
  puts "OT_LATCH_RESTORE $tag: $n lockup cell(s) swapped back from a flop to DLLx2, $miss failed"
}
proc hll_clk {inst} {
  foreach it [$inst getITerms] { if {[[$it getMTerm] getName] in {CLK CK}} { return $it } }
  return ""
}
proc hop_latch_leaf {tag} {
  set f /work/hop_latch_leaf.tsv
  ot_latch_restore leaf_$tag
  if {![file exists $f]} { puts "OT_HOP_LATCH_LEAF $tag: no $f"; return }
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set lim [expr {([info exists ::env(OT_HOP_LATCH_LEAF_UM)] ? $::env(OT_HOP_LATCH_LEAF_UM) : 20.0) * $dbu}]
  set keep [expr {[info exists ::env(OT_HOP_LATCH_LEAF_SITE)] && $::env(OT_HOP_LATCH_LEAF_SITE) eq "keep"}]
  set n 0; set same 0; set miss 0; set moved 0
  set h [open $f]
  while {[gets $h l] >= 0} {
    lassign [split $l "\t"] ln fn
    set li [$blk findInst $ln]; set fi [$blk findInst $fn]
    if {$li eq "NULL" || $fi eq "NULL"} { incr miss; continue }
    set lc [hll_clk $li]; set fc [hll_clk $fi]
    if {$lc eq "" || $fc eq "" || [$fc getNet] eq "NULL"} { incr miss; continue }
    set net [$fc getNet]
    if {[$lc getNet] ne "NULL" && [$lc getNet] eq $net} { incr same; continue }
    if {[$lc getNet] ne "NULL"} { $lc disconnect }
    $lc connect $net
    incr n
    if {!$keep && [$li getPlacementStatus] ni {FIRM LOCKED COVER}} {
      lassign [$fi getLocation] fx fy; lassign [$li getLocation] lx ly
      if {abs($fx - $lx) + abs($fy - $ly) > $lim} {
        $li setLocation [expr {$fx + [[$fi getMaster] getWidth]}] $fy
        $li setPlacementStatus PLACED
        incr moved
      }
    }
  }
  close $h
  puts "OT_HOP_LATCH_LEAF $tag: $n latch(es) hung on their launch flop's leaf, $same already there, $moved moved next to the launch flop, $miss not found"
  if {$moved && [info exists ::env(OT_HOP_LATCH_LEAF_DPL)] && $::env(OT_HOP_LATCH_LEAF_DPL) eq "1"} { catch {detailed_placement} }
}
