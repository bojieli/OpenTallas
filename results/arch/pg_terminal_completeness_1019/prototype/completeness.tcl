source /proof/native_pg_binding.tcl
proc expect_fail {label expression pattern} {
  if {![catch {uplevel 1 $expression} msg] || ![string match $pattern $msg]} {error "WITNESS_MISSING $label: $msg"}
  puts "EXPECTED_FAIL $label $msg"
}
read_db /old/source_order_clone.odb
set b [ord::get_db_block]
set map [ot_pg_prepare $b]
if {[ot_pg_assert_all_native $b $map] != 196864} {error COVERAGE}
set rows 0
foreach inst [$b getInsts] {
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "NATIVE_INCONSISTENCY $why"}
    incr rows
  }
}
puts "ACTUAL_NATIVE_MASTER_CENSUS_PASS $rows PG MTerms each has exact same-role ITerm"
# Native fixture is complete. Proxy emulates an absent/stale ITerm lookup while
# retaining the actual native master, role, other terminals and supply mapping.
set ::real_inst [lindex [$b getInsts] 0]
set ::pg_mt [lindex [[$::real_inst getMaster] getMTerms] 0]
foreach mt [[$::real_inst getMaster] getMTerms] {
  if {[$mt getSigType] in {POWER GROUND}} {set ::pg_mt $mt; break}
}
set ::pin [$::pg_mt getName]
set ::real_term [$::real_inst findITerm $::pin]
set ::mode missing
proc instproxy {method args} {
  if {$method eq "findITerm" && [lindex $args 0] eq $::pin} {
    if {$::mode eq "missing"} {return NULL}
    return termproxy
  }
  return [$::real_inst $method {*}$args]
}
proc termproxy {method args} {
  if {$method eq "getSigType"} {return SIGNAL}
  return [$::real_term $method {*}$args]
}
proc blockproxy {method args} {
  if {$method eq "getInsts"} {return instproxy}
  return [$::b $method {*}$args]
}
foreach mode {missing mismatch} {
  set ::mode $mode
  set reason [expr {$mode eq "missing" ? "OT_PG_MISSING_ITERM" : "OT_PG_ITERM_TYPE_MISMATCH"}]
  expect_fail $mode {ot_pg_bind_before_protect $map instproxy} "*$reason*"
  set r [ot_pg_collect_all_native blockproxy $map]
  if {[dict get $r failure_count] != 1 || [dict get [lindex [dict get $r failures] 0] reason] ne $reason} {error "COLLECTOR_HID_$mode $r"}
  expect_fail final_$mode {ot_pg_assert_all_native blockproxy $map} "*$reason*"
}
puts "MASTER_COMPLETENESS_PASS actual196864 missingITermREFUSE typeMismatchREFUSE finalCollectorFAIL"
exit
