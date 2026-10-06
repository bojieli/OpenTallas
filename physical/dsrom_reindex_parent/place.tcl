# Sixteen aligned list macros adjacent to the unchanged KC8 control slot.
# Geometry only. Actual clock/macro arcs and every data interface stay timed.
source [file join /src physical/common/ot_macro_track_snap.tcl]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set count 0
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} {continue}
    if {![regexp {g_b\[([0-9]+)\].*u_macro} [$inst getName] ignored i]} {error "unrecognized list macro [$inst getName]"}
    set x [expr {4.0+($i%4)*182.096}]
    set y [expr {314.164+($i/4)*37.7}]
    ot_mts::place $inst $x $y R0 LOCKED
    incr count
}
if {$count!=16} {error "fullshape requires sixteen list macros, saw$count"}
ot_mts::assert_on_track -label dsrom_reindex_parent
