# DIE-HEAD-33 10-29 (kit-local, tag +ffp): ring flop band order follows the INPUT PIN coordinate of each flop's data cone
# (locality: a bit's DEPTH slots, its read-select register and the writer-reset counter sit at the band height of the pin
# that feeds them).  Key = y of the input pin reached first (fewest combinational levels) backward from the flop D pin
# (stop at sequential cells and clock nets); a read-select register u_dsel/y[j] of channel dch[c] takes its bit's pin
# (bit = c*WCH + j); flops with no pin keep their name key at the band bottom.  Placement only, 0 cycles, 0 flops.
proc cland_isseq {i} { return [regexp {DFF|DHL|DLL|SDF|ICG} [[$i getMaster] getName]] }
proc cland_cone_pin {i} {
 global ff_dbu
 set it [$i findITerm D]; if {$it eq "NULL"} { return {} }
 set front [list [$it getNet]]; set seen {}
 for {set lv 0} {$lv < 12} {incr lv} {
  set hits {}; set nf {}
  foreach n $front {
   if {$n eq "NULL" || $n eq ""} continue
   set nn [$n getName]
   if {[dict exists $seen $nn] || [$n getSigType] eq "CLOCK"} continue
   dict set seen $nn 1
   foreach bt [$n getBTerms] {
    if {[$bt getIoType] ne "INPUT"} continue
    set bb [$bt getBBox]; lappend hits [list [expr {([$bb yMin]+[$bb yMax])/2.0/$ff_dbu}] [$bt getName]]
   }
   foreach t [$n getITerms] {
    if {![$t isOutputSignal]} continue
    set di [$t getInst]
    if {[cland_isseq $di]} continue
    foreach u [$di getITerms] { if {[$u isInputSignal]} { lappend nf [$u getNet] } }
   }
  }
  if {[llength $hits]} { return [lindex [lsort -real -index 0 $hits] 0] }
  set front $nf
 }
 return {}
}
proc cland_ffp_keys {ffl} {
 # ffl: list of insts -> list of {key inst}
 set out {}; set bity {}; set pend {}; set wch 0
 foreach i $ffl {
  set nm [$i getName]
  if {[regexp {dch\\?\[([0-9]+)\\?\]\.u_dsel/y\\?\[([0-9]+)\\?\]} $nm -> c j]} { lappend pend [list $c $j $i]; if {$c == 0 && $j+1 > $wch} { set wch [expr {$j+1}] }; continue }
  set h [cland_cone_pin $i]
  if {$h eq {} && [regexp {s_d\\?\[([0-9]+)\\?\]\\?\[([0-9]+)\\?\]} $nm -> s k]} { lappend pend [list -1 $k $i $s]; continue }
  if {$h eq {}} { lappend out [list [format {0|%s} $nm] $i]; continue }
  lassign $h y pin
  if {[regexp {^([^\[]*)\[([0-9]+)\\?\]\\?\[([0-9]+)\\?\]} $nm -> b s k]} { dict set bity $k $y } else { set s 9 }
  lappend out [list [format {1|%012.4f|%04d|%s} $y $s $nm] $i]
 }
 foreach p $pend {
  lassign $p c j i s
  if {$c < 0} { set k $j } else { set k [expr {$c*$wch+$j}]; set s 9998 }
  if {![dict exists $bity $k]} { error "OT_CLAND_FFP no slot pin for [$i getName] (bit $k)" }
  lappend out [list [format {1|%012.4f|%04d|%s} [dict get $bity $k] $s [$i getName]] $i]
 }
 return $out
}
