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
    # BAY: n flops over R usable rows (1 row margin each side); c per row, x pitch (xhi - xlo - 2) / c
    set n [llength $insts]
    set R [expr {max(1, int(floor(($yhi - $ylo - 2.0 * $row) / $row)))}]
    set ru [expr {min($R, $n)}]
    set c [expr {int(ceil(double($n) / $ru))}]
    set rp [expr {max(1, $R / $ru)}]
    set xp [expr {($xhi - $xlo - 2.0 - $fw) / max(1, $c - 1)}]
    if {$xp < $fw} { set xp $fw }
    set k 0
    foreach i $insts {
      set cx [expr {$xlo + 1.0 + ($k % $c) * $xp}]
      set cy [expr {$ylo + $row + (($k / $c) * $rp) * $row}]
      $i setLocation [expr {round($cx * $dbu)}] [expr {round($cy * $dbu)}]
      $i setPlacementStatus FIRM
      puts $out [$i getName]
      incr k; incr placed
    }
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
