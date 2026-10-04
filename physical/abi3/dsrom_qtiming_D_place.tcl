# DSROM q-element routes on frame D (2026-10-04, route Z3b): the q-frame D track-aligned macro hook (510.84 x 151.2 um, the
# per_element_envelope q outline), unchanged, then removal of the soft placement blockages RTL-MP leaves (as
# dsrom_qtiming_C_place.tcl does for frame C: the hook overrides RTL-MP's macro placement).
source /src/physical/abi3/dsrom_qframe_D_trk_place.tcl
set ot_nblk 0
foreach b [[ord::get_db_block] getBlockages] { odb::dbBlockage_destroy $b; incr ot_nblk }
puts "OT_QTIMING_PLACE removed_rtlmp_blockages=$ot_nblk"
