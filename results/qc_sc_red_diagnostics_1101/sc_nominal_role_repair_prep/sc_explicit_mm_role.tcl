# PRIVATE analysis-role adapter. No SDC path alias, constraint or source-stage credit.
proc ot_sc_apply_explicit_grt_role {actual_sdc} {
 if {![info exists ::env(OT_MM_INPUT_ANALYSIS_ROLE)]} {return}
 if {$::env(OT_MM_INPUT_ANALYSIS_ROLE) ne "GRT_FROM_FIXED_CLOCK_PLACE"} {error SC_UNKNOWN_MM_ANALYSIS_ROLE}
 if {[file tail $actual_sdc] ne "fixed_clock_PLACE_input.sdc" || $::ot_mm_stage ne "fixed_clock_PLACE_input.sdc"} {error SC_MM_UNEXPECTED_ACTUAL_SDC}
 set b [ord::get_db_block];set ff 0;set nodes 0;set clocks 0;set guides 0
 foreach i [$b getInsts] {
  set m [[$i getMaster] getName]
  if {[string match DFF* $m]} {
   incr ff
   if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} {error "SC_MM_UNFIXED_FF [$i getName]"}
   set t [$i findITerm CLK]
   if {$t eq "NULL" || [$t getNet] eq "NULL" || [[$t getNet] getSigType] ne "CLOCK"} {error "SC_MM_UNROOTED_FF [$i getName]"}
  }
  if {[string match sc_ck_* [$i getName]]} {
   incr nodes
   if {$m ne "BUFx24_ASAP7_75t_R" || [$i getPlacementStatus] ni {FIRM LOCKED COVER}} {error SC_MM_CLOCK_MODEL_MISMATCH}
  }
 }
 foreach n [$b getNets] {
  if {[$n getSigType] eq "CLOCK"} {incr clocks;if {[$n isSpecial]} {error SC_MM_EXCLUDED_CLOCK}}
  if {[$n getSigType] in {SIGNAL CLOCK}} {incr guides [llength [$n getGuides]]}
 }
 if {$ff!=42665 || $nodes!=2389 || $clocks!=2390 || $guides!=0} {error "SC_MM_INPUT_CONTEXT ff=$ff nodes=$nodes clocks=$clocks guides=$guides"}
 # Legacy enum means native GRT RC/sync role ONLY. Actual artifact stays PLACE.
 set ::ot_mm_stage "4_cts.sdc"
 puts "SC_EXPLICIT_MM_ROLE actual=$actual_sdc INPUT_STAGE=fixed_clock_PLACE analysis_role=nativeGRT legacy_enum=4_cts.sdc CTS_operation_credit=0 ff=$ff clock_nodes=$nodes clock_nets=$clocks initial_guides=$guides"
}
