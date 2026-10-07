set ::env(MAKE_TRACKS) /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
read_db /baseline/results/asap7/opentallas_ot_dsrom_reindex_parent_physctx_margin_asap7_reindex_parent_margin/base/2_1_floorplan.odb
source /check/place_fixed_20261007.tcl
# Test the real full-shape database with stale placed locations: cyclically permute
# the legal locations, as an earlier macro placer is permitted to do.
set coords {}
foreach inst $macros {lappend coords [$inst getLocation]}
set i 0
foreach inst $macros {lassign [lindex $coords [expr {($i+1)%16}]] x y; $inst setPlacementStatus PLACED; $inst setLocation $x $y; incr i}
if {![catch {source /src/physical/dsrom_reindex_parent/place.tcl} why]} {error "original unexpectedly passed stale-placement test"}
puts "EXPECTED_ORIGINAL_FAILURE $why"
source /check/place_fixed_20261007.tcl
puts "PASS_REINDEX_PLACE_FULLSHAPE macros=$count"
exit
