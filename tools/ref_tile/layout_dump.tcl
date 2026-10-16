# layout_dump.tcl (OWNER RULE 20:45 PT 2026-10-15): dump the geometry tools/ref_tile/layout_png.py draws, from the
# design loaded in OpenROAD (read_db <any .odb> first).  env: OT_LAYOUT_OUT (json path), OT_LAYOUT_CLOCKS (comma list
# of clock ports), OT_LAYOUT_BINS (density grid, default 64), OT_LAYOUT_TOP (title).
# JSON: die, blocks [name master x0 y0 x1 y1] (hard macros / hardened children), pins [name layer x0 y0 x1 y1],
# pg [net layer x0 y0 x1 y1] (special wires of the top PG layer), density {nx ny grid} (placed std-cell area / bin area;
# null bins = covered by a block), stats {fill, std_area, block_area, die_area}.
set ot_ld_block [ord::get_db_block]
set ot_ld_dbu [expr {double([$ot_ld_block getDbUnitsPerMicron])}]
proc ot_ld_um {v} { return [format %.3f [expr {$v / $::ot_ld_dbu}]] }
proc ot_ld_q {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }
set ot_ld_die [$ot_ld_block getDieArea]
set X0 [$ot_ld_die xMin]; set Y0 [$ot_ld_die yMin]; set X1 [$ot_ld_die xMax]; set Y1 [$ot_ld_die yMax]
set nb [expr {[info exists ::env(OT_LAYOUT_BINS)] ? $::env(OT_LAYOUT_BINS) : 64}]
set bw [expr {double($X1 - $X0) / $nb}]; set bh [expr {double($Y1 - $Y0) / $nb}]
for {set i 0} {$i < $nb * $nb} {incr i} { set ot_ld_g($i) 0.0; set ot_ld_cov($i) 0 }
set blocks {}; set std 0.0; set barea 0.0
foreach inst [$ot_ld_block getInsts] {
  set m [$inst getMaster]
  set bb [$inst getBBox]
  set a [expr {double([$bb getDX]) * [$bb getDY]}]
  if {[$m isBlock]} {
    lappend blocks "\[[ot_ld_q [$inst getName]], [ot_ld_q [$m getName]], [ot_ld_um [$bb xMin]], [ot_ld_um [$bb yMin]], [ot_ld_um [$bb xMax]], [ot_ld_um [$bb yMax]]\]"
    set barea [expr {$barea + $a}]
    for {set j [expr {int(([$bb yMin] - $Y0) / $bh)}]} {$j <= min($nb - 1, int(([$bb yMax] - $Y0 - 1) / $bh))} {incr j} {
      for {set i [expr {int(([$bb xMin] - $X0) / $bw)}]} {$i <= min($nb - 1, int(([$bb xMax] - $X0 - 1) / $bw))} {incr i} {
        if {$i >= 0 && $j >= 0} { set ot_ld_cov([expr {$j * $nb + $i}]) 1 }
      }
    }
    continue
  }
  if {[$m getType] ne "CORE" && ![string match "CORE*" [$m getType]]} { continue }
  if {[string match "TAPCELL*" [$m getName]] || [string match "FILLER*" [$m getName]] || [string match "DECAP*" [$m getName]]} { continue }
  set std [expr {$std + $a}]
  if {[$inst getPlacementStatus] eq "NONE" || [$inst getPlacementStatus] eq "UNPLACED"} { continue }
  set i [expr {min($nb - 1, max(0, int((([$bb xMin] + [$bb xMax]) / 2.0 - $X0) / $bw)))}]
  set j [expr {min($nb - 1, max(0, int((([$bb yMin] + [$bb yMax]) / 2.0 - $Y0) / $bh)))}]
  set k [expr {$j * $nb + $i}]
  set ot_ld_g($k) [expr {$ot_ld_g($k) + $a}]
}
set grid {}
for {set k 0} {$k < $nb * $nb} {incr k} {
  lappend grid [expr {$ot_ld_cov($k) ? "null" : [format %.3f [expr {$ot_ld_g($k) / ($bw * $bh)}]]}]
}
set pins {}
foreach bt [$ot_ld_block getBTerms] {
  foreach bp [$bt getBPins] {
    foreach box [$bp getBoxes] {
      lappend pins "\[[ot_ld_q [$bt getName]], [ot_ld_q [[$box getTechLayer] getName]], [ot_ld_um [$box xMin]], [ot_ld_um [$box yMin]], [ot_ld_um [$box xMax]], [ot_ld_um [$box yMax]]\]"
    }
  }
}
set pg {}; set toplvl -1; set pgw {}
foreach net [$ot_ld_block getNets] {
  if {[$net getSigType] ne "POWER" && [$net getSigType] ne "GROUND"} { continue }
  foreach sw [$net getSWires] {
    foreach sb [$sw getWires] {
      if {[$sb isVia]} { continue }
      set L [$sb getTechLayer]
      set lv [$L getRoutingLevel]
      if {$lv > $toplvl} { set toplvl $lv }
      lappend pgw [list $lv [$net getName] [$L getName] [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
    }
  }
}
foreach w $pgw {
  lassign $w lv n ln a b c d
  if {$lv == $toplvl && [llength $pg] < 4000} { lappend pg "\[[ot_ld_q $n], [ot_ld_q $ln], [ot_ld_um $a], [ot_ld_um $b], [ot_ld_um $c], [ot_ld_um $d]\]" }
}
set clocks {}
if {[info exists ::env(OT_LAYOUT_CLOCKS)]} { foreach c [split $::env(OT_LAYOUT_CLOCKS) ","] { if {$c ne ""} { lappend clocks [ot_ld_q $c] } } }
set dA [expr {double($X1 - $X0) * ($Y1 - $Y0)}]
set top [expr {[info exists ::env(OT_LAYOUT_TOP)] ? $::env(OT_LAYOUT_TOP) : [$ot_ld_block getName]}]
set f [open $::env(OT_LAYOUT_OUT) w]
puts $f "{\"top\": [ot_ld_q $top], \"die\": \[[ot_ld_um $X0], [ot_ld_um $Y0], [ot_ld_um $X1], [ot_ld_um $Y1]\],"
puts $f " \"stats\": {\"fill\": [format %.3f [expr {($std + $barea) / $dA}]], \"std_area\": [format %.1f [expr {$std / $ot_ld_dbu / $ot_ld_dbu}]], \"block_area\": [format %.1f [expr {$barea / $ot_ld_dbu / $ot_ld_dbu}]], \"die_area\": [format %.1f [expr {$dA / $ot_ld_dbu / $ot_ld_dbu}]]},"
puts $f " \"clocks\": \[[join $clocks ", "]\],"
puts $f " \"blocks\": \[[join $blocks ",\n  "]\],"
puts $f " \"pins\": \[[join $pins ",\n  "]\],"
puts $f " \"pg\": \[[join $pg ",\n  "]\],"
puts $f " \"density\": {\"nx\": $nb, \"ny\": $nb, \"grid\": \[[join $grid ", "]\]}}"
close $f
puts "OT_LAYOUT_DUMP $::env(OT_LAYOUT_OUT) blocks [llength $blocks] pins [llength $pins] pg [llength $pg] fill [format %.3f [expr {($std + $barea) / $dA}]]"
