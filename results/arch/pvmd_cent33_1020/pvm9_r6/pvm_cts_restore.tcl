# HBM-SMATT8 10-20 (PVM9 r6b): re-protect the sequential kernel set released by pvm_cts_release.tcl; non-clock bindings must be identical.
set pr_b [ord::get_db_block]
set pr_f [open $::env(RESULTS_DIR)/pvm_cts_release.txt r]
set pr_n 0; set pr_bad 0
foreach row [split [string trim [read $pr_f]] "\n"] {
  set i [$pr_b findInst [lindex $row 0]]
  if {$i eq "NULL"} {error "PVM_CTS_RESTORE missing [lindex $row 0]"}
  set now [list [$i getName]]
  foreach t [$i getITerms] {
    if {[$t isClocked]} continue
    set n [$t getNet]
    lappend now [[$t getMTerm] getName]=[expr {$n eq "NULL" ? "-" : [$n getName]}]
  }
  if {$now ne $row} {incr pr_bad; if {$pr_bad < 5} {puts "PVM_CTS_RESTORE_DIFF $row -> $now"}}
  $i setDoNotTouch true
  incr pr_n
}
close $pr_f
if {$pr_bad} {error "PVM_CTS_RESTORE $pr_bad of $pr_n protected kernel flops changed a non-clock binding during CTS"}
puts "PVM_CTS_RESTORE_PASS reprotected=$pr_n nonclock_bindings_identical"
# (called from the clock_tree_synthesis wrapper in pvm_cts_release.tcl, BEFORE repair_timing / detailed_placement)
