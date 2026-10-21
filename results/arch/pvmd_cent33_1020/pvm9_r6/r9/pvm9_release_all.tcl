# HBM-PVM10 10-20 (PVM9 r9): r8 5_1_grt RSZ-3006 = repair_design could not buffer released kernel net
# g_madd[5]...g_native7.u_native.n3623 because one of its loads (comb cell c2189/A) was still dont_touch: r8 released
# only sequential kernel cells + their input nets, a half-release the resizer cannot work with.  Owner 10-20 09:05:
# no native formal proof; standard equivalence (RTL vs final netlist) + strict bind.  So the bind-first kernel
# dont_touch (needed only for placement fences/native census up to 3_place) is dropped for good from 4_1_cts on:
# every dont_touch inst and net inside a g_native*.u_native kernel is released, listed, and NOT restored.
set pr_b [ord::get_db_block]
set pr_fi [open $::env(RESULTS_DIR)/pvm9_released_insts.txt w]
set pr_fn [open $::env(RESULTS_DIR)/pvm9_released_nets.txt w]
set ni 0; set nn 0; set other_i 0; set other_n 0
foreach i [$pr_b getInsts] {
  if {![$i isDoNotTouch]} continue
  if {[string match {*u_native*} [$i getName]]} {puts $pr_fi "[$i getName] [[$i getMaster] getName]"; $i setDoNotTouch false; incr ni} else {incr other_i}
}
foreach n [$pr_b getNets] {
  if {![$n isDoNotTouch]} continue
  if {[string match {*u_native*} [$n getName]]} {puts $pr_fn [$n getName]; $n setDoNotTouch false; incr nn} else {incr other_n}
}
close $pr_fi; close $pr_fn
puts "PVM9_RELEASE_ALL kernel_insts=$ni kernel_nets=$nn other_dont_touch_insts=$other_i other_dont_touch_nets=$other_n"
if {$ni == 0} {error "PVM9_RELEASE_ALL found no protected kernel cells"}
source /work/hooks/pre_cts_ot_cts_fix.tcl
# r6b EST-0104 fix kept: re-estimate placement RC after standard-mode ot_protect_clock_tree PG binding.
if {[info procs ot_protect_clock_tree] ne "" && [info procs pvm_cts_orig_protect_clock_tree] eq ""} {
  rename ot_protect_clock_tree pvm_cts_orig_protect_clock_tree
  proc ot_protect_clock_tree {args} {
    set r [pvm_cts_orig_protect_clock_tree {*}$args]
    estimate_parasitics -placement
    puts "PVM_CTS_REESTIMATE after ot_protect_clock_tree"
    return $r
  }
}
