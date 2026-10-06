# Four actual PP macros on the established pin-track/site-compatible grid.
set f [open /src/physical/abi3/dsrom_qframe_C_trk_place.tcl r]
set s [read $f];close $f
set s [string map {{u_e.} {u_stage.g_el[0].u_elem.}} $s]
eval $s
set b [ord::get_db_block]
foreach x [$b getBlockages] {odb::dbBlockage_destroy $x}
puts "W5_CONTEXT_FULL_NB2_PP1_MACROS_PLACED"
