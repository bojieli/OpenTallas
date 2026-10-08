# DSROM q-element QM >= 7 (2026-10-06, Z28a post-CTS at 770): the clock-gate enable registers (u_z / u_zc) sat a long
# wire away from their ICG (INVx5 driving 32 fF, ENA slew 231 ps -> ICG setup 99 ps; ENA -71.5 ps against the ICG's
# early root-side clock, setup skew 452 ps).  The enable register's only load is its ICG, so the long wire belongs on
# its D side (a full cycle between same-latency registers), not on ENA.  POST_DETAIL_PLACE hook: the pin keepout
# hook unchanged, then for every ICG the ENA driver chain (inverters / buffers back to the enable flop, at most 3
# cells) is moved onto the ICG's location and the placement re-legalised.  Placement only: the netlist is unchanged.
source /src/physical/abi3/dsrom_q_pin_keepout2.tcl
set ot_blk [ord::get_db_block]
set ot_moved 0
foreach ot_icg [$ot_blk getInsts] {
    if {![string match "ICG*" [[$ot_icg getMaster] getName]]} continue
    set ot_it [$ot_icg findITerm ENA]
    if {$ot_it eq "NULL" || $ot_it eq ""} continue
    set ot_loc [$ot_icg getLocation]
    set ot_net [$ot_it getNet]
    for {set k 0} {$k < 3 && $ot_net ne "NULL" && $ot_net ne ""} {incr k} {
        set ot_drv ""
        foreach t [$ot_net getITerms] { if {[$t isOutputSignal]} { set ot_drv [$t getInst]; break } }
        if {$ot_drv eq ""} break
        if {[$ot_drv getPlacementStatus] in {FIRM LOCKED COVER}} break
        $ot_drv setLocation [lindex $ot_loc 0] [lindex $ot_loc 1]
        incr ot_moved
        puts "OT_ICG_EN move [$ot_drv getName] ([[$ot_drv getMaster] getName]) -> [$ot_icg getName]"
        if {[string match "*DFF*" [[$ot_drv getMaster] getName]]} break
        set ot_net ""
        foreach t [$ot_drv getITerms] { if {[$t isInputSignal]} { set ot_net [$t getNet]; break } }
    }
}
puts "OT_ICG_EN moved $ot_moved cells"
if {$ot_moved > 0} {
    detailed_placement
    check_placement -verbose
}
