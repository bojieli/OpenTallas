# Native composition test of the strict PRE_FINAL_REPORT entry (native_pg_final_entry.tcl) inside the byte-identical
# ORFS final_connect/final_report (copied from tests/pg_final_order_1019). Cases:
#  birth     strict, real CTS checkpoint (192 unprotected unbound PG terms) -> births bound, guard PASS, GC, write, 510/510
#  protected strict, same checkpoint with every unbound inst set dont_touch -> OT_PG_FINAL_PROTECTED_UNBOUND_REFUSED, no GC/write
#  dirty     strict, binding counter dirty before entry -> OT_PG_FINAL_ENTRY_STATE_REFUSED, no GC/write
#  wrongrole strict, all-bound fixture with VDD typed GROUND -> OT_PG_RULE_ROLE, no GC/write
#  allbound  strict, all-bound fixture -> 0 births, guard PASS, write
#  default   OT_PG_STRICT=0 -> entry inert, canonical GC + write (stock ORFS behaviour)
set root /src
set here $root/tests/pg_final_entry_1019
set ::env(SCRIPTS_DIR) $here
set ::env(RESULTS_DIR) $::env(TEST_OUT)
set ::env(OT_PG_HELPER) $root/physical/common_flow/native_pg_binding.tcl
set ::env(OT_PG_STRICT) [expr {$::env(TEST_CASE) ne "default"}]
set ::gc_calls 0
set ::writes 0
namespace eval utl {}
proc utl::set_metrics_stage {args} {}
rename global_connect native_gc
proc global_connect {args} {incr ::gc_calls; native_gc {*}$args}
rename write_db native_write_db
proc write_db {args} {incr ::writes; native_write_db {*}$args}
rename read_db native_read_db
proc read_db {args} {
 native_read_db {*}$args
 set b [ord::get_db_block]
 source $::env(OT_PG_HELPER)
 set before [ot_pg_collect_all_native $b [ot_pg_prepare $b]]
 puts "BEFORE checked=[dict get $before checked] failures=[dict get $before failure_count]"
 if {$::env(TEST_CASE) eq "protected"} {
  foreach i [$b getInsts] {
   foreach t [$i getITerms] {
    if {[[$t getMTerm] getSigType] in {POWER GROUND} && [$t getNet] eq "NULL"} {$i setDoNotTouch 1; break}
   }
  }
 }
 if {$::env(TEST_CASE) eq "dirty"} {set ::ot_pg_bindings_dirty 1}
 if {$::env(TEST_CASE) eq "wrongrole"} {[$b findNet VDD] setSigType GROUND}
 set ::before_state [ot_pg_binding_state $b]
}
set rc [catch {source $here/final_report.tcl} why]
puts "COMPOSE rc=$rc gc_calls=$::gc_calls writes=$::writes reason=$why"
set b [ord::get_db_block]
set unchanged [expr {[ot_pg_binding_state $b] eq $::before_state}]
puts "UNCHANGED_BINDINGS $unchanged"
switch -- $::env(TEST_CASE) {
 protected {if {!$rc || ![string match {*OT_PG_FINAL_PROTECTED_UNBOUND_REFUSED count=*} $why] || $::gc_calls || $::writes || !$unchanged} {error PROTECTED_CASE_FAILED}}
 dirty {if {!$rc || ![string match {*OT_PG_FINAL_ENTRY_STATE_REFUSED*} $why] || $::gc_calls || $::writes || !$unchanged} {error DIRTY_CASE_FAILED}}
 wrongrole {if {!$rc || ![string match {*OT_PG_RULE_ROLE*} $why] || $::gc_calls || $::writes} {error ROLE_CASE_FAILED}}
 default {
  if {$rc || $::writes != 1 || $::gc_calls != 1} {error DEFAULT_CASE_FAILED}
  ot_pg_assert_all_native $b [ot_pg_prepare $b]
 }
 birth - allbound {
  if {$rc || $::writes != 1} {error "PASS_CASE_FAILED $why"}
  if {$::env(TEST_CASE) eq "birth" && $unchanged} {error BIRTH_NOT_BOUND}
  if {$::env(TEST_CASE) eq "allbound" && !$unchanged} {error ALLBOUND_CHANGED}
  ot_pg_assert_all_native $b [ot_pg_prepare $b]
 }
}
puts "TEST_PASS $::env(TEST_CASE)"
