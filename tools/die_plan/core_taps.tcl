# QC-RP1 10-25 F5 (cqb COORD GEOM VERDICT, owner 10-23 structured clock): regional clock taps inside the hard core.
# PRE_CTS (after hold_budget.tcl).  The single core clock port feeds one tap buffer per region; every register clock
# pin moves onto the tap of its region, every macro clock pin onto its OWN short leaf buffer next to the pin, fed from
# the tap of its region.  CTS then builds one local tree per tap net (child builders) under a short root tree;
# core_taps_post.tcl balances the taps (<= OT_CTAP_WIN ps) and latency-matches each macro leaf to its interface regs.
# Regions (core um): S band y < OT_CTAP_SY -> SW / SE split at OT_CTAP_SX; above: W / E split at OT_CTAP_SX and
# 0 / 1 split at OT_CTAP_MY (rp1: west strip, east strip, one per SRAM row, + south-west / south-east).
uplevel #0 {
set ct_blk [ord::get_db_block]
set ct_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc ct_env {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
set ct_sy [expr {round([ct_env OT_CTAP_SY 60.0] * $ct_dbu)}]
set ct_sx [expr {round([ct_env OT_CTAP_SX 130.0] * $ct_dbu)}]
set ct_my [expr {round([ct_env OT_CTAP_MY 169.0] * $ct_dbu)}]
set ct_cell [ct_env OT_CTAP_CELL BUFx16f_ASAP7_75t_R]
set ct_lcell [ct_env OT_CTAP_LEAF_CELL BUFx8_ASAP7_75t_R]
set ct_master [[ord::get_db] findMaster $ct_cell]
set ct_lmaster [[ord::get_db] findMaster $ct_lcell]
if {$ct_master eq "NULL" || $ct_lmaster eq "NULL"} { error "OT_CTAP missing cell $ct_cell / $ct_lcell" }
set ct_port [ct_env OT_CORE_CLK ck]
set ct_bt [$ct_blk findBTerm $ct_port]
if {$ct_bt eq "NULL"} { error "OT_CTAP no clock port $ct_port" }
set ct_root [$ct_bt getNet]
proc ct_region {x y} {
  global ct_sy ct_sx ct_my
  if {$y < $ct_sy} { return [expr {$x < $ct_sx ? "SW" : "SE"}] }
  set h [expr {$x < $ct_sx ? "W" : "E"}]
  return "$h[expr {$y < $ct_my ? 0 : 1}]"
}
set ct_sinks {}; set ct_macro {}
foreach it [$ct_root getITerms] {
  if {[[$it getMTerm] getIoType] ne "INPUT"} continue
  set i [$it getInst]
  if {[[$i getMaster] isBlock]} { set b [$it getBBox] } else { set b [$i getBBox] }
  set x [expr {([$b xMin] + [$b xMax]) / 2}]; set y [expr {([$b yMin] + [$b yMax]) / 2}]
  set r [ct_region $x $y]
  if {[[$i getMaster] isBlock]} { lappend ct_macro [list $it $r $x $y] } else { dict lappend ct_sinks $r [list $it $x $y] }
}
set ct_taps {}
dict for {r rows} $ct_sinks {
  set sx 0; set sy 0
  foreach row $rows { set sx [expr {$sx + [lindex $row 1]}]; set sy [expr {$sy + [lindex $row 2]}] }
  set n [llength $rows]
  set net [odb::dbNet_create $ct_blk "ot_ctap_${r}_n"]; $net setSigType CLOCK
  set buf [odb::dbInst_create $ct_blk $ct_master "ot_ctap_${r}"]
  foreach t [$buf getITerms] {
    set mt [$t getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $ct_root } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $net }
  }
  $buf setLocation [expr {$sx / $n}] [expr {$sy / $n}]; $buf setPlacementStatus PLACED
  foreach row $rows { set it [lindex $row 0]; $it disconnect; $it connect $net }
  dict set ct_taps $r $net
  puts [format "OT_CTAP tap %s sinks %d at %.1f %.1f" $r $n [expr {$sx / $n / double($ct_dbu)}] [expr {$sy / $n / double($ct_dbu)}]]
}
# OT_CTAP_MACRO_ROOT=1: the macro leaf hangs on the core clock root (its own tap) instead of under its region tap, so
# core_taps_post.tcl can place its latency independently (OT_CTAP_MACRO_EARLY useful skew vs its interface regs)
set ct_mroot [ct_env OT_CTAP_MACRO_ROOT 0]
# each macro clock pin: own short leaf from its region tap, placed just outside the macro halo at the pin
foreach row $ct_macro {
  lassign $row it r x y
  set m [$it getInst]; set mb [$m getBBox]
  if {![dict exists $ct_taps $r]} { error "OT_CTAP macro [$m getName] region $r has no register tap" }
  set net [odb::dbNet_create $ct_blk "ot_cleaf_[regsub -all {[^A-Za-z0-9]} [$m getName] _]_n"]; $net setSigType CLOCK
  set buf [odb::dbInst_create $ct_blk $ct_lmaster "ot_cleaf_[regsub -all {[^A-Za-z0-9]} [$m getName] _]"]
  foreach t [$buf getITerms] {
    set mt [$t getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect [expr {$ct_mroot ? $ct_root : [dict get $ct_taps $r]}] } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $net }
  }
  set gap [expr {round(6.0 * $ct_dbu)}]
  set lx [expr {abs($x - [$mb xMin]) < abs([$mb xMax] - $x) ? [$mb xMin] - $gap - [$ct_lmaster getWidth] : [$mb xMax] + $gap}]
  $buf setLocation $lx $y; $buf setPlacementStatus PLACED
  $it disconnect; $it connect $net
  dict set ::ct_leaf [$m getName] [list [$buf getName] $r]
  puts [format "OT_CTAP macro leaf %s region %s at %.1f %.1f" [$m getName] $r [expr {$lx / double($ct_dbu)}] [expr {$y / double($ct_dbu)}]]
}
detailed_placement
}
