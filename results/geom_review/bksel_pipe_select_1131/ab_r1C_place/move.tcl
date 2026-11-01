read_db /work/reset_move/3_place_input.odb
set b [ord::get_db_block]
set states [dict create]
foreach i [$b getInsts] {dict set states [$i getName] [list [$i getLocation] [$i getOrient] [[$i getMaster] getName]]}
set src [$b findInst {u_c.rst_s\[1\]$_DFF_PN0_}]
if {$src eq "NULL"} {error "reset delivery FF absent"}
if {[$src getPlacementStatus] ne "PLACED"} {error "unexpected reset delivery placement status"}
$src setLocation 167508 82890
set changed {}
foreach i [$b getInsts] {
 set before [dict get $states [$i getName]]
 set after [list [$i getLocation] [$i getOrient] [[$i getMaster] getName]]
 if {$before ne $after} {lappend changed [$i getName]}
}
if {[llength $changed] != 1 || [lindex $changed 0] ne [$src getName]} {error "unexpected extra movement $changed"}
check_placement -verbose
write_db /work/run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r1_1131/base/3_place.odb
set f [open /work/reset_move/receipt.txt w]
puts $f "ONE_EXISTING_RESET_FF_MOVE PASS changed=$changed location=167508,82890 orientation=MX no_other_moves=1 cells=[llength [$b getInsts]] nets=[llength [$b getNets]]"
close $f
