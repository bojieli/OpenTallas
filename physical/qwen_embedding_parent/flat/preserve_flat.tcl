# drive-0502 2026-10-08: FLATTEN variant PRE_FLOORPLAN hook. In the flat parent the top-level rst_n also feeds the
# ingress pad chain's first dont_touch BUFx2 (u_ingress...g_pad[*].g_stage[0].u_pad/A), so repair_design cannot buffer
# rst_n (RSZ-3006 "Failed to insert buffer before loads", ODB-1211 dont_touch load) and global_place dies. Give each
# dont_touch pad load on a net that also feeds other cell inputs its own ordinary BUFx2 (the pad chain then hangs off a one-load net), then
# apply the qualified pad retention (physical/qwen_embedding_padded/preserve.tcl, unchanged: same 150/210 cells).
# Logic is unchanged (a buffer); the reset reaches the pad chain one BUFx2 later.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
set iso 0
foreach net [$block getNets] {
    set pads {}
    set others 0
    foreach it [$net getITerms] {
        if {[regexp {g_pad.*g_stage\\?\[0\\?\][./]u_pad$} [[$it getInst] getName]] && [$it getMTerm] ne "" && [[$it getMTerm] getName] eq "A"} {
            lappend pads $it
        } elseif {[$it getIoType] ne "OUTPUT"} { incr others }
    }
    if {[llength $pads] == 0 || $others == 0} { continue }
    foreach it $pads {
        set nn [odb::dbNet_create $block "ot_pad_iso_net_$iso"]
        set bi [odb::dbInst_create $block $master "ot_pad_iso_$iso"]
        set pi [$it getInst]
        set dt [$pi isDoNotTouch]
        $pi setDoNotTouch 0
        $it disconnect
        $it connect $nn
        $pi setDoNotTouch $dt
        [$bi findITerm A] connect $net
        [$bi findITerm Y] connect $nn
        puts "EMBED_PAD_ISO [$net getName] -> [[$it getInst] getName] via ot_pad_iso_$iso"
        incr iso
    }
}
puts "EMBED_PAD_ISO_COUNT $iso"
source /src/physical/qwen_embedding_padded/preserve.tcl
