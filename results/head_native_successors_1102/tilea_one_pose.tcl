# PREP ONLY. ROOT scope is required before native execution. No CTS/route/STA.
# IN is a read-only copy of the actual failed 4_cts.odb. OUT must be new.
foreach v {IN OUT CHECKS PG_HELPER} {if {![info exists ::env($v)]} {error "missing $v"}}
if {[file normalize $::env(IN)] eq [file normalize $::env(OUT)] || [file exists $::env(OUT)]} {error "refuse source/output overwrite"}
source [file join [file dirname [info script]] frozen_geometry.tcl]
read_db $::env(IN)
source $::env(PG_HELPER)
ot_pg_require_bound TILEA_ONE_POSE_INPUT
foreach n [[ord::get_db_block] getNets] {if {[$n getSigType] in {POWER GROUND}} {
 check_power_grid -net [$n getName] -error_file $::env(CHECKS).input_pg_[$n getName].rpt
}}
set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
set name {u_rrl_118/wire11650}; set i [$block findInst $name]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUFx16f_ASAP7_75t_R"} {error "TileA exact buffer/master missing"}
set expected {}; foreach z {359.586 138.510 360.774 138.780} {lappend expected [expr {round($z*$dbu)}]}
if {[hg_box [$i getBBox]] ne $expected} {error "TileA source is not the actual224.883 failing pose"}
set before [hg_state $name]; hg_write $::env(CHECKS).before $before
set status [$i getPlacementStatus]; set orient [$i getOrient]; set dnt [$i isDoNotTouch]
set dy [expr {round(-8.64*$dbu)}]
if {$dy % [expr {round(0.27*$dbu)}] || $dy % [expr {round(8.64*$dbu)}]} {error "native row/PG phase changed"}
lassign [$i getLocation] x y
# ODB refuses setLocation while FIRM/LOCKED. Restore the exact native status.
$i setPlacementStatus PLACED
$i setLocation $x [expr {$y+$dy}]
$i setPlacementStatus $status
if {[$i getOrient] ne $orient || [$i isDoNotTouch] != $dnt || [$i getPlacementStatus] ne $status} {error "selected buffer protection/orientation changed"}
set want {}; foreach z {359.586 129.870 360.774 130.140} {lappend want [expr {round($z*$dbu)}]}
if {[hg_box [$i getBBox]] ne $want} {error "selected buffer delta not exactly -8.64Y"}
check_placement -verbose
ot_pg_require_bound TILEA_ONE_POSE_OUTPUT
foreach n [$block getNets] {if {[$n getSigType] in {POWER GROUND}} {
 check_power_grid -net [$n getName] -error_file $::env(CHECKS).output_pg_[$n getName].rpt
}}
set after [hg_state $name]; hg_require_same $before $after; hg_write $::env(CHECKS).after $after
write_db $::env(OUT)
puts "TILEA_ONE_POSE_CHECKPOINT ONLY: legal placement command completed; no CLK/PG-contact/timing PASS. Fresh dump/image/LOOK and exact old guide/RC isolation required before separate qualifications."
