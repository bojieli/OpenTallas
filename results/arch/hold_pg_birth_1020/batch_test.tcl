read_db $::env(BASE_ODB)
source /fix/physical/common_flow/native_pg_binding.tcl
read_lef /fix/unknown.lef
set b [ord::get_db_block]
set master [[ord::get_db] findMaster HB2xp67_ASAP7_75t_R]
set a [odb::dbInst_create $b $master pg_first_valid]
set badmaster $master
if {$::env(CASE) eq "unknown"} {set badmaster [[ord::get_db] findMaster PG_UNKNOWN_MASTER]}
set z [odb::dbInst_create $b $badmaster pg_second_bad]
$a setLocation 2160 2160;$a setPlacementStatus FIRM
$z setLocation 4320 2160;$z setPlacementStatus FIRM
if {$::env(CASE) in {wrong wrongprotected}} {[$z findITerm VDD] connect [$b findNet VSS]}
if {$::env(CASE) in {protected wrongprotected}} {$z setDoNotTouch 1}
proc state {b} {
 set r {};foreach i [$b getInsts] {
  set pins {};foreach t [$i getITerms] {lappend pins [list [[$t getMTerm] getName] [$t getNet]]}
  dict set r [$i getName] [list [$i getMaster] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [$i getSourceType] [lsort $pins]]
 }
 set rules {};foreach g [$b getGlobalConnects] {lappend rules [list [$g getInstPattern] [$g getPinPattern] [$g getNet] [$g getRegion]]}
 return [list $r [lsort $rules]]
}
set before [state $b]
set rc [catch {ot_pg_bind_batch_before_protect $b [list $a $z]} why]
if {$::env(CASE) ne "positive"} {
 if {!$rc} {error EXPECTED_REFUSAL}
 if {$before ne [state $b]} {error WHOLE_BATCH_PARTIAL_MUTATION}
 if {[[$a findITerm VDD] getNet] ne "NULL" || [$a isDoNotTouch]} {error FIRST_VALID_CHANGED_BEFORE_SECOND_REFUSAL}
 puts "HOLD_PG_ATOMIC_NEGATIVE case=$::env(CASE) PASS reason=$why all_pins_flags_source_rules_unchanged=1"
} else {
 if {$rc} {error $why}
 foreach i [list $a $z] {
  if {[[$i findITerm VDD] getNet] ne [$b findNet VDD] || [[$i findITerm VSS] getNet] ne [$b findNet VSS] || [$i isDoNotTouch]} {error BAD_POSITIVE_BIND}
  $i setDoNotTouch 1
 }
 puts "HOLD_PG_POSITIVE PASS bound=$why protected_after_binding=1"
}
