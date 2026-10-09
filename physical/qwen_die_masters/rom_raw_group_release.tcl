source /src/physical/qwen_die_masters/rom_cap_release.tcl
set b [ord::get_db_block]
set f $::env(RESULTS_DIR)/ot_rom_raw_group_fixed.txt
set fh [open $f r]
foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$b findInst $n]
    if {$i eq "NULL" || $i eq ""} {error "Missing fixed raw stage $n"}
    $i setPlacementStatus PLACED
}
close $fh
