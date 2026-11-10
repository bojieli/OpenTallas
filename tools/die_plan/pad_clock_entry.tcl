# GENERATED-COPY of tools/die_plan/pad_clock_entry.tcl (PRE_CTS, opt-in plan clock.pad_clock pins[].entries;
# S81 RCK2-1109, COORD loopgap-155x-1109).  A second entry of an input pad clock: a plan-placed trunk from the pad
# pin (one `cell` per station, hops <= 405 um, checked by pad_clock.check_entries) ends in an entry driver; its output
# net (the entry name) takes every std-cell clock sink whose pin lies inside one of the entry regions plus the declared
# macro clock pins.  TritonCTS then builds one local tree per entry under the same clock (the pad net keeps the rest)
# and its latency balancing equalises them (station-to-station nets have one sink, so CTS leaves them as planned).
# Data: ::pce_entries {port entry cell {stations} {x y} {regions} {{module pin} ...} ?{take ports}?} (pad_clock.entries_tcl).
# S81 LEAF-CLKENTRY-1109 (opt-in plan clock.tap_entries): a core-clock REGIONAL entry uses the same trunk from a die-spine
# tap port; the optional 8th field lists the tap ports (clk / clk_t<k>) whose nets give up their std-cell sinks inside the
# regions (after the nearest-tap split of clock_taps.tcl), so one entry can take a channel that two taps share.  Absent
# 8th field = the sinks of `port` only (the RCK2 pad-clock form, unchanged).
set pce_blk [ord::get_db_block]
set pce_db [ord::get_db]
set pce_dbu [$pce_blk getDbUnitsPerMicron]
proc pce_site {x y} {
  # nearest row (and its orientation) that spans x; x snapped to that row's site grid
  global pce_blk pce_dbu
  set X [expr {round($x * $pce_dbu)}]; set Y [expr {round($y * $pce_dbu)}]
  set best ""
  foreach r [$pce_blk getRows] {
    set bb [$r getBBox]
    if {$X < [$bb xMin] || $X > [$bb xMax]} continue
    set d [expr {abs([$bb yMin] - $Y)}]
    if {$best eq "" || $d < [lindex $best 0]} { set best [list $d $r] }
  }
  if {$best eq ""} { error "PAD_CLOCK_ENTRY: no row spans ($x, $y)" }
  set r [lindex $best 1]; set bb [$r getBBox]
  set sw [[$r getSite] getWidth]
  set sx [expr {[$bb xMin] + round(($X - [$bb xMin]) / double($sw)) * $sw}]
  return [list $sx [$bb yMin] [$r getOrient]]
}
proc pce_cell {name master x y} {
  global pce_blk pce_db
  set m [$pce_db findMaster $master]
  if {$m eq "NULL"} { error "PAD_CLOCK_ENTRY: no master $master" }
  set i [odb::dbInst_create $pce_blk $m $name]
  if {$i eq "NULL"} { error "PAD_CLOCK_ENTRY: cannot create $name" }
  lassign [pce_site $x $y] sx sy so
  $i setOrient $so
  $i setLocation $sx $sy
  $i setPlacementStatus PLACED
  return $i
}
proc pce_pin {inst dir} {
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ne "SIGNAL"} continue
    if {$dir eq "out" && [$mt getIoType] eq "OUTPUT"} { return $it }
    if {$dir eq "in" && [$mt getIoType] eq "INPUT"} { return $it }
  }
  error "PAD_CLOCK_ENTRY: [[$inst getMaster] getName] has no $dir signal pin"
}
proc pce_in {x y regs} {
  foreach r $regs { lassign $r x0 y0 x1 y1; if {$x >= $x0 && $x <= $x1 && $y >= $y0 && $y <= $y1} { return 1 } }
  return 0
}
set pce_tap_src {}
foreach pce_e $::pce_entries {
  lassign $pce_e port ename cell stations exy regions msinks takes
  set bt [$pce_blk findBTerm "${port}\[0\]"]
  if {$bt eq "NULL"} { set bt [$pce_blk findBTerm $port] }
  if {$bt eq "NULL"} { error "PAD_CLOCK_ENTRY: pad clock port $port not in the block" }
  set root [$bt getNet]
  if {$root eq "NULL"} { error "PAD_CLOCK_ENTRY: pad clock port $port has no net" }
  # snapshot the sinks before the trunk taps the root net (and, for a tap entry, the nets of every take port)
  set srcnets [list $root]
  foreach tp $takes {
    if {$tp eq $port} continue
    set tb [$pce_blk findBTerm $tp]
    if {$tb eq "NULL" || [$tb getNet] eq "NULL"} { error "PAD_CLOCK_ENTRY: $port entry $ename take port $tp not in the block" }
    lappend srcnets [$tb getNet]
  }
  set sinks {}
  foreach sn $srcnets {
    foreach it [$sn getITerms] { if {[$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} { lappend sinks $it } }
  }
  set src $root; set k 0; set pts [concat $stations [list $exy]]; set first ""
  foreach pt $pts {
    lassign $pt x y
    set last [expr {$k == [llength $pts] - 1}]
    set iname [expr {$last ? "pce_${ename}_drv" : "pce_${ename}_s$k"}]
    set i [pce_cell $iname $cell $x $y]
    set a [pce_pin $i in]
    $a connect $src
    if {$first eq ""} { set first $a }
    set nn [expr {$last ? $ename : "pce_${ename}_n$k"}]
    set net [odb::dbNet_create $pce_blk $nn]
    if {$net eq "NULL"} { error "PAD_CLOCK_ENTRY: net $nn exists" }
    $net setSigType CLOCK
    [pce_pin $i out] connect $net
    set src $net; incr k
  }
  # No dont_touch on the trunk: TritonCTS re-hangs station s0's input on its pad-net tree (ODB-0370 on a dont_touch
  # s0) and skips the 1-sink inter-station nets itself (CTS-0041); -repair_clock_nets may add a slew repeater on a
  # station net (RSZ-3006 on a dont_touch net, t14 probe 11-09).  The trunk cells are ordinary PLACED clock buffers.
  set moved 0; set mac 0; set left 0; set want {}
  foreach ms $msinks { dict set want [join $ms /] 0 }
  foreach it $sinks {
    set inst [$it getInst]; set mt [$it getMTerm]
    if {[[$inst getMaster] isBlock]} {
      set key "[[$inst getMaster] getName]/[$mt getName]"
      if {[dict exists $want $key]} {
        $it disconnect; $it connect $src; incr moved; incr mac; dict incr want $key
      } else { incr left }
      continue
    }
    set bb [$it getBBox]
    set px [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $pce_dbu}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $pce_dbu}]
    if {[pce_in $px $py $regions]} { $it disconnect; $it connect $src; incr moved } else { incr left }
  }
  dict for {key cnt} $want { if {$cnt == 0} { error "PAD_CLOCK_ENTRY: $port entry $ename: declared macro sink $key not on the pad net" } }
  if {$moved == 0} { error "PAD_CLOCK_ENTRY: $port entry $ename moved no sink (regions $regions)" }
  puts "OT_PAD_CLOCK_ENTRY $port -> $ename: [llength $pts] x $cell (trunk [expr {[llength $pts] - 1}] stations + driver at ([lindex $exy 0], [lindex $exy 1])), sinks moved $moved ($mac macro pins), left on $port $left"
  if {[llength $takes]} { dict lappend pce_tap_src $port [list $first $cell] }
}
# Tap entries only: the trunk inputs must hang at the tap ROOT, not at the leaves of the tap's own CTS tree (probe t21
# 11-09: entry driver input at 185-231 ps behind the clk_t9 tree, entry sinks 383-400 ps).  The sinks a tap entry
# source port keeps go behind one root buffer at the tap pin (pce_<port>_root -> net pce_<port>_rest), so the port net
# carries only first-stage trunk inputs + that buffer and TritonCTS builds the remaining local tree under the buffer.
dict for {port fl} $pce_tap_src {
  set bt [$pce_blk findBTerm $port]
  set root [$bt getNet]
  set firsts [lmap f $fl {lindex $f 0}]
  set rest {}
  foreach it [$root getITerms] {
    if {[lsearch -exact $firsts $it] >= 0} continue
    if {[$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} { lappend rest $it }
  }
  if {![llength $rest]} continue
  set bb [$bt getBBox]
  set i [pce_cell "pce_${port}_root" [lindex $fl 0 1] [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $pce_dbu}] \
           [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $pce_dbu}]]
  [pce_pin $i in] connect $root
  set net [odb::dbNet_create $pce_blk "pce_${port}_rest"]
  if {$net eq "NULL"} { error "PAD_CLOCK_ENTRY: net pce_${port}_rest exists" }
  $net setSigType CLOCK
  [pce_pin $i out] connect $net
  foreach it $rest { $it disconnect; $it connect $net }
  puts "OT_PAD_CLOCK_ENTRY $port root buffer pce_${port}_root: [llength $rest] sinks behind it, [llength $firsts] trunk input(s) at the tap root"
}
