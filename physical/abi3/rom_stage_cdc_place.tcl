# Gated stage with synchronised crossings (2026-10-04): the DSROM q-frame C track-aligned macro hook
# (dsrom_qframe_C_trk_place.tcl, unchanged) applied to every element of ot_v41_rom_stage_q_pg_cdc_w10: element k
# sits at g_el[k].u_elem in the q-frame tile (k % ot_cols, k / ot_cols) of 510.84 x 126.9 um.  ot_k / ot_cols are set
# by the per-size hooks rom_stage_cdc_place_k1.tcl / _k4.tcl, which source this file.
set ot_fh [open /src/physical/abi3/dsrom_qframe_C_trk_place.tcl r]
set ot_src [read $ot_fh]
close $ot_fh
set i0 [string first "set ot_macros \{" $ot_src]
set i1 [string first "\n\}\n" $ot_src $i0]
set tbl [string range $ot_src [expr {$i0 + [string length "set ot_macros \{"]}] [expr {$i1 - 1}]]
set new {}
for {set k 0} {$k < $ot_k} {incr k} {
    set dx [expr {($k % $ot_cols) * 510.84}]
    set dy [expr {($k / $ot_cols) * 126.9}]
    foreach {name mx my orient capture} $tbl {
        set n [string map [list "u_e." "g_el\[$k\].u_elem."] $name]
        lappend new $n [format %.3f [expr {$mx + $dx}]] [format %.3f [expr {$my + $dy}]] $orient $capture
    }
}
set ot_src [string replace $ot_src $i0 [expr {$i1 + 1}] "set ot_macros [list $new]"]
eval $ot_src
set ot_nblk 0
foreach b [[ord::get_db_block] getBlockages] { odb::dbBlockage_destroy $b; incr ot_nblk }
puts "OT_STAGE_CDC_PLACE k=$ot_k cols=$ot_cols removed_rtlmp_blockages=$ot_nblk"
