# Only cx successor: existing captures remain at ROM pins. Raw onehot groups
# are near their three south/two north banks; expansion and return relay have
# separate bounded positions toward the middle logic band. FIRM during GPL,
# released before DPL; no frame, clock, or IO budget changes.
source /src/physical/qwen_die_masters/rom_cap_at_pins.tcl
set ot_raw_blk [ord::get_db_block]
set ot_raw_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_raw_f [open $::env(RESULTS_DIR)/ot_rom_raw_group_fixed.txt w]
set ot_raw_n 0
set ot_raw_words 0
foreach i [$ot_raw_blk getInsts] {
    set n [string map {"\\" ""} [$i getName]]
    if {![regexp {g_pair\[([01])\]\.g_raw_group\.u_raw\.(raw_s|raw_n|gs|gn|rs|rn)\[([0-9]+)\]} $n _ pair stage bit]} continue
    if {![string match DFF* [[$i getMaster] getName]]} continue
    set y0 [dict get {raw_s 230.04 raw_n 1060.02 gs 340.2 gn 950.04 rs 500.04 rn 780.03} $stage]
    set w [expr {double([[$i getMaster] getWidth])/$ot_raw_dbu}]
    set h [expr {double([[$i getMaster] getHeight])/$ot_raw_dbu}]
    set x [expr {30.0+$pair*140.0+($bit%32)*($w+0.108)}]
    set y [expr {$y0+int($bit/32)*($h+0.27)}]
    $i setLocation [expr {round($x*$ot_raw_dbu)}] [expr {round($y*$ot_raw_dbu)}]
    $i setPlacementStatus FIRM
    puts $ot_raw_f [$i getName]
    incr ot_raw_n
    if {$stage eq "raw_s" || $stage eq "raw_n"} {incr ot_raw_words}
}
close $ot_raw_f
puts "OT_RAW_GROUP fixed $ot_raw_n stage registers including $ot_raw_words raw bank-group bits"
if {$ot_raw_words != 1024} {error "OT_RAW_GROUP expected full2columns x2groups x256bit raw registers"}
