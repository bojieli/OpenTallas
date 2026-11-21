# place_regions_cone.tcl -- pure procs of the PLACE-REGION cone rule (FLOW-NOADV-R3 11-20, FABLE-PD-S81-1840); sourced by place_regions.tcl
# (kit) and by the tclsh test.  No odb call in here: the callers pass the neighbour / candidate procs.
# Why: S81 serdes_tx_encoder: a region whose members were the 5,926 flops left 5,975 gates and the repair buffers of the same cone outside the
# group; the legaliser then found cells inside the region box that were not members (DPL-0033 on every J5 serdes).
#   ot_pr_cone MEMBERS IN_PROC OUT_PROC CAND_PROC LIMIT
#     the combinational cells of the logic cone of MEMBERS: breadth-first backward through IN_PROC (drivers) and forward through OUT_PROC
#     (loads) over cells CAND_PROC accepts (movable, standard, not sequential, not in another region); flops / macros end a branch.
#     More than LIMIT x |MEMBERS| cone cells = the cone is not separable from the design: error (refuse), never a silent whole-design region.
#   ot_pr_coverage N_MEMBERS N_EXTRA -> members / (members + cone cells)
proc ot_pr_cone {members in_proc out_proc cand_proc limit} {
  array unset seen
  foreach m $members { set seen($m) 1 }
  set extra {}
  set queue $members
  set max [expr {$limit * [llength $members]}]
  while {[llength $queue]} {
    set cur [lindex $queue 0]; set queue [lrange $queue 1 end]
    foreach nb [concat [$in_proc $cur] [$out_proc $cur]] {
      if {[info exists seen($nb)]} continue
      set seen($nb) 1
      if {![$cand_proc $nb]} continue
      lappend extra $nb
      lappend queue $nb
      if {[llength $extra] > $max} { error "cone has more than $max cells (> $limit x [llength $members] members): not separable from the design" }
    }
  }
  return $extra
}
proc ot_pr_coverage {n_members n_extra} {
  if {$n_members + $n_extra <= 0} { return 1.0 }
  return [expr {double($n_members) / ($n_members + $n_extra)}]
}
