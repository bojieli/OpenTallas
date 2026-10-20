# HBM-SMATT8 10-20 (PVM9 r6b): r6 4_1_cts ODB-0370 = CTS cannot re-connect the CLK term of dont_touch bind-first kernel
# flops.  Release dont_touch on the protected SEQUENTIAL kernel instances only for clock_tree_synthesis; record every
# non-clock term->net binding first.  pvm_cts_restore.tcl (run inside the clock_tree_synthesis wrapper, before repair_timing) re-protects exactly this set and refuses unless
# every non-clock binding is identical (CTS may only move the clock-input terms onto tree nets).
set pc_b [ord::get_db_block]
set pc_f [open $::env(RESULTS_DIR)/pvm_cts_release.txt w]
set pc_n 0
foreach i [$pc_b getInsts] {
  if {![$i isDoNotTouch] || ![[$i getMaster] isSequential]} continue
  set row [list [$i getName]]
  foreach t [$i getITerms] {
    if {[$t isClocked]} continue
    set n [$t getNet]
    lappend row [[$t getMTerm] getName]=[expr {$n eq "NULL" ? "-" : [$n getName]}]
  }
  puts $pc_f $row
  $i setDoNotTouch false
  incr pc_n
}
close $pc_f
puts "PVM_CTS_RELEASE sequential_dont_touch=$pc_n"
if {$pc_n == 0} {error "PVM_CTS_RELEASE found no protected sequential kernel cells"}
source /work/hooks/pre_cts_ot_cts_fix.tcl
# re-protect immediately after clock_tree_synthesis, so the post-CTS repair_timing / detailed_placement see the kernels dont_touch again
rename clock_tree_synthesis pvm_cts_orig_clock_tree_synthesis
proc clock_tree_synthesis {args} {
  pvm_cts_orig_clock_tree_synthesis {*}$args
  uplevel #0 {source /work/hooks/pvm_cts_restore.tcl}
}
# r6b EST-0104 (inconsistent parasitics at the CTS repair_timing): standard-mode ot_protect_clock_tree PG-binds the new CTS
# cells (pg_bound=5) after cts.tcl's estimate_parasitics and re-estimates only in strict mode.  Re-estimate placement RC
# after it here (what the strict branch does); run-local, reported to the common_flow owner.
if {[info procs ot_protect_clock_tree] ne "" && [info procs pvm_cts_orig_protect_clock_tree] eq ""} {
  rename ot_protect_clock_tree pvm_cts_orig_protect_clock_tree
  proc ot_protect_clock_tree {args} {
    set r [pvm_cts_orig_protect_clock_tree {*}$args]
    estimate_parasitics -placement
    puts "PVM_CTS_REESTIMATE after ot_protect_clock_tree"
    return $r
  }
}
