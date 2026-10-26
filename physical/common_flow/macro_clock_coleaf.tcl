# Explicit E5 experiment: put a macro clock on one of its own interface-register
# clock leaves. TritonCTS's macro balancing left the macro 13..54ps early on GRT
# RC. Sharing the last driver removes the unmatched local-tree levels.
namespace eval ::ot_macro_coleaf {}
proc ::ot_macro_coleaf::xy {it} {
  set b [$it getBBox]
  return [list [expr {([$b xMin]+[$b xMax])/2.0}] [expr {([$b yMin]+[$b yMax])/2.0}]]
}
proc ::ot_macro_coleaf::driver {net} {
  set out {}
  foreach p [$net getITerms] { if {[$p isOutputSignal]} { lappend out $p } }
  if {[llength $out] != 1} { return "" }
  return [lindex $out 0]
}
proc ::ot_macro_coleaf::tap {net {depth 0}} {
  if {$depth > 40} { error "macro co-leaf clock path exceeds 40 buffers" }
  set d [driver $net]; if {$d eq ""} { return "" }
  set i [$d getInst]; set n [$i getName]
  if {[regexp {^ot_dtap_[0-9]+$} $n]} { return $n }
  if {![regexp {^(BUF|INV|CKBUF|CKINV|HB)} [[$i getMaster] getName]]} { return "" }
  set in {}
  foreach p [$i getITerms] { if {[$p isInputSignal] && [$p getSigType] ni {POWER GROUND}} { lappend in $p } }
  if {[llength $in] != 1} { return "" }
  set up [[lindex $in 0] getNet]
  if {$up eq "NULL" || $up eq ""} { return "" }
  return [tap $up [expr {$depth+1}]]
}
proc ::ot_macro_coleaf::registers {net {depth 0}} {
  set out {}
  foreach p [$net getITerms] {
    set i [$p getInst]; set m [$i getMaster]
    if {[$m isSequential] && ![$m isBlock]} { lappend out $i; continue }
    if {$depth == 0 && [regexp {^(BUF|INV|HB)} [$m getName]]} {
      foreach q [$i getITerms] {
        set n [$q getNet]
        if {[$q getSigType] in {POWER GROUND} || $n eq "NULL" || $n eq "" || $n eq $net || [$n getSigType] eq "CLOCK"} continue
        lappend out {*}[registers $n 1]
      }
    }
  }
  return $out
}
proc ::ot_macro_coleaf::plan {{max_um 100}} {
  set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]; set changes {}
  foreach i [$blk getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set clocks {}; set regs {}
    foreach p [$i getITerms] {
      set n [$p getNet]
      if {$n eq "NULL" || $n eq "" || [$p getSigType] in {POWER GROUND}} continue
      if {[$n getSigType] eq "CLOCK" && [$p isInputSignal]} { lappend clocks $p; continue }
      if {[$n getSigType] ne "CLOCK"} { lappend regs {*}[registers $n] }
    }
    foreach ck $clocks {
      set old [$ck getNet]; set root [tap $old]
      if {$root eq ""} { error "macro co-leaf cannot identify density tap for [$i getName]" }
      lassign [xy $ck] mx my
      set candidates [dict create]
      foreach r [lsort -unique $regs] {
        foreach p [$r getITerms] {
          set n [$p getNet]
          if {![$p isInputSignal] || $n eq "NULL" || $n eq "" || [$n getSigType] ne "CLOCK" || $n eq $old} continue
          if {[tap $n] ne $root} continue
          set d [driver $n]; if {$d eq ""} continue
          lassign [xy $d] dx dy
          set dist [expr {(abs($dx-$mx)+abs($dy-$my))/$u}]
          if {$dist > $max_um} continue
          set name [$n getName]
          if {![dict exists $candidates $name]} { dict set candidates $name [list $n $d $dist 0 $mx $my $dx $dy] }
          set row [dict get $candidates $name]; lset row 3 [expr {[lindex $row 3]+1}]; dict set candidates $name $row
        }
      }
      set best {}; set score 1e30
      dict for {nm row} $candidates {
        # Prefer the nearest shared driver; a larger IF leaf breaks equal-distance ties.
        set s [expr {[lindex $row 2]-0.001*[lindex $row 3]}]
        if {$s < $score} { set best $row; set score $s }
      }
      if {![llength $best]} { error "macro co-leaf no same-tap IF leaf within ${max_um}um of [$i getName]/[[$ck getMTerm] getName]" }
      lappend changes [list $ck $old {*}$best]
    }
  }
  return $changes
}
proc ::ot_macro_coleaf::apply {{report ""}} {
  set max_um [expr {[info exists ::env(OT_DTSH_MACRO_COLEAF_MAX_UM)] ? $::env(OT_DTSH_MACRO_COLEAF_MAX_UM) : 100}]
  # Plan all macros before changing any connection; missing IF leaves fail closed.
  set changes [plan $max_um]
  set f ""; if {$report ne ""} { set f [open $report w]; puts $f "macro\told_net\tnew_net\tdriver\twire_um\tinterface_regs\tmacro_x_dbu\tmacro_y_dbu\tdriver_x_dbu\tdriver_y_dbu" }
  foreach row $changes {
    lassign $row ck old new driver dist count mx my dx dy
    set text "[[$ck getInst] getName]\t[$old getName]\t[$new getName]\t[[$driver getInst] getName]\t$dist\t$count\t$mx\t$my\t$dx\t$dy"
    puts "OT_MACRO_COLEAF $text"
    if {$f ne ""} { puts $f $text }
    $ck disconnect; $ck connect $new
  }
  if {$f ne ""} { close $f }
  puts "OT_MACRO_COLEAF applied [llength $changes] macros, added_data_cycles=0"
}
