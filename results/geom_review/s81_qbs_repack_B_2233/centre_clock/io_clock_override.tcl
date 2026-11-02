# DISABLED CANDIDATE ONLY: source after generated io.tcl in a new own kit.
# Same ck BTerm/net; physical contract changes and all parent references move together.
set cb [[ord::get_db_block] findBTerm {ck}]
if {$cb eq "NULL" || $cb eq ""} {error "centre clock ck BTerm missing"}
foreach bp [$cb getBPins] {odb::dbBPin_destroy $bp}
set bp [odb::dbBPin_create $cb]
$bp setPlacementStatus FIRM
set u [[ord::get_db_block] getDbUnitsPerMicron]
odb::dbBox_create $bp [[ord::get_db_tech] findLayer M5] [expr {int(round(323.988*$u))}] [expr {int(round(330.972*$u))}] [expr {int(round(324.036*$u))}] [expr {int(round(331.452*$u))}]
