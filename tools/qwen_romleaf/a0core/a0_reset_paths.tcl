# Opt-in synchronous reset delivery: four equally deep RTL landing levels, <=405um per registered hop.
# OT_RST_LAND_DISTRIBUTED=1 emits identical intermediate copy families; immutable synthesis proves each family's
# same clock/D/reset before redistributing loads, and ot_rst_copies.py pairs chain families copy k -> copy k.
# QC-A0R 2026-10-25: this hook no longer rewires anything.  It VERIFIES on the synthesized netlist that every
# level-L copy k is fed (through buffers / inverters only, logical polarity) by level-(L-1) copy k (level 1: the
# single stage-0 root), places every copy at its reviewed site and checks every registered hop <= 405 um.  A copy
# chain whose final copy has no live load is removed WHOLE by eliminate_dead_logic; a present copy without its
# same-index parent is an error (never bypassed).  (The old D-pin rewire connected D to the parent's QN net:
# inverted reset on ASAP7 DFFHQN.)
set aw_blk [ord::get_db_block]
set aw_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set aw_stages $::env(OT_RST_LAND_STAGES)
set aw_last [expr {$aw_stages-1}]
set aw_bt [$aw_blk findBTerm rst_n]
if {$aw_bt eq "NULL"} { error "OT_A0_RESET_PATH missing rst_n pin" }
set aw_bb [$aw_bt getBBox]
set aw_root [list [expr {([$aw_bb xMin]+[$aw_bb xMax])/2.0/$aw_dbu}] [expr {([$aw_bb yMin]+[$aw_bb yMax])/2.0/$aw_dbu}]]
set aw_cells {}; set aw_plan {}
if {![info exists ::env(OT_A0_RESET_PATHS)]} {error "OT_A0_RESET_PATH missing reviewed OT_A0_RESET_PATHS"}
set aw_fn [expr {[string match "/*" $::env(OT_A0_RESET_PATHS)] ? $::env(OT_A0_RESET_PATHS) : "/src/$::env(OT_A0_RESET_PATHS)"}]
set aw_f [open $aw_fn r]
while {[gets $aw_f line]>=0} {
  if {[string match "#*" $line] || [string trim $line] eq ""} continue
  lassign [split $line "\t"] k lev x y
  dict set aw_plan "$lev,$k" [list $x $y]
}
close $aw_f
foreach i [$aw_blk getInsts] {
  set nm [$i getName]
  if {![string match "*DFF*" [[$i getMaster] getName]]} continue
  if {[regexp {^ot_rrs__rst_n__ot_rl([0-9]*)v__c([0-9]+)} $nm -> lev k]} {
    if {$lev eq ""} {set lev $aw_last}
  } elseif {[regexp {^rst_n__ot_rl([0-9]+)\$} $nm -> lev]} {set k 0} else {continue}
  if {[dict exists $aw_cells "$lev,$k"]} {error "OT_A0_RESET_PATH ambiguous level/copy $lev,$k"}
  dict set aw_cells "$lev,$k" $i
}
# the register that logically drives the D pin of flop i, through single-input buffers / inverters only
proc aw_source {i} {
  set d {}
  foreach it [$i getITerms] { if {[[$it getMTerm] getName] eq "D"} {set d $it} }
  if {$d eq ""} {error "OT_A0_RESET_PATH [$i getName] has no D pin"}
  set net [$d getNet]; set inv 0
  for {set hop 0} {$hop<16} {incr hop} {
    if {$net eq "NULL"} {error "OT_A0_RESET_PATH [$i getName] D unconnected"}
    set drv {}
    foreach it [$net getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drv $it} }
    if {[llength $drv]!=1} {error "OT_A0_RESET_PATH [$i getName] D net [$net getName] has [llength $drv] drivers"}
    set it [lindex $drv 0]; set c [$it getInst]; set mn [[$c getMaster] getName]
    if {[string match "*DFF*" $mn]} {
      set pn [[$it getMTerm] getName]
      if {$pn eq "QN"} {set inv [expr {!$inv}]} elseif {$pn ne "Q"} {error "OT_A0_RESET_PATH $mn pin $pn"}
      return [list $c $inv]
    }
    if {![regexp {^(INV|BUF|HB)} $mn]} {error "OT_A0_RESET_PATH [$i getName] D driven by logic $mn ([$c getName])"}
    if {[string match "INV*" $mn]} {set inv [expr {!$inv}]}
    set a {}
    foreach t2 [$c getITerms] { if {[[$t2 getMTerm] getIoType] eq "INPUT"} {lappend a $t2} }
    if {[llength $a]!=1} {error "OT_A0_RESET_PATH buffer [$c getName] has [llength $a] inputs"}
    set net [[lindex $a 0] getNet]
  }
  error "OT_A0_RESET_PATH [$i getName] buffer chain too long"
}
proc aw_lpath {a b fraction} {
  lassign $a x0 y0; lassign $b x1 y1
  set dx [expr {abs($x1-$x0)}]; set dy [expr {abs($y1-$y0)}]
  set s [expr {($dx+$dy)*$fraction}]
  if {$s<=$dx} {return [list [expr {$x0+($x1>=$x0 ? 1:-1)*$s}] $y0]}
  return [list $x1 [expr {$y0+($y1>=$y0 ? 1:-1)*($s-$dx)}]]
}
set aw_positions {}; set aw_n 0; set aw_hmax 0; set aw_dead {}
set aw_out [open $::env(RESULTS_DIR)/a0_reset_path_flops.txt w]
# Index zero at every level is the canonical RTL chain; level-1 copies all hang off the single stage-0 register.
foreach key [lsort -dictionary [dict keys $aw_cells]] {
  lassign [split $key ,] lev k
  set i [dict get $aw_cells $key]
  if {![dict exists $aw_plan $key]} {error "OT_A0_RESET_PATH no reviewed site for $key"}
  set xy [dict get $aw_plan $key]
  lassign $xy x y
  $i setLocation [expr {int(round($x*$aw_dbu))}] [expr {int(round($y*$aw_dbu))}]
  $i setPlacementStatus FIRM
  dict set aw_positions $key $xy
  puts $aw_out [$i getName]
  incr aw_n
  if {$lev==0} continue
  set pkey "[expr {$lev-1}],[expr {$lev==1 ? 0:$k}]"
  if {![dict exists $aw_cells $pkey]} {error "OT_A0_RESET_PATH missing parent $pkey for $key"}
  lassign [aw_source $i] src inv
  if {$src ne [dict get $aw_cells $pkey]} {error "OT_A0_RESET_PATH $key fed by [$src getName], not same-index parent $pkey"}
  if {$inv} {error "OT_A0_RESET_PATH $key inverted parent polarity"}
}
for {set k 0} {$k<32} {incr k} {
  if {![dict exists $aw_cells "$aw_last,$k"] && [dict exists $aw_plan "$aw_last,$k"]} {lappend aw_dead $k}
}
close $aw_out
foreach key [dict keys $aw_positions] {
  lassign [split $key ,] lev k
  if {$lev==0} continue
  set pkey "[expr {$lev-1}],[expr {$lev==1 ? 0:$k}]"
  lassign [dict get $aw_positions $pkey] px py
  lassign [dict get $aw_positions $key] x y
  set d [expr {abs($x-$px)+abs($y-$py)}]
  if {$d>$aw_hmax} {set aw_hmax $d}
  if {$d>405} {error "OT_A0_RESET_PATH $pkey->$key hop $d >405um"}
}
puts "OT_A0_RESET_PATH $aw_n flops FIRM; $aw_stages reset cycles; same-index parents verified; dead whole chains (no live load) [list $aw_dead]; max planned registered hop $aw_hmax um PASS"
