set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /work/anchor_targets.tsv r]
set count 0
while {[gets $f line]>=0} {
 set a [split $line "\t"]
 set i [$b findInst [lindex $a 0]]
 if {$i eq "NULL"} {error "missing anchor [lindex $a 0]"}
 set m [$i getMaster]
 set x [expr {round([lindex $a 1]*$dbu-[$m getWidth]/2.0)}]
 set y [expr {round([lindex $a 2]*$dbu-[$m getHeight]/2.0)}]
 $i setLocation $x $y
 $i setPlacementStatus PLACED
 incr count
}
close $f
puts "CODEX_ANCHOR targets=$count"
