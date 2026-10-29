# Kit-local structural placement repair. Synchronous reset boundary relay is
# timed and must stay beside its N-face input; original face hook skipped rst_n.
set xb [ord::get_db_block]
set xi [$xb findInst {u_fcore.rst_q$_DFF_PN0_}]
if {$xi eq "NULL" || $xi eq ""} { error "XCAL_RESET_ANCHOR missing expected reset relay" }
set xu [[ord::get_db_tech] getDbUnitsPerMicron]
$xi setLocation [expr {round(120.015*$xu)}] [expr {round(218.700*$xu)}]
$xi setOrient R0
$xi setPlacementStatus FIRM
puts "XCAL_RESET_ANCHOR [$xi getName] [$xi getLocation]"
