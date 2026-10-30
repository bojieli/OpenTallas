read_db /work/run/results/asap7/hbc_ot_s81_kp4_dchn/base/5_1_grt.odb
set b [ord::get_db_block]
set t [$b findBTerm rst_n]
set bps [$t getBPins]
if {[llength $bps]!=1} {error "expected one BPin"}
set bp [lindex $bps 0]
set boxes [$bp getBoxes]
if {[llength $boxes]!=1} {error "expected one reset box"}
set box [lindex $boxes 0]
if {[[$box getTechLayer] getName] ne "M5" || [$box xMin]!=108012 || [$box xMax]!=108036} {error "reset geometry changed"}
set layer [$box getTechLayer]
set status [$bp getPlacementStatus]
set x0 [expr {[$box xMin]-48}]; set y0 [$box yMin]
set x1 [expr {[$box xMax]-48}]; set y1 [$box yMax]
odb::dbBPin_destroy $bp
set bp [odb::dbBPin_create $t]
$bp setPlacementStatus $status
odb::dbBox_create $bp $layer $x0 $y0 $x1 $y1
write_db /work/run/results/asap7/hbc_ot_s81_kp4_dchn/base/5_1_grt.odb
foreach name {clk rst_n} {set t [$b findBTerm $name]; foreach bp [$t getBPins] {foreach box [$bp getBoxes] {puts "CANDIDATE_PIN $name [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}}
