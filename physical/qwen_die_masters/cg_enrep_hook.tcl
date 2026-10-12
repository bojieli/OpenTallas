# el1011-q-seq (2026-10-11): regional ICG enables as a STANDALONE CTS hook (list it in OT_CTS_FIX_HOOKS AFTER
# physical/common_flow/cg_pushdown.tcl).  Why standalone: the TT batch overlay (tools/closure_loop/tt_overlay.py)
# refreshes physical/common_flow/cg_pushdown.tcl from its pinned copy (no OT_CG_ENREP), and ORFS floorplan
# eliminate_dead_logic deletes the RTL's kept-but-unloaded replica flops (g_merr.en_r), so ctlm_i-1763e0919 routed all
# 441 pushed-down u_me_cg clones on ONE enable flop (en_c -> ENA -555 ps post-CTS, 441 loads over 773 um).
# Here the replicas are made at CTS time from the enable's own driver: the gate clones (*u_me_cg* ICGs sharing one ENA
# net) are split into OT_CG_ENREP_N (16) location groups by recursive median bisection; for each group the enable's
# driving register (and an INV / BUF between it and the ENA net) is CLONED -- same master, same D / CLK nets -- and
# placed at the group centroid, and the group's ENA pins move to the clone's net.  The clones are identical registers
# of one D, so the function is unchanged (exact); every ICG enable becomes a short local wire.
proc ot_cg_enrep_clone {} {
  if {[info exists ::ot_cg_enrep_done]} return
  set gglob [expr {[info exists ::env(OT_CG_ENREP_GATE)] ? $::env(OT_CG_ENREP_GATE) : "*u_me_cg*"}]
  set R [expr {[info exists ::env(OT_CG_ENREP_N)] ? $::env(OT_CG_ENREP_N) : 16}]
  set blk [ord::get_db_block]
  set gates {}
  foreach i [$blk getInsts] { if {[string match $gglob [$i getName]] && [regexp {^ICG} [[$i getMaster] getName]]} { lappend gates $i } }
  if {[llength $gates] < 2} { puts "OT_CG_ENREP none (gates=[llength $gates])"; return }
  set en0 [[[lindex $gates 0] findITerm ENA] getNet]
  if {$en0 eq "NULL"} { puts "OT_CG_ENREP none (no ENA net)"; return }
  # the driver chain: up to two INV / BUF stages back to a register
  set chain {}; set d [$en0 getFirstOutput]
  for {set hop 0} {$hop < 3 && $d ne "NULL"} {incr hop} {
    set di [$d getInst]; set mn [[$di getMaster] getName]
    lappend chain [list $di [$d getMTerm]]
    if {[regexp {^(DFF|SDF)} $mn]} break
    if {![regexp {^(INV|BUF|HB)} $mn]} { puts "OT_CG_ENREP none (enable driver $mn is logic)"; return }
    set ai [$di findITerm A]
    if {$ai eq "NULL" || [$ai getNet] eq "NULL"} { puts "OT_CG_ENREP none (open chain)"; return }
    set d [[$ai getNet] getFirstOutput]
  }
  set reg [lindex [lindex $chain end] 0]
  if {![regexp {^(DFF|SDF)} [[$reg getMaster] getName]]} { puts "OT_CG_ENREP none (no register driver)"; return }
  set groups [list $gates]
  while {[llength $groups] < $R} {
    set li -1; set lm 1
    for {set x 0} {$x < [llength $groups]} {incr x} { if {[llength [lindex $groups $x]] > $lm} { set lm [llength [lindex $groups $x]]; set li $x } }
    if {$li < 0} break
    set g [lindex $groups $li]
    set xs [lmap i $g { lindex [$i getLocation] 0 }]; set ys [lmap i $g { lindex [$i getLocation] 1 }]
    set ax [expr {([tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs]) >= ([tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys]) ? 0 : 1}]
    set srt [lsort -integer -index 1 [lmap i $g { list $i [lindex [$i getLocation] $ax] }]]
    set h [expr {[llength $srt] / 2}]
    set groups [lreplace $groups $li $li [lmap e [lrange $srt 0 [expr {$h - 1}]] { lindex $e 0 }] [lmap e [lrange $srt $h end] { lindex $e 0 }]]
  }
  set k 0
  foreach g $groups {
    set sx 0; set sy 0
    foreach i $g { lassign [$i getLocation] x y; incr sx $x; incr sy $y }
    set cx [expr {$sx / [llength $g]}]; set cy [expr {$sy / [llength $g]}]
    # clone the chain from the register forward: register inputs keep their nets, each stage drives a new net
    set prev "NULL"
    for {set c [expr {[llength $chain] - 1}]} {$c >= 0} {incr c -1} {
      lassign [lindex $chain $c] oi omt
      set ni [odb::dbInst_create $blk [$oi getMaster] "ot_enrep_${k}_${c}"]
      foreach it [$oi getITerms] {
        set mt [$it getMTerm]
        if {[$mt getSigType] eq "POWER" || [$mt getSigType] eq "GROUND"} continue
        if {[$mt getIoType] eq "OUTPUT"} continue
        set nt [$ni findITerm [$mt getName]]
        if {$c < [llength $chain] - 1 && [$mt getName] eq "A"} { $nt connect $prev; continue }
        if {[$it getNet] ne "NULL"} { $nt connect [$it getNet] }
      }
      set on [odb::dbNet_create $blk "ot_enrep_n_${k}_${c}"]
      [$ni findITerm [$omt getName]] connect $on
      $ni setLocation $cx $cy; $ni setPlacementStatus PLACED
      set prev $on
    }
    foreach i $g { set en [$i findITerm ENA]; $en disconnect; $en connect $prev }
    incr k
  }
  set ::ot_cg_enrep_done 1
  puts "OT_CG_ENREP gates=[llength $gates] groups=$k chain=[llength $chain] (cloned [[$reg getMaster] getName] [$reg getName])"
}
if {[info procs ot_cg_pushdown] ne "" && [info procs ot_cg_pushdown_noenrep] eq ""} {
  rename ot_cg_pushdown ot_cg_pushdown_noenrep
  proc ot_cg_pushdown {} {
    ot_cg_pushdown_noenrep
    ot_cg_enrep_clone
    # cg_pushdown's clock_tree_synthesis wrapper runs repair_design only when clones were made: force it (new nets)
    set ::ot_cg_clones [expr {[info exists ::ot_cg_clones] ? max($::ot_cg_clones, 1) : 1}]
  }
  puts "OT_CG_ENREP hook armed (wraps ot_cg_pushdown)"
} else {
  puts "OT_CG_ENREP hook: ot_cg_pushdown not loaded (list cg_pushdown.tcl first)"
}
