# HBM-SMATT9 10-20 (PVM9 r8): r6c 5_1_grt FF hold -50.0 ps on 448 reg->reg endpoints, ALL inside the bind-first kernels
# (g_native7.u_native cNNNN/QN -> inv -> cMMMM/D, ~82 ps local CTS skew, 45 ps data): repair_timing cannot insert hold
# buffers because the kernel flops and nets are dont_touch (the r6b release covered CTS only). Owner 10-20 09:05:
# standard equivalence (RTL vs netlist) + strict bind, no native formal proof. So keep the SEQUENTIAL kernel cells and the
# nets on their non-clock INPUT pins released through 4_1_cts and 5_1_grt (CTS + hold repair); combinational kernel cells
# stay dont_touch. pvm8_restore.tcl (POST_GLOBAL_ROUTE) re-protects every surviving cell/net and reports every change.
set pc_b [ord::get_db_block]
set pc_f [open $::env(RESULTS_DIR)/pvm_cts_release.txt w]
set pn_f [open $::env(RESULTS_DIR)/pvm8_release_nets.txt w]
set pc_n 0; set pn_n 0
foreach i [$pc_b getInsts] {
  if {![$i isDoNotTouch] || ![[$i getMaster] isSequential]} continue
  set row [list [$i getName] [[$i getMaster] getName]]
  foreach t [$i getITerms] {
    if {[$t isClocked]} continue
    set n [$t getNet]
    lappend row [[$t getMTerm] getName]=[expr {$n eq "NULL" ? "-" : [$n getName]}]
    if {$n ne "NULL" && [$t isInputSignal] && [$n isDoNotTouch]} {$n setDoNotTouch false; puts $pn_f [$n getName]; incr pn_n}
  }
  puts $pc_f $row
  $i setDoNotTouch false
  incr pc_n
}
close $pc_f; close $pn_f
puts "PVM8_RELEASE sequential_dont_touch=$pc_n input_nets=$pn_n"
if {$pc_n == 0} {error "PVM8_RELEASE found no protected sequential kernel cells"}
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
