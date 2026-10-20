# Source-owned placement batch. No protection flags are set or cleared.
source /src/physical/common_flow/native_pg_binding.tcl
proc ot_candidate_pg_ready {stage} {
 set b [ord::get_db_block]
 set bound [ot_pg_bind_batch_before_protect $b [$b getInsts]]
 ot_pg_assert_all_native $b [ot_pg_prepare $b]
 puts "CANDIDATE_BIRTH_PG_READY stage=$stage newly_bound=$bound"
}
proc ot_candidate_physical_only {i} {
 set m [$i getMaster]
 if {[$m getType] ni {CORE_SPACER CORE_WELLTAP}} {return 0}
 set pins [$m getMTerms]
 if {![llength $pins]} {error "PHYSICAL_ONLY missing master pin census [$m getName]"}
 foreach p $pins {if {[$p getSigType] ni {POWER GROUND}} {return 0}}
 return 1
}
