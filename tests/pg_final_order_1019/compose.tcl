set root /src
set here $root/tests/pg_final_order_1019
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
# Entry fixture alterations happen immediately after load, before analysis.
rename read_db native_read_db
proc read_db {args} {
 native_read_db {*}$args
 set b [ord::get_db_block]
 source $::env(OT_PG_HELPER)
 set before [ot_pg_collect_all_native $b [ot_pg_prepare $b]]
 puts "BEFORE checked=[dict get $before checked] failures=[dict get $before failure_count]"
 set ::before_state [ot_pg_binding_state $b]
 if {$::env(TEST_CASE) eq "protected"} {
  foreach i [$b getInsts] {
   foreach t [$i getITerms] {
    if {[[$t getMTerm] getSigType] in {POWER GROUND} && [$t getNet] eq "NULL"} {$i setDoNotTouch 1; break}
   }
  }
 }
 if {$::env(TEST_CASE) eq "dirty"} {set ::ot_pg_bindings_dirty 1}
 if {$::env(TEST_CASE) eq "wrongrole"} {
  [$b findNet VDD] setSigType GROUND
 }
 if {$::env(TEST_CASE) eq "ambiguous"} {
  set alt [odb::dbNet_create $b VDD_SECOND_DOMAIN]
  $alt setSigType POWER
  $b addGlobalConnect NULL .* VDD $alt 0
 }
}
set rc [catch {source $here/final_report.tcl} why]
puts "COMPOSE rc=$rc gc_calls=$::gc_calls writes=$::writes reason=$why"
set b [ord::get_db_block]
set unchanged [expr {[ot_pg_binding_state $b] eq $::before_state}]
puts "UNCHANGED_BINDINGS $unchanged"
if {$::env(TEST_CASE) in {unbound protected}} {
 if {!$rc || ![string match {*OT_PG_FINAL_LATE_BINDING_REFUSED count=192*} $why] || $::gc_calls || $::writes || !$unchanged} {error COMPOSE_CAUSAL_FAILED}
} elseif {$::env(TEST_CASE) eq "dirty"} {
 if {!$rc || ![string match {*OT_PG_FINAL_RC_DIRTY_REFUSED*} $why] || $::gc_calls || $::writes} {error DIRTY_CAUSAL_FAILED}
} elseif {$::env(TEST_CASE) eq "wrongrole"} {
 if {!$rc || ![string match {*OT_PG_RULE_ROLE*} $why] || $::gc_calls || $::writes} {error ROLE_CAUSAL_FAILED}
} elseif {$::env(TEST_CASE) eq "ambiguous"} {
 if {!$rc || ![string match {*OT_PG_AMBIGUOUS_DOMAIN*} $why] || $::gc_calls || $::writes} {error DOMAIN_CAUSAL_FAILED}
} else {
 if {$rc || $::writes != 1} {error PASS_CONTROL_FAILED}
 ot_pg_assert_all_native $b [ot_pg_prepare $b]
}
puts "TEST_PASS $::env(TEST_CASE)"
