# Source-bound four local SRAM clock buffers. No clock ports, phase or normal edges change.
# Every placement is selected from actual legal rows minus ALL placed cells and blockages.
set mb [ord::get_db_block]
set mu [[ord::get_db_tech] getDbUnitsPerMicron]
set mm [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
if {$mm eq "NULL" || [$mm isBlock]} {error {LOCAL_MACRO_CLK missing exact BUFx24 master}}
set bt [$mb findBTerm ck]
if {$bt eq "NULL"} {error {LOCAL_MACRO_CLK missing literal ck port}}
set source_net [$bt getNet]
set targets {}
foreach bank {0 1 2 3} {
    set name "u_core.u_end.u_link.g_bank\[$bank\].u_store.u_sram"
    set macro [$mb findInst $name]
    if {$macro eq "NULL" || [[$macro getMaster] getName] ne "ot_sram_1r1w_64x512_m1_r2c2"} {error "LOCAL_MACRO_CLK missing exact SRAM $name"}
    set clock [$macro findITerm clk]
    if {$clock eq "NULL" || [$clock getNet] ne $source_net} {error "LOCAL_MACRO_CLK $name/clk is not on literal unchanged ck root"}
    lassign [$clock getAvgXY] ok px py
    if {!$ok} {error "LOCAL_MACRO_CLK missing actual clock pin geometry $name"}
    if {[$mb findInst ot_local_macro_clk_$bank] ne "NULL"} {error {LOCAL_MACRO_CLK refuses duplicate insertion}}
    lappend targets [list $bank $clock $px $py]
}
source /src/physical/common_flow/anchor_row_packing.tcl
set rows {};set maxheight 0
foreach row [$mb getRows] {
    set b [$row getBBox];set h [expr {[$b yMax]-[$b yMin]}]
    if {$h<=0 || [$row getSpacing]<=0} continue
    lappend rows [list [$b yMin] [$b xMin] [$b xMax] [$b yMax] [$row getSpacing] [$row getOrient]]
    set maxheight [expr {max($maxheight,$h)}]
}
set rows [lsort -integer -index 0 $rows]
if {![llength $rows]} {error {LOCAL_MACRO_CLK no legal rows}}
set free {};set ri 0
foreach row $rows {dict set free $ri [list [list [lindex $row 1] [lindex $row 2]]];incr ri}
set obstacles {}
foreach inst [$mb getInsts] {
    if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
    set b [$inst getBBox];lappend obstacles [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
foreach blockage [$mb getBlockages] {
    set b [$blockage getBBox];lappend obstacles [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
foreach rect $obstacles {
    lassign $rect x0 y0 x1 y1
    set ri [ot_anchor_pack::lower $rows [expr {$y0-$maxheight}]]
    for {} {$ri<[llength $rows]} {incr ri} {
        lassign [lindex $rows $ri] ry rx ex ey pitch orient
        if {$ry >= $y1} break
        if {$ey>$y0} {dict set free $ri [ot_anchor_pack::cut [dict get $free $ri] $x0 $x1]}
    }
}
set width [$mm getWidth];set height [$mm getHeight];set added {}
foreach target $targets {
    lassign $target bank clock px py
    set score Inf;set best {};set ri 0
    foreach row $rows {
        lassign $row ry rx ex ey pitch orient
        if {$height==$ey-$ry} {
            foreach interval [dict get $free $ri] {
                lassign $interval a b
                set lo [expr {$rx+int(ceil(double($a-$rx)/$pitch))*$pitch}]
                set hi [expr {$rx+int(floor(double($b-$width-$rx)/$pitch))*$pitch}]
                if {$hi<$lo} continue
                set x [expr {max($lo,min($hi,$rx+round(($px-$width/2.0-$rx)/$pitch)*$pitch))}]
                set cost [expr {abs($x+$width/2.0-$px)+abs($ry+$height/2.0-$py)}]
                if {$cost<$score} {set score $cost;set best [list $ri $x $ry $orient]}
            }
        }
        incr ri
    }
    if {$best eq "" || $score>21.6*$mu} {error "LOCAL_MACRO_CLK no local legal station for bank$bank distance $score DBU"}
    lassign $best ri x y orient
    set cell [odb::dbInst_create $mb $mm ot_local_macro_clk_$bank]
    $cell setOrient $orient;$cell setLocation $x $y;$cell setPlacementStatus FIRM;$cell setDoNotTouch 1
    set input [$cell findITerm A];set output [$cell findITerm Y]
    if {$input eq "NULL" || $output eq "NULL"} {error {LOCAL_MACRO_CLK BUFx24 pin ABI mismatch}}
    set leaf [odb::dbNet_create $mb ot_local_macro_clk_${bank}_net]
    $leaf setSigType CLOCK;$leaf setDoNotTouch 1
    $clock disconnect;$clock connect $leaf;$input connect $source_net;$output connect $leaf
    dict set free $ri [ot_anchor_pack::cut [dict get $free $ri] $x [expr {$x+$width}]]
    lappend added $cell
    puts "LOCAL_MACRO_CLK bank$bank pin=[$clock getInst]/clk station=[$cell getName] xy=($x,$y) orient=$orient reach_dbu=$score source=[$source_net getName]"
}
global_connect
foreach cell $added {
    foreach power {VDD VSS} {
        set it [$cell findITerm $power]
        if {$it eq "NULL" || [$it getNet] eq "NULL" || [[$it getNet] getName] ne $power} {error "LOCAL_MACRO_CLK missing actual $power connection for [$cell getName]"}
    }
}
if {[llength $added]!=4} {error {LOCAL_MACRO_CLK did not insert exactly four stations}}
puts {LOCAL_MACRO_CLK exact4 legal local stations, actual VDD/VSS connected; no source clock ports/phases/edges changed}
