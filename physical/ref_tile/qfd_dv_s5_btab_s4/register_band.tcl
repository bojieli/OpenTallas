# Structural register floorplan: all 320 FFs, including select copies, in one N band.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set r [odb::dbRegion_create $b btab_capture_band]
odb::dbBox_create $r [expr {round(2.16*$dbu)}] [expr {round(176.4*$dbu)}] [expr {round(300.24*$dbu)}] [expr {round(213.84*$dbu)}]
set g [odb::dbGroup_create $r btab_capture_ff]
set cnt 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} continue
 if {![regexp {\$_DFF} [$i getName]]} continue
 if {[$i getGroup] ne "NULL"} {error "BTAB_BAND unexpected existing group [$i getName]"}
 $g addInst $i
 incr cnt
}
if {$cnt != 320} {error "BTAB_BAND expected all320 registers, got $cnt"}
puts "BTAB_BAND all320 registers in one full-width N band"
