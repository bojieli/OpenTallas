set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ms {}
foreach m [$b getInsts] {if {[[$m getMaster] isBlock]} {lappend ms $m}}
if {[llength $ms]!=1} {error "store141 expected exactly one native SRAM"}
set m [lindex $ms 0]
$m setOrient R0
$m setLocation [expr {round(18.036*$dbu)}] [expr {round(25.92*$dbu)}]
$m setPlacementStatus FIRM
puts "STORE141_MACRO [$m getName] x=18.036 y=25.92"
