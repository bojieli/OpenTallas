# DSROM q-element OUTPUT PIN-FLOP BAND (QXPQ-FIX 2026-10-18, S81.STA.LEAF.3.5; NS-QXPQ native audit of the closed RSTP
# view: launch FAIL x4 up to 258.9 ps, prow/pnseg output registers (g_o2.q_*, DFFHQNx1) placed far from their N-face pins,
# then the post-route hold ECO put an HB2 at the flop driving the long wire).  The g_o2 q_* registers exist only to be the
# output pin flops (their only load is the port, see ot_v41_rom_elem_qx_pq_w10.sv g_o2), but the placer left them in the
# logic.  POST_DETAIL_PLACE hook: the ICG enable adjacency hook (which sources the pin keepout + PG check) unchanged,
# then for every signal output port the driver chain (at most 3 buffers / inverters, each with fanout 1) back to a
# flip-flop whose Q drives only that chain is moved onto the port's pin (x = pin centre, y = the core row at the pin's
# face), and the placement is re-legalised.  The flops form one band along the face beside their pins; the long wire is
# now on the full-cycle o_* -> q_* register path inside the element, and any hold pad the ECO adds sits at the pin.
# Connectivity only (no instance names: yosys renames parameterised modules).  Placement only: the netlist is unchanged.
source /src/physical/abi3/dsrom_q_icg_en_adjacent.tcl
set ot_blk [ord::get_db_block]
set ot_core [$ot_blk getCoreArea]
set ot_rowh [[[lindex [$ot_blk getRows] 0] getSite] getHeight]
set ot_cy0 [$ot_core yMin]; set ot_cy1 [$ot_core yMax]
set ot_ob_moved 0; set ot_ob_ports 0; set ot_ob_skip 0
proc ot_ob_fanout1 {net} {
    set n 0
    foreach t [$net getITerms] { if {[$t isInputSignal]} { incr n } }
    return [expr {$n + [llength [$net getBTerms]] - 1}]
}
foreach bt [$ot_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND CLOCK}} continue
    if {[$bt getIoType] ne "OUTPUT"} continue
    set ot_pb [lindex [$bt getBPins] 0]
    if {$ot_pb eq "" || $ot_pb eq "NULL"} continue
    set ot_box [lindex [$ot_pb getBoxes] 0]
    set ot_px [expr {([$ot_box xMin] + [$ot_box xMax]) / 2}]
    set ot_py [expr {([$ot_box yMin] + [$ot_box yMax]) / 2}]
    if {$ot_py >= ($ot_cy0 + $ot_cy1) / 2} { set ot_ty [expr {$ot_cy1 - $ot_rowh}] } else { set ot_ty $ot_cy0 }
    incr ot_ob_ports
    set ot_net [$bt getNet]
    set ot_chain {}
    set ot_ff ""
    for {set k 0} {$k < 4 && $ot_net ne "NULL" && $ot_net ne ""} {incr k} {
        set ot_drv ""
        foreach t [$ot_net getITerms] { if {[$t isOutputSignal]} { set ot_drv [$t getInst]; break } }
        if {$ot_drv eq ""} break
        # the chain must be private to this port: one load per stage (the port, or the next chain cell)
        if {[ot_ob_fanout1 $ot_net] != 0} break
        set ot_m [[$ot_drv getMaster] getName]
        if {[string match "*DFF*" $ot_m]} { set ot_ff $ot_drv; break }
        if {![string match "BUF*" $ot_m] && ![string match "INV*" $ot_m] && ![string match "HB*" $ot_m]} break
        lappend ot_chain $ot_drv
        set ot_net ""
        foreach t [$ot_drv getITerms] { if {[$t isInputSignal]} { set ot_net [$t getNet]; break } }
    }
    if {$ot_ff eq "" || [$ot_ff getPlacementStatus] in {FIRM LOCKED COVER}} {
        incr ot_ob_skip
        puts "OT_OUTFLOP skip [$bt getName] (no private register driver)"
        continue
    }
    foreach c [concat $ot_chain [list $ot_ff]] {
        set w [[$c getMaster] getWidth]
        $c setLocation [expr {$ot_px - $w / 2}] $ot_ty
        incr ot_ob_moved
    }
    puts "OT_OUTFLOP [$bt getName] <- [$ot_ff getName] ([[$ot_ff getMaster] getName]) +[llength $ot_chain] buf"
}
puts "OT_OUTFLOP ports $ot_ob_ports moved $ot_ob_moved cells skipped $ot_ob_skip"
if {$ot_ob_moved > 0} {
    detailed_placement
    check_placement -verbose
    # report the band: worst flop -> pin distance after legalisation
    set ot_dmax 0
    foreach bt [$ot_blk getBTerms] {
        if {[$bt getIoType] ne "OUTPUT" || [$bt getSigType] in {POWER GROUND CLOCK}} continue
        set n [$bt getNet]; if {$n eq "NULL"} continue
        foreach t [$n getITerms] { if {[$t isOutputSignal]} {
            set b [[lindex [$bt getBPins] 0] getBBox]; set i [[$t getInst] getBBox]
            set d [expr {abs(([$b xMin]+[$b xMax])/2 - ([$i xMin]+[$i xMax])/2) + abs(([$b yMin]+[$b yMax])/2 - ([$i yMin]+[$i yMax])/2)}]
            if {$d > $ot_dmax} { set ot_dmax $d }
        } }
    }
    puts "OT_OUTFLOP worst driver->pin manhattan [expr {double($ot_dmax) / [[ord::get_db_tech] getDbUnitsPerMicron]}] um"
}
