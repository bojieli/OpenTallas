# DSROM q-element PIN-FLOP BAND, CPR variant (S81-PINREG4 2026-10-19, SAFE item 1).  The output band
# (dsrom_q_outflop_band.tcl, unchanged: it places every private output register -- now incl. the CPR busy / fault pin
# flops -- at its pin), then the same for the INPUT pin registers of the go command (CPR = 1: go_pf / go_tag_pf): for each
# signal input port whose name matches OT_Q_INFLOP_RE (default ^go(_tag)?(\[|$)), the load chain (at most 3 buffers /
# inverters, each with exactly one load) from the pin to a flip-flop D is moved onto the port's pin (x = pin centre, y =
# the core row at the pin's face) and re-legalised, so the pin -> D wire is a few um and the go fan-out wire sits on the
# full-cycle go_pf -> u_e path.  Connectivity only (no instance names).  Placement only: the netlist is unchanged.
source /src/physical/abi3/dsrom_q_outflop_band.tcl
set ot_ib_re [expr {[info exists ::env(OT_Q_INFLOP_RE)] ? $::env(OT_Q_INFLOP_RE) : {^go(_tag)?(\[|$)}}]
set ot_ib_moved 0; set ot_ib_ports 0; set ot_ib_skip 0
proc ot_ib_loads {net} {
    set l {}
    foreach t [$net getITerms] { if {[$t isInputSignal]} { lappend l $t } }
    return $l
}
foreach bt [$ot_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND CLOCK}} continue
    if {[$bt getIoType] ne "INPUT"} continue
    if {![regexp $ot_ib_re [$bt getName]]} continue
    set ot_pb [lindex [$bt getBPins] 0]
    if {$ot_pb eq "" || $ot_pb eq "NULL"} continue
    set ot_box [lindex [$ot_pb getBoxes] 0]
    set ot_px [expr {([$ot_box xMin] + [$ot_box xMax]) / 2}]
    set ot_py [expr {([$ot_box yMin] + [$ot_box yMax]) / 2}]
    if {$ot_py >= ($ot_cy0 + $ot_cy1) / 2} { set ot_ty [expr {$ot_cy1 - $ot_rowh}] } else { set ot_ty $ot_cy0 }
    incr ot_ib_ports
    set ot_net [$bt getNet]
    set ot_chain {}; set ot_ff ""
    for {set k 0} {$k < 4 && $ot_net ne "NULL" && $ot_net ne ""} {incr k} {
        set ot_l [ot_ib_loads $ot_net]
        if {[llength $ot_l] != 1 || [llength [$ot_net getBTerms]] != 1} break
        set ot_ld [[lindex $ot_l 0] getInst]
        set ot_m [[$ot_ld getMaster] getName]
        if {[string match "*DFF*" $ot_m]} { set ot_ff $ot_ld; break }
        if {![string match "BUF*" $ot_m] && ![string match "INV*" $ot_m] && ![string match "HB*" $ot_m]} break
        lappend ot_chain $ot_ld
        set ot_net ""
        foreach t [$ot_ld getITerms] { if {[$t isOutputSignal]} { set ot_net [$t getNet]; break } }
    }
    if {$ot_ff eq "" || [$ot_ff getPlacementStatus] in {FIRM LOCKED COVER}} {
        incr ot_ib_skip
        puts "OT_INFLOP skip [$bt getName] (no private pin register)"
        continue
    }
    foreach c [concat $ot_chain [list $ot_ff]] {
        set w [[$c getMaster] getWidth]
        $c setLocation [expr {$ot_px - $w / 2}] $ot_ty
        incr ot_ib_moved
    }
    puts "OT_INFLOP [$bt getName] -> [$ot_ff getName] ([[$ot_ff getMaster] getName]) +[llength $ot_chain] buf"
}
puts "OT_INFLOP ports $ot_ib_ports moved $ot_ib_moved cells skipped $ot_ib_skip"
if {$ot_ib_moved > 0} {
    detailed_placement
    check_placement -verbose
}
