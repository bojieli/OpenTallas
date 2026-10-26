# PATH-KV-ASTK8 10-26: kv3_astk POST_CTS (with SKIP_CTS_REPAIR_TIMING = 1).  ORFS cts.tcl repairs hold BEFORE the
# POST_CTS hook, i.e. on a tree that the hook then changes (ASTK7: 9172 hold buffers on the pre-affinity tree; HBM
# ELEM 10-24 gq_land same lesson).  Order here: (1) reconnect the dedicated face root directly to ck, (2) leaf_affinity.tcl re-hangs zero-logic pairs
# with face-tree anchors kept, (3) astk_tap_target.tcl measures face-tree delay to the 250 / 202.5 contract, then ONE repair on
# the final tree (repair_timing_helper, the ORFS cts.tcl call with the kit margins), detailed placement, check.
# Keep the dedicated interface root directly at ck after CTS. TritonCTS builds
# a root tree for zone taps and otherwise places this root behind that tree too,
# adding ~80-100 ps to every face sink. This parallel branch is synchronous and
# receives propagated timing from the same physical clock port.
uplevel #0 {
set er_blk [ord::get_db_block]
set er_inst [$er_blk findInst ot_face_root]
set er_port [$er_blk findBTerm ck]
if {$er_inst eq "NULL" || $er_port eq "NULL"} { error "ASTK_EARLY_FACE_ROOT missing root/ck" }
set er_in [$er_inst findITerm A]
$er_in disconnect
$er_in connect [$er_port getNet]
puts "ASTK_EARLY_FACE_ROOT connected ot_face_root/A directly to ck"
}
estimate_parasitics -placement
source /work/leaf_affinity.tcl
source /work/astk_tap_target.tcl
estimate_parasitics -placement
repair_timing_helper
detailed_placement
check_placement -verbose
estimate_parasitics -placement
# This hook creates delay/repair cells after the floorplan's initial PG pass.
global_connect
