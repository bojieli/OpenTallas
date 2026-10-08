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
    set half -1
    regexp {g_half\[([01])\]} $iname unused half
    lappend cells [list $inst $b $k $half]
}
set split128 [expr {[llength $cells]==132}]
if {[llength $cells]!=68 && !$split128} {error "WINDOW full shape requires 68 or 132 columns, found [llength $cells]"}
# rtl_macro_placer has already placed these columns: release them so the explicit grid does not clash with its result
foreach cell $cells { [lindex $cell 0] setPlacementStatus UNPLACED }
foreach cell $cells {
    lassign $cell inst b k half
    if {$split128} {
        if {$k<16 && $half<0} {error "split128 payload half missing: [$inst getName]"}
        set slot [expr {$k==16 ? 32 : 2*$k+$half}]
        set bankpitch [expr {200.0+6*max($maxw,$maxh)+5*32.0}]
        set x [expr {100.0+($b%2)*$bankpitch+($slot%6)*($maxw+32.0)}]
        set y [expr {100.0+int($b/2)*$bankpitch+int($slot/6)*($maxh+32.0)}]
        ot_mts::place $inst $x $y R0 LOCKED
        continue
    }
    set x [expr {100.0+($b%2)*900.0+($k%4)*($maxw+32.0)}]
    set y [expr {100.0+int($b/2)*900.0+int($k/4)*($maxh+32.0)}]
    ot_mts::place $inst $x $y R0 LOCKED
}
ot_mts::assert_on_track -label window_full128_columns
