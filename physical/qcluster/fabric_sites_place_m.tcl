# Codex 10-20 fullm: structural reserved-ring legal regions after fullk ODB-0359.
# QW-CB16A0 10-20: the capacity loop variable is rw (was row: it overwrote the 0.27-um row pitch used by later 5-column
# compact-block lines; found by the Codex 05:13 control audit).
# QW-CB16FULL2 (2026-10-20): fabric_sites_place.tcl + BAY lines.  A site line with 7 columns (prefix x y xlo xhi ylo yhi)
# is a RESERVED std-cell bay of one soft landing-ring half (qc_full_kit.py bays()): its flops are spread evenly over the
# whole bay box (row pitch and column pitch chosen so the bay is uniformly filled), not packed into a 24-um 100 %-dense
# block (the 10-19 qfd_c_b16_full / fullb gates: 2,056 ring flops per 24 x 25 um block -> post-CTS DPL negotiation stall).
# 5-column lines keep the original compact-block behaviour (1-bit reset stages).
# Original header:
# Q-CLUSTER (2026-10-17) PRE_GLOBAL_PLACE: place every fabric register stage of qfd_c_b16_dv at its planned site
# (results/arch/qwen_cluster_1017/relay_sites_dv.json -> OT_QC_SITES tsv: prefix x y xlo xhi).  The stage's flops go FIRM
# in a compact block centred on the site, clipped to its corridor [xlo, xhi], so every registered hop keeps the planned
# <= 405 um reach and GPL cannot drag a relay along a 5-mm corridor.  fabric_sites_release.tcl (PRE_DETAIL_PLACE)
# returns them to PLACED for DPL.  Placement only; netlist unchanged.
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OT_QC_SITES) r]
set sites {}
foreach l [split [read $f] "\n"] {
  if {$l eq "" || [string index $l 0] eq "#"} continue
  lappend sites [split $l "\t"]
}
close $f
# instance index: stage prefix -> sequential instances (name with escapes removed)
set byp [dict create]
foreach s $sites { dict set byp [lindex $s 0] {} }
set nseq 0
foreach inst [$blk getInsts] {
  set m [[$inst getMaster] getName]
  if {![string match *DFF* $m]} continue
  incr nseq
  set n [string map {\\ ""} [$inst getName]]
  set parts [split $n .]
  # longest stage prefix match: u_fab.<stage>
  if {[llength $parts] < 3} continue
  set p "[lindex $parts 0].[lindex $parts 1]"
  if {[dict exists $byp $p]} { dict lappend byp $p $inst }
}
set row 0.27
set out [open $::env(RESULTS_DIR)/ot_qc_sites_firm.txt w]
set placed 0; set empty 0
set nbay 0
foreach s $sites {
  lassign $s p x y xlo xhi ylo yhi
  set insts [dict get $byp $p]
  if {![llength $insts]} { incr empty; continue }
  set fw [expr {double([[[lindex $insts 0] getMaster] getWidth]) / $dbu}]
  if {$ylo ne "" && $yhi ne ""} {
    # A ring bay is a legal region, not FIRM individual standard cells. GPL owns all positions;
    # group membership keeps the complete ring FF mass inside its sized, reserved bay.
    set region [odb::dbRegion_create $blk qc_bay_$nbay]
    $region setRegionType EXCLUSIVE
    odb::dbBox_create $region [expr {round($xlo*$dbu)}] [expr {round($ylo*$dbu)}] [expr {round($xhi*$dbu)}] [expr {round($yhi*$dbu)}]
    set group [odb::dbGroup_create $region qc_bay_$nbay]
    set area 0.0
    foreach i $insts {
      if {[$i getGroup] ne "NULL" && [$i getGroup] ne ""} {error "QC_BAY already grouped [$i getName]"}
      $group addInst $i
      $i setPlacementStatus UNPLACED
      set m [$i getMaster]
      set area [expr {$area+double([$m getWidth])*[$m getHeight]/($dbu*$dbu)}]
      incr placed
    }
    set capacity 0.0
    foreach rw [$blk getRows] {
      set bb [$rw getBBox]
      set rx0 [expr {[$bb xMin]/double($dbu)}];set ry0 [expr {[$bb yMin]/double($dbu)}]
      set rx1 [expr {[$bb xMax]/double($dbu)}];set ry1 [expr {[$bb yMax]/double($dbu)}]
      set capacity [expr {$capacity+max(0.0,min($xhi,$rx1)-max($xlo,$rx0))*max(0.0,min($yhi,$ry1)-max($ylo,$ry0))}]
    }
    if {$capacity<=0 || $area/$capacity>0.35} {error "QC_BAY insufficient legal row capacity $p area=$area capacity=$capacity"}
    puts "QC_BAY region=$nbay prefix=$p flops=[llength $insts] area=$area capacity=$capacity fill=[expr {$area/$capacity}]"
    incr nbay
    continue
  }
  set bw [expr {min(24.0, $xhi - $xlo - 4.0)}]
  set per [expr {max(1, int($bw / $fw))}]
  set nrow [expr {int(ceil(double([llength $insts]) / $per))}]
  set x0 [expr {max($xlo + 2.0, min($x - $per * $fw / 2.0, $xhi - 2.0 - $per * $fw))}]
  set y0 [expr {$y - $nrow * $row / 2.0}]
  set k 0
  foreach i $insts {
    set cx [expr {$x0 + ($k % $per) * $fw}]
    set cy [expr {$y0 + ($k / $per) * $row}]
    $i setLocation [expr {round($cx * $dbu)}] [expr {round($cy * $dbu)}]
    $i setPlacementStatus FIRM
    puts $out [$i getName]
    incr k; incr placed
  }
}
close $out
puts "OT_QC_SITES placed $placed of $nseq flops at [llength $sites] stage sites ($nbay ring bays, $empty sites matched no flop)"
if {$placed < 0.9 * $nseq} { error "OT_QC_SITES: only $placed of $nseq flops matched a stage site" }
