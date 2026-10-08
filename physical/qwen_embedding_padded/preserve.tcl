# Set ODB persistence before floorplan remove_buffers, sizing or repair.
set count 0
foreach inst [[ord::get_db_block] getInsts] {
    if {[string match "*g_pad*" [$inst getName]]} {
        if {[[$inst getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {error "Unexpected ingress pad cell"}
        $inst setDoNotTouch 1
        incr count
    }
}
if {![info exists ::env(EMBED_PAD_CELLS)] || $count != $::env(EMBED_PAD_CELLS)} {
    error "Ingress pad retention failed: $count cells"
}
puts "EMBED_PAD_RETENTION $count actual fixed BUFx2 cells"
