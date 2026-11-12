read_db $::env(ODB)
set blk [ord::get_db_block]; set u [$blk getDefUnits]
set bw 20.0; set W 1442.88; set H 1226.88
array set a {}; array set hp {}
foreach i [$blk getInsts] {
  set m [$i getMaster]; if {[$m getType] ne "CORE" && ![string match "CORE*" [$m getType]]} continue
  if {[string match "*TAPCELL*" [$m getName]] || [string match "*FILLER*" [$m getName]] || [string match "*DECAP*" [$m getName]]} continue
  set bb [$i getBBox]; set x [expr {([$bb xMin]+[$bb xMax])/2.0/$u}]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]
  set k "[expr {int($x/$bw)}],[expr {int($y/$bw)}]"
  set ar [expr {double([$m getWidth])*[$m getHeight]/$u/$u}]
  if {![info exists a($k)]} {set a($k) 0.0}
  set a($k) [expr {$a($k)+$ar}]
  if {[string match "*u_hp_ft*" [$i getName]]} {if {![info exists hp($k)]} {set hp($k) 0}; incr hp($k)}
}
foreach face {S N W E core} {set s($face) 0.0; set n($face) 0; set mx($face) 0.0; set o90($face) 0; set hpc($face) 0; set hpb($face) {}}
foreach k [array names a] {
  lassign [split $k ,] bx by
  set x0 [expr {$bx*$bw}]; set y0 [expr {$by*$bw}]
  if {$y0 < 40} {set f S} elseif {$y0+$bw > $H-40} {set f N} elseif {$x0 < 40} {set f W} elseif {$x0+$bw > $W-40} {set f E} else {set f core}
  set d [expr {$a($k)/($bw*$bw)}]
  set s($f) [expr {$s($f)+$d}]; incr n($f); if {$d>$mx($f)} {set mx($f) $d}; if {$d>0.9} {incr o90($f)}
  if {[info exists hp($k)]} {incr hpc($f) $hp($k); lappend hpb($f) $d}
}
foreach f {S N W E core} {
  set hm 0.0; set hx 0.0; foreach d $hpb($f) {set hm [expr {$hm+$d}]; if {$d>$hx} {set hx $d}}
  if {[llength $hpb($f)]} {set hm [expr {$hm/[llength $hpb($f)]}]}
  puts [format "T41DENS face %s bins %d mean %.3f max %.3f bins>0.90 %d | hp_cells %d hp_bins %d hp_bin_mean %.3f hp_bin_max %.3f" $f $n($f) [expr {$n($f)?$s($f)/$n($f):0}] $mx($f) $o90($f) $hpc($f) [llength $hpb($f)] $hm $hx]
}
