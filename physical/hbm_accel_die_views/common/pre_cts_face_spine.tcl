# PRE_CTS hook (safe-hbm 2026-10-08, reviewer decision R-Q3 variant 2): a pre-CTS clock SPINE to the output faces.
# hbm_quant (hfd_quant, 4.6 % utilisation in a 1,400 x 359 um slot) spreads its boundary clock insertion by ~380-430 ps
# (calib.json FF 480..856 / TT 567..1000): the output pin flops sit on the far W / E faces, reached through long clock
# wires and repeater chains that CTS sizes per sink cluster.  This hook gives every output port group (OT_SPINE_PORTS,
# default the four t_su_* faces) ONE clock branch: a BUFx24 placed at the centroid of that group's pin flops, driven from
# the root clock net, with the group's pin flops moved onto its output net; CTS then builds each face's sub-tree below
# its spine buffer (the root tree only sees the spine buffers there).  Netlist change on the clock only (one buffer per
# face group), logic and constraints unchanged, 0 cycles.  Runs the default PRE_CTS hook first.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
set ot_blk [ord::get_db_block]
set ot_db [ord::get_db]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_bufm [$ot_db findMaster BUFx24_ASAP7_75t_R]
set ot_groups [expr {[info exists ::env(OT_SPINE_PORTS)] ? $::env(OT_SPINE_PORTS) : "t_su_SW t_su_NW t_su_SE t_su_NE"}]
proc ot_sp_pin_flop {bt} {
  # port <- [one INV/BUF] <- DFF : return the DFF inst or ""
  set n [$bt getNet]
  if {$n eq "NULL" || $n eq ""} { return "" }
  set its [$n getITerms]
  if {[llength $its] != 1} { return "" }
  set i [[lindex $its 0] getInst]
  if {[regexp {^(INV|BUF)} [[$i getMaster] getName]]} {
    set a ""; foreach t [$i getITerms] { if {[$t isInputSignal]} { set a $t } }
    if {$a eq ""} { return "" }
    set n2 [$a getNet]; if {$n2 eq "NULL" || [llength [$n2 getITerms]] != 2} { return "" }
    foreach t [$n2 getITerms] { if {$t ne $a} { set i [$t getInst] } }
  }
  if {![string match "DFF*" [[$i getMaster] getName]]} { return "" }
  return $i
}
foreach g $ot_groups {
  set ffs {}
  foreach bt [$ot_blk getBTerms] {
    if {[string first "${g}\[" [$bt getName]] != 0 && [$bt getName] ne $g} continue
    set f [ot_sp_pin_flop $bt]
    if {$f ne ""} { lappend ffs $f }
  }
  if {[llength $ffs] < 2} { puts "OT_SPINE $g: [llength $ffs] pin flops, skipped"; continue }
  set ck [[[lindex $ffs 0] findITerm CLK] getNet]
  set sx 0.0; set sy 0.0; set moved 0
  set nn [odb::dbNet_create $ot_blk "ot_spine_${g}_ck"]
  $nn setSigType CLOCK
  set b [odb::dbInst_create $ot_blk $ot_bufm "ot_spine_${g}"]
  foreach f $ffs {
    set t [$f findITerm CLK]
    if {[$t getNet] ne $ck} continue
    set l [$f getLocation]; set sx [expr {$sx + [lindex $l 0]}]; set sy [expr {$sy + [lindex $l 1]}]
    $t disconnect; $t connect $nn; incr moved
  }
  [$b findITerm A] connect $ck
  [$b findITerm Y] connect $nn
  $b setLocation [expr {int($sx / $moved)}] [expr {int($sy / $moved)}]
  $b setPlacementStatus PLACED
  $b setSourceType TIMING
  puts "OT_SPINE $g: [llength $ffs] pin flops, $moved moved onto ot_spine_${g}_ck at ([expr {$sx / $moved / $ot_dbu}], [expr {$sy / $moved / $ot_dbu}]) from [$ck getName]"
}
