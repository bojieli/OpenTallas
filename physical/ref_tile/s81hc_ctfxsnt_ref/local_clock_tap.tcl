# Physical repair for the measured ul_out[15] clock return: old leaf x235um
# drove its pin-owned clone x71um through a clock repeater, adding ~56ps skew.
# Retap only to an existing non-inverting leaf on the SAME external clock root,
# within40um, retaining every real clock buffer, data connection and constraint.
proc ot_nt_clock_root {net} {
  for {set hop 0} {$hop < 40} {incr hop} {
    set ports {}
    foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT"} { lappend ports [$bt getName] } }
    if {[llength $ports]} { return [lsort $ports] }
    set driver ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set driver [$it getInst]; break } }
    if {$driver eq "" || ![string match "BUF*" [[$driver getMaster] getName]]} { return {} }
    set input [$driver findITerm A]
    if {$input eq "NULL"} { return {} }
    set net [$input getNet]
    if {$net eq "NULL"} { return {} }
  }
  return {}
}
proc ot_nt_in_cts {} {
  # The generator installs this wrapper only in PRE_CTS; each later ORFS
  # stage/signoff replay starts a fresh interpreter. cts_args belongs to CTS.
  return [expr {[llength [info procs ::ot_ref_cts_boundary_orig]] && [info exists ::cts_args]}]
}
proc ot_nt_clock_leaf {net} {
  for {set hop 0} {$hop < 40} {incr hop} {
    set driver ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set driver [$it getInst]; break } }
    if {$driver eq "" || ![string match "BUF*" [[$driver getMaster] getName]]} { return "" }
    if {[string match "clkbuf_leaf_*" [$driver getName]]} { return $driver }
    set input [$driver findITerm A]
    if {$input eq "NULL"} { return "" }
    set net [$input getNet]
  }
  return ""
}
set ot_nt_block [ord::get_db_block]
set ot_nt_leaves {}
foreach inst [$ot_nt_block getInsts] {
  if {![string match "clkbuf_leaf_*" [$inst getName]]} continue
  if {![string match "BUF*" [[$inst getMaster] getName]]} continue
  foreach it [$inst getITerms] {
    if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {
      lappend ot_nt_leaves [list [$inst getName] $inst [$it getNet]]
    }
  }
}
# This boundary hook is also sourced before CTS; there is then no tree to repair.
if {[llength $ot_nt_leaves]} {
  set ot_nt_bt [$ot_nt_block findBTerm {ul_out[15]}]
  if {$ot_nt_bt eq "NULL"} { error "NORM_CLOCK_TAP: ul_out15 missing" }
  set ot_nt_net [$ot_nt_bt getNet]; set ot_nt_ff ""
  for {set hop 0} {$hop < 8} {incr hop} {
    set driver ""
    foreach it [$ot_nt_net getITerms] { if {[$it isOutputSignal]} { set driver [$it getInst]; break } }
    if {$driver eq ""} break
    set master [[$driver getMaster] getName]
    if {[string match "DFF*" $master] || [string match "ASYNC_DFF*" $master]} { set ot_nt_ff $driver; break }
    if {![regexp {^(BUF|INV|HB)} $master]} break
    set input [$driver findITerm A]
    if {$input eq "NULL"} break
    set ot_nt_net [$input getNet]
  }
  if {$ot_nt_ff eq ""} { error "NORM_CLOCK_TAP: ul_out15 has no dedicated launch FF" }
  set ot_nt_clk [$ot_nt_ff findITerm CLK]
  set ot_nt_old [$ot_nt_clk getNet]
  set ot_nt_root [ot_nt_clock_root $ot_nt_old]
  if {$ot_nt_root ne {clk}} { error "NORM_CLOCK_TAP: unexpected/inverting clock root $ot_nt_root" }
  lassign [$ot_nt_ff getLocation] fx fy
  set ot_nt_best {}; set ot_nt_dist Inf
  foreach item [lsort -index 0 $ot_nt_leaves] {
    lassign $item name inst net
    if {[ot_nt_clock_root $net] ne $ot_nt_root} continue
    lassign [$inst getLocation] x y
    set distance [expr {abs($x - $fx) + abs($y - $fy)}]
    if {$distance < $ot_nt_dist} { set ot_nt_best $item; set ot_nt_dist $distance }
  }
  set ot_nt_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  if {$ot_nt_best eq "" || $ot_nt_dist > 40 * $ot_nt_dbu} { error "NORM_CLOCK_TAP: no same-root local leaf within40um" }
  lassign $ot_nt_best name inst net
  set ot_nt_current [ot_nt_clock_leaf $ot_nt_old]
  set ot_nt_current_dist Inf
  if {$ot_nt_current ne ""} {
    lassign [$ot_nt_current getLocation] x y
    set ot_nt_current_dist [expr {abs($x - $fx) + abs($y - $fy)}]
  }
  if {$ot_nt_current_dist > 40 * $ot_nt_dbu} {
    # Never mutate a routed ODB or a signoff replay: the clock route is rebuilt
    # only inside the actual CTS step, then later hooks merely verify it.
    if {![ot_nt_in_cts]} { error "NORM_CLOCK_TAP: remote leaf remains outside CTS; rerun physical CTS" }
    $ot_nt_clk disconnect
    $ot_nt_clk connect $net
    puts "NORM_CLOCK_TAP [$ot_nt_ff getName]/CLK: [$ot_nt_old getName] -> [$net getName], root $ot_nt_root, local leaf $name distance [expr {$ot_nt_dist / double($ot_nt_dbu)}]um"
  }
}
