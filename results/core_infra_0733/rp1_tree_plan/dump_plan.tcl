read_db /work/shared_rp1.odb
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /work/technology.tsv w];puts $f "DBU $u"
set r [$b getCoreArea];puts $f [list CORE [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
foreach r [$b getRows] {set z [$r getBBox];puts $f [list ROW [$z xMin] [$z yMin] [$z xMax] [$z yMax] [[$r getSite] getWidth] [$r getOrient]]}
foreach name {BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R} {
 set m [[ord::get_db] findMaster $name];puts $f [list MASTER $name [$m getWidth] [$m getHeight]]
}
foreach i [$b getInsts] {
 if {[string match mp_isl* [$i getName]]} continue
 if {![[$i getMaster] isBlock] && [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
 set z [$i getBBox];puts $f [list OBSTACLE [$i getName] [expr {[[$i getMaster] isBlock] ? "macro" : "fixed"}] [$z xMin] [$z yMin] [$z xMax] [$z yMax]]
}
close $f
