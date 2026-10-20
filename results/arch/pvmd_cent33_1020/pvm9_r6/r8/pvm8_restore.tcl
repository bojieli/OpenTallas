# HBM-SMATT9 10-20 (PVM9 r8): re-protect the kernel set released by pvm8_release.tcl after 5_1_grt repair; report changes.
set pr_b [ord::get_db_block]
set pr_f [open $::env(RESULTS_DIR)/pvm_cts_release.txt r]
set pr_n 0; set pr_master 0; set pr_bind 0; set pr_missing 0
foreach row [split [string trim [read $pr_f]] "\n"] {
  set i [$pr_b findInst [lindex $row 0]]
  if {$i eq "NULL"} {incr pr_missing; puts "PVM8_RESTORE_MISSING [lindex $row 0]"; continue}
  if {[[$i getMaster] getName] ne [lindex $row 1]} {incr pr_master; if {$pr_master <= 5} {puts "PVM8_RESTORE_MASTER [lindex $row 0] [lindex $row 1] -> [[$i getMaster] getName]"}}
  set now [list [$i getName] [[$i getMaster] getName]]
  foreach t [$i getITerms] {
    if {[$t isClocked]} continue
    set n [$t getNet]
    lappend now [[$t getMTerm] getName]=[expr {$n eq "NULL" ? "-" : [$n getName]}]
  }
  if {[lrange $now 2 end] ne [lrange $row 2 end]} {incr pr_bind}
  $i setDoNotTouch true
  incr pr_n
}
close $pr_f
set nn 0
set nf [open $::env(RESULTS_DIR)/pvm8_release_nets.txt r]
foreach nm [split [string trim [read $nf]] "\n"] {set n [$pr_b findNet $nm]; if {$n ne "NULL"} {$n setDoNotTouch true; incr nn}}
close $nf
puts "PVM8_RESTORE reprotected=$pr_n nets=$nn missing=$pr_missing master_changed=$pr_master bindings_changed=$pr_bind (hold buffers on D inputs expected)"
if {$pr_missing} {error "PVM8_RESTORE $pr_missing protected kernel flops vanished"}
