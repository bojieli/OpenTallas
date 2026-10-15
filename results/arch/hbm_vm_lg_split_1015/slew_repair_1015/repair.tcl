# Same-edge INV drive repair; source-state, clocks, constraints and ports unchanged.
# The caller sets exact source net; this addresses one measured return capture.
set block [ord::get_db_block]
set net [$block findNet $::ot_lg_repair_net]
if {$net eq "NULL"} { error "LG repair: source net absent $::ot_lg_repair_net" }
set drivers {}; set sinks {}
foreach it [$net getITerms] {
 if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}
 if {[$it getIoType] eq "INPUT"} {lappend sinks $it}
}
if {[llength $drivers] != 1 || [llength $sinks] != 2} {
 error "LG repair: expected one driver/two capture sinks on $::ot_lg_repair_net"
}
set inst [[lindex $drivers 0] getInst]
set old [$inst getMaster]
if {![regexp {^INVx[12]_ASAP7_75t_R$} [$old getName]]} {
 error "LG repair: unexpected driver [$old getName]"
}
set new [[ord::get_db] findMaster INVx4_ASAP7_75t_R]
if {$new eq "NULL"} {error "LG repair: missing INVx4 master"}
set delta [expr {([$new getWidth]*[$new getHeight]-[$old getWidth]*[$old getHeight])/1.0e6}]
puts "LG_SLEW_REPAIR net=$::ot_lg_repair_net inst=[$inst getName] old=[$old getName] new=[$new getName] same_edge=1 delta_area_um2=$delta"
resize_cell [$inst getName] INVx4_ASAP7_75t_R
# Legalize the actual wider standard cell before routing; no CTS/phase change.
detailed_placement
check_placement -verbose
