# QW-CB16A0-3 10-20 fabric_sites_place_n.tcl (kits qfd_c_b16_fulln / fullnb): fullm sites hook with ring bays as
# deterministic uniform FIRM lattices instead of EXCLUSIVE GPL regions (root cause of fullmb/mr/mbr GPL-0305: stacked
# identical-net ring flops in a region never separate).  The fullk ODB-0359 root cause was a DUPLICATED site prefix
# (30 stages had both a 5-column and a 7-column line -> the same flops were placed twice); this hook refuses duplicates.
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
set seen [dict create]
set seenp [dict create]
foreach s $sites {
  lassign $s p x y xlo xhi ylo yhi
  if {[dict exists $seenp $p]} { error "OT_QC_SITES duplicate site prefix $p (fullk ODB-0359 root cause)" }
  dict set seenp $p 1
  set insts [dict get $byp $p]
  if {![llength $insts]} { incr empty; continue }
  set fw [expr {double([[[lindex $insts 0] getMaster] getWidth]) / $dbu}]
  if {$ylo ne "" && $yhi ne ""} {
    # QW-CB16A0-3 fulln: a ring bay is a DETERMINISTIC UNIFORM LATTICE of FIRM flops (no GPL ownership).
    # fullmb/fullmr/fullmbr GPL-0305: GPL initial place stacked up to 145 identical-net ring flops on one point of a
    # 43.2 um EXCLUSIVE region (qc_bay_77 overflow stuck 0.22 > target, penalty 1e33 -> NaN).  The flops are spread here
    # over every row of the bay at an even, site-snapped pitch, FIRM through GPL/resizer, released to PLACED for DPL.
    set n [llength $insts]
    set rys {}
    foreach rw [$blk getRows] {
      set bb [$rw getBBox]
      set ry0 [expr {[$bb yMin]/double($dbu)}]; set ry1 [expr {[$bb yMax]/double($dbu)}]
      set rx0 [expr {[$bb xMin]/double($dbu)}]; set rx1 [expr {[$bb xMax]/double($dbu)}]
      if {$ry0 >= $ylo + 0.26 && $ry1 <= $yhi - 0.26 && $rx0 <= $xlo + 1.0 && $rx1 >= $xhi - 1.0} { lappend rys $ry0 }
    }
    set rys [lsort -real -unique $rys]
    set R [llength $rys]
    if {$R < 1} { error "QC_BAY no full-width row inside bay $p" }
    set site 0.054
    set xl [expr {$xlo + 1.0}]; set xr [expr {$xhi - 1.0 - $fw}]
    set S [expr {int(floor(($xr - $xl) / $fw)) + 1}]
    set area [expr {$n * $fw * 0.27}]
    set capacity [expr {$R * ($xhi - $xlo) * 0.27}]
    if {$n > $R * $S || $area / $capacity > 0.35} {error "QC_BAY insufficient legal row capacity $p n=$n rows=$R slots=$S fill=[expr {$area/$capacity}]"}
    set c [expr {int(ceil(double($n) / $R))}]
    set xp [expr {$c > 1 ? ($xr - $xl) / double($c - 1) : 0.0}]
    if {$c > 1 && $xp < $fw} { error "QC_BAY pitch below cell width $p" }
    set k 0
    foreach i $insts {
      if {[dict exists $seen [$i getName]]} { error "QC_BAY instance placed twice [$i getName] ($p and [dict get $seen [$i getName]])" }
      dict set seen [$i getName] $p
      set r [expr {$k % $R}]; set col [expr {$k / $R}]
      # alternate the column phase per row so neighbouring rows interleave (even 2-D density)
      set cx [expr {$xl + $col * $xp + (($r % 2) ? 0.5 * $xp : 0.0)}]
      if {$cx > $xr} { set cx [expr {$xl + $col * $xp}] }
      set cx [expr {round($cx / $site) * $site}]
      $i setLocation [expr {round($cx * $dbu)}] [expr {round([lindex $rys $r] * $dbu)}]
      $i setPlacementStatus FIRM
      puts $out [$i getName]
      incr k; incr placed
    }
    puts "QC_BAY lattice=$nbay prefix=$p flops=$n rows=$R per_row=$c xpitch=[format %.3f $xp] fill=[format %.4f [expr {$area/$capacity}]]"
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
    if {[dict exists $seen [$i getName]]} { error "OT_QC_SITES instance placed twice [$i getName]" }
    dict set seen [$i getName] $p
    $i setLocation [expr {round($cx * $dbu)}] [expr {round($cy * $dbu)}]
    $i setPlacementStatus FIRM
    puts $out [$i getName]
    incr k; incr placed
  }
}
close $out
puts "OT_QC_SITES placed $placed of $nseq flops at [llength $sites] stage sites ($nbay ring bays, $empty sites matched no flop)"
if {$placed < 0.9 * $nseq} { error "OT_QC_SITES: only $placed of $nseq flops matched a stage site" }
