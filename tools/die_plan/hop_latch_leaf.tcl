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
proc hll_clk {inst} {
  foreach it [$inst getITerms] { if {[[$it getMTerm] getName] in {CLK CK}} { return $it } }
  return ""
}
proc hop_latch_leaf {tag} {
  set f /work/hop_latch_leaf.tsv
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
