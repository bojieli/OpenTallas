# Four complete banks, seventeen full-depth sector columns per bank.
source /src/physical/common/ot_macro_track_snap.tcl
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set maxw 0.0
set maxh 0.0
set cells {}
foreach inst [$block getInsts] {
    set name [[$inst getMaster] getName]
    if {$name ni {ot_dsrom_window_column_128 ot_dsrom_window_column_256}} {continue}
    # Flattened instance names escape hierarchy brackets (g_bank\[0\].g_col\[0\]...); match without them.
    set iname [string map {\\ {}} [$inst getName]]
    if {![regexp {g_bank\[([0-3])\].*g_col\[([0-9]+)\]} $iname unused b k]} {
        error "unexpected WINDOW column instance [$inst getName]"
    }
    set maxw [expr {max($maxw,double([[$inst getMaster] getWidth])/$dbu)}]
    set maxh [expr {max($maxh,double([[$inst getMaster] getHeight])/$dbu)}]
    lappend cells [list $inst $b $k]
}
if {[llength $cells]!=68} {error "WINDOW full shape requires 68 columns, found [llength $cells]"}
foreach cell $cells {
    lassign $cell inst b k
    set x [expr {100.0+($b%2)*900.0+($k%4)*($maxw+32.0)}]
    set y [expr {100.0+int($b/2)*900.0+int($k/4)*($maxh+32.0)}]
    ot_mts::place $inst $x $y R0 LOCKED
}
ot_mts::assert_on_track -label window_full128_columns
