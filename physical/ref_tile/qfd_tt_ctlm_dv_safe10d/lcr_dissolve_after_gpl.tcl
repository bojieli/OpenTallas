# QW-TTC8 10-20 (CTLM8 safe8u / safe8bu, pre_dpl_extra): the lp_cone_regions core / hr partition is a GLOBAL-PLACEMENT
# assignment.  Root cause of the safe8t / safe8bt DPL FAIL (cts.log 3_5): 3_4 repair_design inserted 12,828 / 11,633
# buffers (7,750 slew + 625 cap violations) that belong to NO group; OpenDP forbids un-grouped cells inside a region,
# so every repair buffer placed beside its cone (deep inside ot_lcr_core / ot_lcr_hr, 4-10 % std util) had to travel to
# the pin bands: 27,582 illegal cells, 15,992 stuck -> 9,806 edge-spacing / 226 padding / 13,686 overlaps, then
# improve_placement crashed (detail_place.tcl:42 bad optional access).  CTS / GRT repair cells would repeat it.
# Fix: after GPL + resize the partition is encoded in the placement itself (every owned cell sits in its region box);
# dissolve the ot_lcr groups / regions here so DPL only legalises locally and later repair / CTS cells have a legal home.
# Report how many un-grouped movable cells sit inside each region box (the population that failed) before dissolving.
set ot_lcd_block [ord::get_db_block]
set ot_lcd_dbu [$ot_lcd_block getDbUnitsPerMicron]
set ot_lcd_boxes {}
foreach r [$ot_lcd_block getRegions] {
    if {![string match ot_lcr_* [$r getName]]} continue
    foreach b [$r getBoundaries] {lappend ot_lcd_boxes [list [$r getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}
}
set ot_lcd_in [dict create]
set ot_lcd_free 0
foreach inst [$ot_lcd_block getInsts] {
    if {[[$inst getMaster] isBlock] || [$inst isFixed]} continue
    if {![string match CORE* [[$inst getMaster] getType]]} continue
    if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} continue
    lassign [$inst getLocation] x y
    set hit ""
    foreach bx $ot_lcd_boxes {
        lassign $bx n x0 y0 x1 y1
        if {$x >= $x0 && $x < $x1 && $y >= $y0 && $y < $y1} {set hit $n; break}
    }
    if {$hit eq ""} {incr ot_lcd_free} else {dict incr ot_lcd_in $hit}
}
puts "OT_LCD un-grouped movable cells inside regions: [dict get [dict merge {ot_lcr_core 0 ot_lcr_hr 0} $ot_lcd_in] ot_lcr_core] core / [dict get [dict merge {ot_lcr_core 0 ot_lcr_hr 0} $ot_lcd_in] ot_lcr_hr] hr; outside (pin bands) $ot_lcd_free"
set ot_lcd_ng 0; set ot_lcd_nr 0; set ot_lcd_members 0
foreach g [$ot_lcd_block getGroups] {
    if {![string match ot_lcr_* [$g getName]]} continue
    set m [$g getInsts]
    incr ot_lcd_members [llength $m]
    foreach i $m {$g removeInst $i}
    odb::dbGroup_destroy $g
    incr ot_lcd_ng
}
foreach r [$ot_lcd_block getRegions] {
    if {![string match ot_lcr_* [$r getName]]} continue
    odb::dbRegion_destroy $r
    incr ot_lcd_nr
}
if {$ot_lcd_ng != 2 || $ot_lcd_nr != 2} {error "OT_LCD expected 2 ot_lcr groups / regions, found $ot_lcd_ng / $ot_lcd_nr"}
puts "OT_LCD PASS dissolved $ot_lcd_ng groups / $ot_lcd_nr regions ($ot_lcd_members members keep their GPL region placement)"
