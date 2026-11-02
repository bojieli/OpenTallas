# Owned Cap WEST2 pure-routing candidate; first PRE after original routed DB/libs/SDC load.
source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error CAP_STRICT_PG_REQUIRED}
ot_pg_native_birth_begin /work/nativepgbirth.so
set cb [ord::get_db_block]
# Preserve resolved normal antenna policy; this private no-birth diagnostic refuses
# any eligible diode master across EVERY actually loaded dbLib before analysis.
set antenna_masters {};set library_inventory {}
foreach lib [[ord::get_db] getLibs] {
 set count 0
 foreach master [$lib getMasters] {
  incr count
  if {[$master getType] eq "CORE_ANTENNACELL"} {lappend antenna_masters [list [$lib getName] [$master getName]]}
 }
 lappend library_inventory [list [$lib getName] $count]
}
if {![llength $library_inventory]} {error CAP_EMPTY_ACTUAL_LIBRARY_INVENTORY}
if {[llength $antenna_masters]} {error "CAP_NO_BIRTH_DIAGNOSTIC_HAS_ELIGIBLE_DIODE $antenna_masters"}
puts "CAP_ACTUAL_ALL_LIB_ANTENNA_INVENTORY zero eligible CORE_ANTENNACELL; libraries $library_inventory; normalpolicy SKIP_ANTENNA_REPAIR=$::env(SKIP_ANTENNA_REPAIR)"
set ::cap_targets {_27646_ wire17963}
set ::cap_expected_nets [lsort {net19290 _14198_ _14199_ net19400 _14200_ net17964}]
# All three source spacers overlap only the reviewed destination bboxes.
set ::cap_spacers {FILLER_186_604 FILLER_276_605 FILLER_276_627}
set ::cap_inst_before [dict create]
foreach i [$cb getInsts] {dict set ::cap_inst_before [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]}
foreach name $::cap_spacers {
 set i [$cb findInst $name];if {$i eq "NULL" || [[$i getMaster] getType] ne "CORE_SPACER"} {error CAP_EXACT_SPACER_REQUIRED}
 if {![llength [[$i getMaster] getMTerms]]} {error CAP_EMPTY_PG_SPACER}
 foreach mt [[$i getMaster] getMTerms] {if {[$mt getSigType] ni {POWER GROUND}} {error CAP_SIGNAL_SPACER_REFUSED}}
 odb::dbInst_destroy $i
}
set seen [dict create]
foreach i [$cb getInsts] {
 set n [$i getName];set v [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
 if {![dict exists $::cap_inst_before $n] || $v ne [dict get $::cap_inst_before $n]} {error "CAP_SPACER_NON_TARGET_CHANGE $n"}
 dict set seen $n 1
}
set removed {};dict for {n v} $::cap_inst_before {if {![dict exists $seen $n]} {lappend removed $n}}
if {[lsort $removed] ne [lsort $::cap_spacers]} {error CAP_EXACT_DELETION_SET}
set pa [ot_native_pg_audit];if {[dict get $pa creates] || [dict get $pa swaps]} {error CAP_UNEXPECTED_BIRTH_OR_SWAP}
source /work/clk_freeze.tcl
# Full original physical clock wire dump; baseline constraints are not replaced by routed SPEF estimates.
ot_clk_dump $::env(RESULTS_DIR)/clock_original.tsv cap_original
# Full non-target wire tokens are preserved (includes every actual propagated reset SIGNAL net).
set ::cap_wire_before [dict create];set ::cap_net_flags [dict create]
foreach n [$cb getNets] {
 dict set ::cap_net_flags [$n getName] [list [$n getSigType] [$n isDoNotTouch]]
 if {[$n getSigType] in {POWER GROUND} || [$n getName] in $::cap_expected_nets} continue
 dict set ::cap_wire_before [$n getName] [ot_clk_wire_tokens $n]
 $n setDoNotTouch 1
}
# No native resizing is permitted anywhere in this checkpoint, including inherited hooks.
foreach c {repair_design repair_timing repair_tie_fanout buffer_ports resize repair_clock_nets} {
 if {[llength [info commands ::$c]]} {rename ::$c ::cap_disabled_$c;proc ::$c args {error CAP_ROUTING_ONLY_RESIZER_REFUSED}}
}
puts "CAP_PRE PASS exact3spacers; nativePG0; all non-target wires/real reset sigtypes snapshotted; no resizer"
