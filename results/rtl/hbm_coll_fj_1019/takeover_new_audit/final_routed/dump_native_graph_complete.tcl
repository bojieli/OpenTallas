read_db $::env(AUDIT_ODB)
set b [ord::get_db_block]
set f [open $::env(CELL_GRAPH) w]
foreach i [$b getInsts] {foreach t [$i getITerms] {
 if {[$t getSigType] in {POWER GROUND}} continue
 set n [$t getNet];set nn ""
 if {$n eq "NULL" || $n eq ""} {if {[$t getIoType] ne "OUTPUT"} {error "UNCONNECTED_INPUT [$i getName]/[[$t getMTerm] getName]"};set nn "__OPEN_OUTPUT__[$i getName]/[[$t getMTerm] getName]"} else {set nn [$n getName]}
 puts $f "[[$i getMaster] getName]\t[$i getName]\t[[$t getMTerm] getName]\t$nn"
}}
close $f
set f [open $::env(PORT_GRAPH) w]
foreach t [$b getBTerms] {if {[$t getSigType] in {POWER GROUND}} continue;set n [$t getNet];if {$n eq "NULL" || $n eq ""} {error UNCONNECTED_BTERM};puts $f "[$t getIoType]\t[$t getName]\t[$n getName]"}
close $f
puts FJ_NATIVE_GRAPH_DUMP_COMPLETE
