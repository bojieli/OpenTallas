# Native launch repair against source-owned v2, no clock/SDC/logic epoch change.
# Each measured affected FF-hold slack is79.6..81.6ps; one surplus internal
# HB2 contributes~27psFF/~38psTT. Required boundary outhold pads remain.
set block [ord::get_db_block]
foreach {name expected_source expected_sink} {
 hold12379 {u_core.hrq[5]$_SDFF_PN0_} _047692_
 hold12384 {u_core.hrq[146]$_SDFF_PN0_} _047755_
 hold12417 {u_core.hrq[214]$_SDFF_PN0_} _047836_
} {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne "HB2xp67_ASAP7_75t_R"} {error "CTNL2 launch ECO: bad master $name"}
 set input NULL;set output NULL
 foreach pin [$inst getITerms] {
  set d [[$pin getMTerm] getIoType]
  if {$d eq "INPUT"} {set input $pin}
  if {$d eq "OUTPUT"} {set output $pin}
 }
 set upstream [$input getNet];set downstream [$output getNet];set srcs {};set dsts {}
 foreach pin [$upstream getITerms] {if {$pin ne $input && [[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend srcs [[$pin getInst] getName]}}
 foreach pin [$downstream getITerms] {if {$pin ne $output} {lappend dsts [[$pin getInst] getName]}}
 set source_name [lindex $srcs 0]
 regsub -all {\\([\[\]])} $source_name {\1} source_name
 if {[llength $srcs] != 1 || [llength $dsts] != 1 || $source_name ne $expected_source || [lindex $dsts 0] ne $expected_sink || [llength [$downstream getBTerms]]} {error "CTNL2 launch ECO connectivity $name: $srcs -> $dsts"}
 foreach pin [$downstream getITerms] {if {$pin ne $output} {$pin connect $upstream}}
 odb::dbInst_destroy $inst;odb::dbNet_destroy $downstream
 puts "CTNL2_OUTPUT_ECO bypassed $name, preserving FF/inverter/boundary pad"
}
set cleared 0
foreach net [$block getNets] {set wire [$net getWire];if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr cleared}}
puts "CTNL2_OUTPUT_ECO invalidated $cleared stale dbWires before fresh route"
