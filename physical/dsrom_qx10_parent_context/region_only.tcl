# Retained PDN continuation: canonical doInitialPlace removes its empty core
# component. Bypass only the earlier broken uniform-density query. No cells,
# groups, region geometry, data/clock connections or protection are modified.
if {[info exists ::env(PLACE_DENSITY_LB_ADDON)] && $::env(PLACE_DENSITY_LB_ADDON) ne ""} {
    error "region-only placement must not initialize the empty core in density prequery"
}
if {$::env(PLACE_DENSITY)!=0.6} {error "region-only placement changed original density"}
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set expected_groups {qx10_parent 211245 qx10_engine 37202}
set groups_seen {}
foreach group [$block getGroups] {
    set name [$group getName]
    if {![dict exists $expected_groups $name]} {error "unexpected placement group $name"}
    set members [llength [$group getInsts]]
    if {$members != [dict get $expected_groups $name]} {error "retained group membership changed: $name"}
    lappend groups_seen $name
}
if {[lsort $groups_seen] ne [lsort [dict keys $expected_groups]]} {error "both real groups must survive"}
set expected_regions {
    qx10_parent {2.16 2.16 525.096 237.60}
    qx10_engine {527.256 44.55 1038.096 195.21}
}
foreach region [$block getRegions] {
    set name [$region getName]
    if {![dict exists $expected_regions $name] || [$region getRegionType] ne "EXCLUSIVE"} {
        error "retained fence changed: $name"
    }
    set bounds [$region getBoundaries]
    if {[llength $bounds]!=1} {error "fence has unexpected geometry"}
    set box [[lindex $bounds 0] getBox]
    set coords [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
    set expected {}
    foreach x [dict get $expected_regions $name] {lappend expected [expr {round($x*$units)}]}
    if {$coords ne $expected} {error "retained fence bounds changed: $name $coords vs $expected"}
}
set unassigned 0;set movable 0;set macros 0
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {[$master isBlock]} {incr macros;continue}
    if {[regexp {SPACER|WELLTAP} [$master getType]] || [$inst isFixed]} {continue}
    incr movable
    if {[$inst getGroup] eq "NULL"} {incr unassigned}
}
if {$macros!=4 || $movable!=248447 || $unassigned!=0} {error "retained placement inventory changed"}
puts "OT_QX10_REGION_ONLY_INVENTORY groups=2 parent=211245 engine=37202 movable=$movable unassigned=$unassigned macros=$macros density=0.6 all_fences_unchanged=1"
