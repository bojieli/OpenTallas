# Installed OpenDB dbBox_destroy leaves a linked region boundary in this case.
# Preserve actual groups, membership and modeled union while recreating region.
set ot_fast_block [ord::get_db_block]
set ot_fast_region [$ot_fast_block findRegion cp_body]
set ot_fast_group [$ot_fast_block findGroup cp_body]
if {$ot_fast_region eq "NULL" || $ot_fast_group eq "NULL"} {error "Missing source-owned CP body"}
set ot_fast_expected {{17280 17280 60480 56160} {22464 56160 60480 60480} {60480 17280 64800 64800} {17280 60480 60480 64800}}
set ot_fast_boxes {}
foreach ot_fast_box [$ot_fast_region getBoundaries] {lappend ot_fast_boxes [list [$ot_fast_box xMin] [$ot_fast_box yMin] [$ot_fast_box xMax] [$ot_fast_box yMax]]}
if {[lsort -unique $ot_fast_boxes] ne [lsort $ot_fast_expected]} {error "Unexpected FAST union: $ot_fast_boxes"}
if {[llength $ot_fast_boxes]!=4} {
 if {[llength $ot_fast_boxes]!=5 || [llength [lsearch -all -exact $ot_fast_boxes {17280 17280 60480 56160}]]!=2} {error "Unexpected duplicate boundary"}
 set ot_fast_members {}
 foreach ot_fast_inst [$ot_fast_group getInsts] {lappend ot_fast_members [$ot_fast_inst getName]}
 $ot_fast_region removeGroup $ot_fast_group
 odb::dbRegion_destroy $ot_fast_region
 set ot_fast_region [odb::dbRegion_create $ot_fast_block cp_body]
 $ot_fast_region setRegionType EXCLUSIVE
 $ot_fast_region addGroup $ot_fast_group
 foreach ot_fast_box $ot_fast_expected {odb::dbBox_create $ot_fast_region {*}$ot_fast_box}
 set ot_fast_after {}
 foreach ot_fast_inst [$ot_fast_group getInsts] {lappend ot_fast_after [$ot_fast_inst getName]}
 if {[lsort $ot_fast_members] ne [lsort $ot_fast_after]} {error "CP body membership changed"}
}
if {[llength [$ot_fast_region getBoundaries]]!=4} {error "FAST region must serialize four unique boundaries"}
puts "OT_FAST_UNIQUE_REGIONS boxes=4 body_cells=[llength [$ot_fast_group getInsts]] union_um2=2235.75552"
