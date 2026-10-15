read_db roundtrip.odb
source pdn_bbox_obs.tcl
set file [open expected_obs.txt]; set expected [string trim [read $file]]; close $file
set readback [[ord::get_db_block] findInst tap]
if {$expected ne [ot_pdn_bbox::obstructions [$readback getMaster]]} {error "route ODB detailed OBS changed"}
if {[[ord::get_db] findMaster OT_PDN_BBOX_qfd_xs_tap] ne "NULL"} {error "temporary alias persisted"}
check_power_grid -net VDD
check_power_grid -net VSS
puts ROUTE_ODB_DETAILED_OBS_IDENTICAL
