# ROM stage power gating (2026-10-04): the DSROM q-frame C track-aligned macro hook (dsrom_qtiming_C_place.tcl,
# unchanged) on the power-gated element top ot_v41_rom_elem_q_pg_w10, whose element sits at u_pg.u_elem instead
# of u_e: the hook's macro table is re-rooted by a string map, nothing else changes.
set ot_fh [open /src/physical/abi3/dsrom_qframe_C_trk_place.tcl r]
set ot_src [read $ot_fh]
close $ot_fh
eval [string map {"\{u_e." "\{u_pg.u_elem."} $ot_src]
set ot_nblk 0
foreach b [[ord::get_db_block] getBlockages] { odb::dbBlockage_destroy $b; incr ot_nblk }
puts "OT_PG_PLACE removed_rtlmp_blockages=$ot_nblk"
