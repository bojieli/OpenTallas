read_db /work/input.odb
load /work/nativepgbirth.so Nativepgbirth
set b [ord::get_db_block]; set db [$b getDataBase]
set buf NULL
foreach l [$db getLibs] {foreach m [$l getMasters] {if {[$m getName] eq "BUFx2_ASAP7_75t_R"} {set buf $m}}}
if {$buf eq "NULL"} {error NO_NATIVE_BUFFER}
set lib [$buf getLib]
proc state {b} {
 set rows {}
 foreach i [$b getInsts] {
  set ts {};foreach t [$i getITerms] {set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};lappend ts [list [[$t getMTerm] getName] $nn]}
  lappend rows [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [lsort $ts]]
 }
 return [lsort $rows]
}
set mode $::env(PG_NEG)
set expected ""
if {$mode eq "ambiguous"} {
 set n [odb::dbNet_create $b OT_WRONG_VDD];$n setSigType POWER
 odb::dbGlobalConnect_create $n NULL {.*} {^VDD$}
 set expected *AMBIGUOUS_DOMAIN*
} elseif {$mode eq "regional"} {
 set r [odb::dbRegion_create $b OT_PG_REGION]
 odb::dbGlobalConnect_create [$b findNet VDD] $r {.*} {^VDD$}
 set expected *UNSUPPORTED_RULE_CONTEXT*
} elseif {$mode eq "signal_rule"} {
 odb::dbGlobalConnect_create [$b findNet VDD] NULL {.*} {^A$}
 set expected *RULE_SIGNAL_PIN*
} elseif {$mode eq "existing_wrong_domain" || $mode eq "protected_unbound"} {
 set i [odb::dbInst_create $b $buf OT_EXISTING_BAD]
 if {$mode eq "existing_wrong_domain"} {
  set n [odb::dbNet_create $b OT_WRONG_VDD];$n setSigType POWER
  [$i findITerm VDD] connect $n
  [$i findITerm VSS] connect [$b findNet VSS]
 } else {$i setDoNotTouch true}
 set expected *AUDIT*
}
if {$expected ne ""} {
 set before [state $b]
 if {![catch {ot_native_pg_install [$db getId] [$b getId]} err] || ![string match $expected $err]} {error "NEGATIVE_NOT_REJECTED $mode $err"}
 if {$before ne [state $b]} {error "NEGATIVE_MUTATED_CONTEXT $mode"}
 puts "NATIVE_PG_NEGATIVE_PASS $mode $err UNCHANGED"
} elseif {$mode eq "unknown_new_master" || $mode eq "swap_wrong_role"} {
 if {$mode eq "unknown_new_master"} {
  set m [odb::dbMaster_create $lib OT_BAD_MASTER]
  odb::dbMTerm_create $m VDDX INOUT POWER
  odb::dbMTerm_create $m VSS INOUT GROUND
  $m setFrozen
 } else {
  set used [dict create];foreach i [$b getInsts] {dict set used [[$i getMaster] getName] 1}
  set m NULL
  foreach candidate [$lib getMasters] {
   if {[string match BUFx*_ASAP7_75t_R [$candidate getName]] && ![dict exists $used [$candidate getName]]} {set m $candidate;break}
  }
  if {$m eq "NULL"} {error NO_UNUSED_NATIVE_MASTER}
 }
 ot_native_pg_install [$db getId] [$b getId]
 try {
  if {$mode eq "unknown_new_master"} {
   set before [state $b]
   if {![catch {odb::dbInst_create $b $m OT_BAD_NEW} err] || ![string match *UNKNOWN_DOMAIN* $err]} {error "NEGATIVE_NOT_REJECTED $mode $err"}
   # Native create has allocated the rejected cell; no analysis is requested.
   set i [$b findInst OT_BAD_NEW]
   if {$i eq "NULL"} {error NEGATIVE_BAD_CELL_NOT_PRESENT}
   foreach t [$i getITerms] {if {[$t getNet] ne "NULL"} {error NEGATIVE_PARTIAL_BIND}}
   ot_native_pg_uninstall; odb::dbInst_destroy $i
   if {$before ne [state $b]} {error NEGATIVE_CHANGED_EXISTING}
  } else {
   set i [odb::dbInst_create $b $buf OT_GOOD_NEW]
   set before [state $b]
   set bad_pg [$m findMTerm VDD]; $bad_pg setSigType GROUND
   if {![catch {$i swapMaster $m} err] || ![string match *PIN_ROLE* $err]} {error "NEGATIVE_NOT_REJECTED $mode $err"}
   $bad_pg setSigType POWER
   if {$before ne [state $b]} {error NEGATIVE_MASTER_MUTATED}
   puts "NATIVE_PG_NEGATIVE_AUDIT [ot_native_pg_audit]"
  }
  puts "NATIVE_PG_NEGATIVE_PASS $mode $err UNCHANGED_EXISTING"
 } finally {ot_native_pg_uninstall}
} else {error UNKNOWN_NEGATIVE_MODE}
