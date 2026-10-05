# DSROM q-element timing screens/routes (2026-10-03), frame C: the q-frame track-aligned macro hook, unchanged, then
# removal of the soft placement blockages RTL-MP leaves when it misses its own utilisation target (S_C1: four
# maxDensity-0 blockages over 387 x 63 um of free core pushed the global-placement density bound over 1.0, FLW-0024).
# The hook overrides RTL-MP's macro placement, so its blockages describe a placement that no longer exists.
source /src/physical/abi3/dsrom_qframe_C_trk_place.tcl
set ot_nblk 0
foreach b [[ord::get_db_block] getBlockages] { odb::dbBlockage_destroy $b; incr ot_nblk }
puts "OT_QTIMING_PLACE removed_rtlmp_blockages=$ot_nblk"
