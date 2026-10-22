source /proof/native_pg_binding.tcl
proc expect_fail {label expression pattern} {
  if {![catch {uplevel 1 $expression} msg] || ![string match $pattern $msg]} {error "WITNESS_MISSING $label: $msg"}
  puts "EXPECTED_FAIL $label $msg"
}
set path [lindex [glob /route/work/orfs/results/asap7/*/base/6_final.odb] 0]
read_db $path
set block [ord::get_db_block]
set mapping [ot_pg_prepare $block]
set missing {}; set saved {}
foreach inst [$block getInsts] {
  foreach term [$inst getITerms] {
    if {[[$term getMTerm] getSigType] in {POWER GROUND} && [$term getNet] eq "NULL"} {
      dict set missing [$inst getName] $inst
      lappend saved [list [$inst getName] [[$term getMTerm] getName]]
    }
  }
}
if {[dict size $missing] != 322 || [llength $saved] != 644} {error "WRONG_FIXTURE"}
# Actual old ordering is negative: global_connect skips protected cells.
global_connect
set fh [open /proof/original_native_pg_failures.tcldict w]
puts $fh [ot_pg_collect_all_native $block $mapping]
close $fh
expect_fail original_default {ot_pg_assert_all_native $block $mapping} {*OT_PG_FINAL_FAIL count=644*}
set inst [lindex [dict values $missing] 0]
expect_fail protected_order {ot_pg_bind_before_protect $mapping $inst} {*OT_PG_ORDER_PROTECTED_UNBOUND*}
# Fixture-only rewind protection to reproduce pre-protection insertion point.
# Production callback NEVER clears any protection.
set bound 0
dict for {name inst} $missing {
  if {![$inst isDoNotTouch]} {error "FIXTURE_NOT_PROTECTED $name"}
  $inst setDoNotTouch 0
  incr bound [ot_pg_bind_before_protect $mapping $inst]
  $inst setDoNotTouch 1
}
if {$bound != 644} {error "BIND_COUNT $bound"}
global_connect
set mapping [ot_pg_prepare $block]
if {[ot_pg_assert_all_native $block $mapping] != 196864} {error "COVERAGE_COUNT"}
# Correct already-bound protected cells are read-only/idempotent.
dict for {name inst} $missing {
  if {![$inst isDoNotTouch] || [ot_pg_bind_before_protect $mapping $inst] != 0} {error "PROTECTION_OR_IDEMPOTENCE"}
}
write_db /proof/source_order_clone.odb
# Native actual wrong-domain metadata refuses before protection.
set inst [lindex [dict values $missing] 0]
$inst setDoNotTouch 0
set term [$inst findITerm VDD]
set good [$term getNet]
$term connect [$block findNet VSS]
expect_fail wrong_role_net {ot_pg_bind_before_protect $mapping $inst} {*OT_PG_WRONG_DOMAIN*}
$term connect $good
# Unknown declared mapping and ambiguous actual-rule domain cannot infer names.
set key [list [$inst getName] VDD]
set bad $mapping; dict unset bad $key
expect_fail unknown_domain {ot_pg_bind_before_protect $bad $inst} {*OT_PG_UNKNOWN_DOMAIN*}
set aux [odb::dbNet_create $block AUX_POWER]
$aux setSigType POWER
add_global_connection -net AUX_POWER -inst_pattern .* -pin_pattern {^VDD$} -power
expect_fail ambiguous_rules {ot_pg_prepare $block} {*OT_PG_AMBIGUOUS_DOMAIN*}
puts "PROTOTYPE_PASS exact322instances644bindings all196864nativePGterms defaultFAIL protectedFAIL wrongFAIL unknownFAIL ambiguousFAIL"
exit
