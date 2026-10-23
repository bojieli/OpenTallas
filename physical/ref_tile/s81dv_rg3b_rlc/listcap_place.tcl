# Capture the used 17 bits of each list entry beside its SRAM read face.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set count 0
set f [open $::env(RESULTS_DIR)/rlc_placed.txt w]
foreach i [$b getInsts] {
 set n [string map {\\ {}} [$i getName]]
 if {![regexp {lf_pick_q\[([0-9]+)\]} $n -> bit]} continue
 set bank [expr {int($bit/136)}]
 set localbit [expr {$bit%136}]
 set x [expr {($bank==0?237.6:21.6)+($localbit%8)*1.08}]
 set y [expr {($bank==0?144.72:235.44)+int($localbit/8)*1.08}]
 $i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]
 $i setPlacementStatus FIRM
 puts $f [$i getName]
 incr count
}
close $f
puts "RLC_CAPTURE_PLACED $count"
if {$count != 272} {error "RLC expected 272 capture flops, found $count"}
