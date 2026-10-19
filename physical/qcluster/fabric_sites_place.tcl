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
foreach s $sites {
  lassign $s p x y xlo xhi
  set insts [dict get $byp $p]
  if {![llength $insts]} { incr empty; continue }
  set fw [expr {double([[[lindex $insts 0] getMaster] getWidth]) / $dbu}]
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
puts "OT_QC_SITES placed $placed of $nseq flops at [llength $sites] stage sites ($empty sites matched no flop)"
if {$placed < 0.9 * $nseq} { error "OT_QC_SITES: only $placed of $nseq flops matched a stage site" }
