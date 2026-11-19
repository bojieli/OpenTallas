# GENERATED-COPY of tools/die_plan/pad_clock_trunk.tcl (PRE_CTS, opt-in plan clock.pad_clock pins[].die_trunk with host "type";
# FABLE-FIX-S81-SERDES 11-18, COORD ruling 11-18: stations inside a hard type are built by the kit, the die cannot own them).
# The kit port of the pad clock sits at from_xy_um (pad_clock.io_tcl); this hook builds the plan chain of repeaters
# (one `cell` per station, hops <= 405 um checked by pad_clock.die_trunks) and puts EVERY load the port net has at that moment
# behind the last station: plain sinks, regional roots, star legs alike, so it is sourced after the other pad-clock hooks and
# is independent of the in-type clock form.  Same port, clock, flops, constraints and cycles; ordinary PLACED clock buffers
# (pct_<port>_s<k>).  A station must lie within OT_PCT_SNAP_UM (default 6) of a placement row: the plan gives legal sites.
# Data: ::pct_trunks {port cell {{x y} ...}} (pad_clock.trunk_tcl).  pct_report (POST_CTS, cts_post.tcl) prints the arrival
# of the trunk end (propagated clock, placement RC): OT_PAD_CLOCK_TRUNK ... end_arrival_ps.
set pct_blk [ord::get_db_block]
set pct_u [expr {double([$pct_blk getDbUnitsPerMicron])}]
set pct_snap [expr {[info exists ::env(OT_PCT_SNAP_UM)] && $::env(OT_PCT_SNAP_UM) ne "" ? $::env(OT_PCT_SNAP_UM) : 6.0}]
set ::pct_ends {}
proc pct_site {x y w} {
  # nearest row that holds a cell of width w at x; fails beyond the snap distance (never a silent far move)
  global pct_blk pct_u pct_snap
  set X [expr {round($x * $pct_u)}]; set Y [expr {round($y * $pct_u)}]; set best ""
  foreach r [$pct_blk getRows] {
    set bb [$r getBBox]
    if {$X < [$bb xMin] || $X + $w > [$bb xMax]} continue
    set d [expr {abs([$bb yMin] - $Y)}]
    if {$best eq "" || $d < [lindex $best 0]} { set best [list $d $r] }
  }
  if {$best eq "" || [lindex $best 0] > $pct_snap * $pct_u} {
    error "PAD_CLOCK_TRUNK: no placement row within $pct_snap um of station ($x, $y): give the plan a legal site"
  }
  set r [lindex $best 1]; set bb [$r getBBox]; set sw [[$r getSite] getWidth]
  return [list [expr {[$bb xMin] + round(($X - [$bb xMin]) / double($sw)) * $sw}] [$bb yMin] [$r getOrient]]
}
foreach pct_t $::pct_trunks {
  lassign $pct_t pct_port pct_cell pct_st
  set pct_bt [$pct_blk findBTerm "${pct_port}\[0\]"]
  if {$pct_bt eq "NULL"} { set pct_bt [$pct_blk findBTerm $pct_port] }
  if {$pct_bt eq "NULL"} { error "PAD_CLOCK_TRUNK: pad clock port $pct_port not in the block" }
  set pct_root [$pct_bt getNet]
  if {[$pct_blk findInst pct_${pct_port}_s0] ne "NULL"} continue
  set pct_m [[ord::get_db] findMaster $pct_cell]
  if {$pct_m eq "NULL"} { error "PAD_CLOCK_TRUNK: no master $pct_cell" }
  set pct_loads {}
  foreach pct_it [$pct_root getITerms] {
    if {[$pct_it isInputSignal] || [[$pct_it getMTerm] getSigType] eq "CLOCK"} { lappend pct_loads $pct_it }
  }
  if {![llength $pct_loads]} { error "PAD_CLOCK_TRUNK: $pct_port has no load" }
  set pct_src $pct_root; set pct_k 0; set pct_last ""
  foreach pct_pt $pct_st {
    lassign $pct_pt pct_x pct_y
    set pct_i [odb::dbInst_create $pct_blk $pct_m pct_${pct_port}_s$pct_k]
    lassign [pct_site $pct_x $pct_y [$pct_m getWidth]] pct_sx pct_sy pct_so
    $pct_i setOrient $pct_so; $pct_i setLocation $pct_sx $pct_sy; $pct_i setPlacementStatus PLACED
    set pct_in ""; set pct_out ""
    foreach pct_it [$pct_i getITerms] {
      set pct_mt [$pct_it getMTerm]
      if {[$pct_mt getSigType] ne "SIGNAL"} continue
      if {[$pct_mt getIoType] eq "INPUT"} { set pct_in $pct_it } elseif {[$pct_mt getIoType] eq "OUTPUT"} { set pct_out $pct_it }
    }
    if {$pct_in eq "" || $pct_out eq ""} { error "PAD_CLOCK_TRUNK: $pct_cell is not a one-input buffer" }
    $pct_in connect $pct_src
    set pct_src [odb::dbNet_create $pct_blk pct_${pct_port}_n$pct_k]
    if {$pct_src eq "NULL"} { error "PAD_CLOCK_TRUNK: net pct_${pct_port}_n$pct_k exists" }
    $pct_src setSigType CLOCK
    $pct_out connect $pct_src
    set pct_last $pct_i; incr pct_k
  }
  if {!$pct_k} continue
  foreach pct_it $pct_loads { $pct_it disconnect; $pct_it connect $pct_src }
  lappend ::pct_ends [list $pct_port [$pct_last getName] [[$pct_out getMTerm] getName] $pct_k [llength $pct_loads]]
  puts "OT_PAD_CLOCK_TRUNK $pct_port: $pct_k x $pct_cell stations built by the kit, [llength $pct_loads] load(s) of the port net behind [$pct_last getName]"
}
proc pct_report {} {
  # arrival of each trunk end, same source edge, propagated clock, placement RC (information; the routed sign-off decides)
  if {![llength $::pct_ends]} return
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
  foreach e $::pct_ends {
    lassign $e port inst pin k loads
    set a ""
    catch { set a [get_property [get_pins $inst/$pin] arrival_max_rise] }
    if {$a ne "" && ![string match *INF $a] && abs($a) < 1.0} { set a [expr {$a * 1e12}] }
    if {$a eq "" || [string match *INF $a]} { puts "OT_PAD_CLOCK_TRUNK $port end $inst/$pin: no arrival (WARN)"; continue }
    puts [format "OT_PAD_CLOCK_TRUNK %s end %s/%s stations %d end_arrival_ps %.1f (placement RC)" $port $inst $pin $k $a]
  }
}
