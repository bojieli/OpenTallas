# DIE-S81-75 11-07 eng_rr_e vJ (OT_MACRO_OUT_BUF_MIN_UM): one buffer at the macro face on every long macro output net.
# Measured on vI routed: 36 of 188 slew-failing nets are macro rd_out pins with no driver between pin and wire (worst 490 ps,
# u_xq.br_rd[53]). repair_design leaves them near the limit at GRT RC, RCX puts them over. The macro pin then sees one buffer
# input and the wire sees a real driver. Function unchanged.
set mb_min [expr {double($::env(OT_MACRO_OUT_BUF_MIN_UM))}]
set mb_blk [ord::get_db_block]; set mb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set mb_m [[ord::get_db] findMaster [expr {[info exists ::env(OT_MACRO_OUT_BUF)] ? $::env(OT_MACRO_OUT_BUF) : "BUFx4_ASAP7_75t_R"}]]
set mb_n 0; set mb_skip 0
foreach mb_i [$mb_blk getInsts] {
  if {[[$mb_i getMaster] getType] ne "BLOCK"} continue
  set mb_bb [$mb_i getBBox]
  foreach it [$mb_i getITerms] {
    set mt [$it getMTerm]
    if {[$mt getIoType] ne "OUTPUT" || [$mt getSigType] in {POWER GROUND CLOCK}} continue
    set net [$it getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net isSpecial]} continue
    set xs {}; set ys {}; set others {}
    foreach y [$net getITerms] { set b [$y getBBox]; lappend xs [$b xMin]; lappend ys [$b yMin]; if {$y ne $it} { lappend others $y } }
    foreach y [$net getBTerms] { set b [$y getBBox]; lappend xs [$b xMin]; lappend ys [$b yMin] }
    set xs [lsort -integer $xs]; set ys [lsort -integer $ys]
    set hp [expr {double([lindex $xs end]-[lindex $xs 0]+[lindex $ys end]-[lindex $ys 0])/$mb_dbu}]
    if {$hp < $mb_min || ![llength $others] || [llength [$net getBTerms]]} { incr mb_skip; continue }
    set pb [$it getBBox]; set px [$pb xMin]; set py [$pb yMin]; set g [expr {2*$mb_dbu}]
    # just outside the nearest macro edge
    set dl [expr {$px-[$mb_bb xMin]}]; set dr [expr {[$mb_bb xMax]-$px}]; set db [expr {$py-[$mb_bb yMin]}]; set dt [expr {[$mb_bb yMax]-$py}]
    set dm [lindex [lsort -integer [list $dl $dr $db $dt]] 0]
    if {$dm == $dl} { set bx [expr {[$mb_bb xMin]-$g}]; set by $py } elseif {$dm == $dr} { set bx [expr {[$mb_bb xMax]+$g}]; set by $py } elseif {$dm == $db} { set bx $px; set by [expr {[$mb_bb yMin]-$g}] } else { set bx $px; set by [expr {[$mb_bb yMax]+$g}] }
    incr mb_n
    set bi [odb::dbInst_create $mb_blk $mb_m "ot_mob_$mb_n"]
    set nn [odb::dbNet_create $mb_blk "ot_mob_${mb_n}_n"]; $nn setSigType SIGNAL
    foreach y $others { $y disconnect; $y connect $nn }
    foreach y [$bi getITerms] { set m [$y getMTerm]; if {[$m getSigType] in {POWER GROUND}} continue
      if {[$m getIoType] eq "INPUT"} { $y connect $net } elseif {[$m getIoType] eq "OUTPUT"} { $y connect $nn } }
    $bi setLocation $bx $by; $bi setPlacementStatus PLACED
  }
}
puts "OT_MACRO_OUT_BUF $mb_n buffers on macro outputs >= $mb_min um HPWL, $mb_skip left"
if {$mb_n} { detailed_placement; check_placement -verbose }
