# OpenROAD harness for ot_macro_track_snap.tcl (driven by tools/test_ot_macro_track_snap.py).
# Env: OT_SRC_ROOT, OT_TEST_LEFS (space-separated macro LEFs), OT_TEST_VERILOG (one instance per macro,
# module ot_mts_top), OT_TEST_DIE (die/core extent in um).  Prints one OT_MTS_CASE line per
# (macro, orientation) and OT_MTS_NEG lines for the negative cases.
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l $::env(OT_TEST_LEFS) { read_lef $l }
read_verilog $::env(OT_TEST_VERILOG)
link_design ot_mts_top
lassign $::env(OT_TEST_DIE) dw dh
initialize_floorplan -die_area "0 0 $dw $dh" -core_area "0 0 $dw $dh" -site asap7sc7p5t
set ::env(MAKE_TRACKS) $plat/openRoad/make_tracks.tcl
source $::env(MAKE_TRACKS)
source $::env(OT_SRC_ROOT)/physical/common/ot_macro_track_snap.tcl

set block [ord::get_db_block]
set targets {{103.217 201.333} {57.5 33.3}}
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {![$m isBlock]} { continue }
    if {[string match u_pair_* [$inst getName]]} { continue }
    set orients {R0}
    if {[$m getSymmetryX]} { lappend orients MX }
    if {[$m getSymmetryY]} { lappend orients MY }
    if {[$m getSymmetryX] && [$m getSymmetryY]} { lappend orients R180 }
    foreach o $orients {
        foreach t $targets {
            lassign $t tx ty
            if {[catch {ot_mts::place $inst $tx $ty $o} xy]} {
                puts "OT_MTS_CASE [$m getName] $o NO_LEGAL_ORIGIN"
                break
            }
            set n [ot_mts::assert_on_track -insts [list $inst] -warn_only -label "[$m getName]:$o"]
            set loc [$inst getLocation]
            puts "OT_MTS_CASE [$m getName] $o placed [lindex $loc 0] [lindex $loc 1] offtrack $n"
        }
    }
    # negative 1: a legal R0 placement moved 6 nm (x and y) must trip the (non-warn) assert
    if {![catch {ot_mts::place $inst 50 50 R0}]} {
        set loc [$inst getLocation]
        $inst setPlacementStatus PLACED
        $inst setLocation [expr {[lindex $loc 0] + 6}] [expr {[lindex $loc 1] + 6}]
        set tripped [catch {ot_mts::assert_on_track -insts [list $inst] -label neg6} msg]
        puts "OT_MTS_NEG [$m getName] shift6nm tripped $tripped"
    }
    # negative 2: the defective hooks' snap (MX, origin y = 0 mod 0.048 on the row grid)
    if {[$m getSymmetryX]} {
        $inst setPlacementStatus PLACED
        $inst setOrient MX
        $inst setLocation 0 [expr {2160 * 10}]
        set n [ot_mts::assert_on_track -insts [list $inst] -warn_only -label naive]
        puts "OT_MTS_NEG [$m getName] naive_mx_origin0 offtrack $n"
    }
    $inst setPlacementStatus NONE
}
# the w10 q-pair stack: rom0 R0 at y 0.54, rom1 MX requested at 63.45 (the hooks' coordinates); the snap
# must not overlap rom0 even when the legal MX point nearest 63.45 would
if {[info exists ::env(OT_TEST_PAIR)] && $::env(OT_TEST_PAIR) ne ""} {
    set a [$block findInst u_$::env(OT_TEST_PAIR)]
    set b [$block findInst u_pair_$::env(OT_TEST_PAIR)]
    ot_mts::place $a 5.4 0.54 R0
    ot_mts::place $b 5.4 63.45 MX
    set ba [$a getBBox]; set bb [$b getBBox]
    set n [ot_mts::assert_on_track -insts [list $a $b] -warn_only -label pair]
    puts "OT_MTS_PAIR $::env(OT_TEST_PAIR) rom0_top [$ba yMax] rom1_bottom [$bb yMin] offtrack $n"
}
puts "OT_MTS_DONE"
