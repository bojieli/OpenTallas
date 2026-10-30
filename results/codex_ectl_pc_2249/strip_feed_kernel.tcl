# DIE-KV-41 q0 V4 (kit-local POST_CTS, before leaf_affinity): MACRO-SHADOW STRIP FEED.
# Root cause (q0 V3 routed, CHECKED): leaf drivers in the 13-um strip between SRAM macro[0] and the S core edge hang on
# level-5 buffers placed above the macro / up the W corridor; the routed parent nets detour around the macro (193 um for
# a 51-um straight hop) -> strip leaves 285-329 ps vs 200-268 elsewhere (pair skew 132 > 80).
# Rule (geometry only, no timing input): every clock leaf driver INSIDE the strip rect whose parent buffer is OUTSIDE the
# rect is re-hung onto a planned feed placed at the nearer strip end (W or E), with the same buffer depth as before.
#   OT_SF_RECT  "x0 y0 x1 y1" um (the strip; plan geometry = macro x-span x [core edge, macro bottom])
#   OT_SF_MODE  sibling (V4a): feed = 1 buffer at the strip end, input = the level-(p-1) net (old parent's input level)
#                               whose driver is nearest the feed point
#               chain   (V4b): feed = 2 buffers (corridor top above the strip end -> strip end), input = the level-(p-2)
#                               net whose driver is nearest the corridor top
#   OT_SF_W_XY / OT_SF_E_XY "x y" feed points at the strip ends; OT_SF_WTOP_XY / OT_SF_ETOP_XY corridor tops (chain)
#   OT_SF_MASTER (default BUFx24_ASAP7_75t_R = the CTS buffer)
# ORFS may source this hook inside a procedure: the shared state lives in the global namespace.
global sf_b sf_u sf_x0 sf_y0 sf_x1 sf_y1 sf_mode sf_master sf_leaf sf_bad sf_mid sf_plevel sf_gone sf_prefix
proc sf_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set sf_b [ord::get_db_block]; set sf_u [[ord::get_db_tech] getDbUnitsPerMicron]
lassign [sf_env OT_SF_RECT ""] sf_x0 sf_y0 sf_x1 sf_y1
if {$sf_x0 eq ""} { puts "OT_SF skip (no OT_SF_RECT)"; return }
set sf_mode [sf_env OT_SF_MODE sibling]
set sf_prefix [sf_env OT_SF_PREFIX strip]
set sf_master [[ord::get_db] findMaster [sf_env OT_SF_MASTER BUFx24_ASAP7_75t_R]]
proc sf_c {i} { global sf_u; set b [$i getBBox]; list [expr {([$b xMin]+[$b xMax])/2.0/$sf_u}] [expr {([$b yMin]+[$b yMax])/2.0/$sf_u}] }
proc sf_in {x y} { global sf_x0 sf_y0 sf_x1 sf_y1; expr {$x >= $sf_x0 && $x <= $sf_x1 && $y >= $sf_y0 && $y <= $sf_y1} }
proc sf_isbuf {i} { set m [[$i getMaster] getName]; expr {[string match "BUF*" $m] || [string match "CLKBUF*" $m]} }
proc sf_inet {i} { foreach t [$i getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { return [$t getNet] } }; return "NULL" }
proc sf_onet {i} { foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { return [$t getNet] } }; return "NULL" }
proc sf_drv {n} { foreach t [$n getITerms] { if {[$t isOutputSignal]} { return [$t getInst] } }; return "NULL" }
# clock leaf drivers = buffers whose output net reaches a register CLK pin
set sf_leaf {}
foreach i [$sf_b getInsts] {
  if {![sf_isbuf $i]} continue
  set o [sf_onet $i]; if {$o eq "NULL" || [$o getSigType] ne "CLOCK"} continue
  foreach t [$o getITerms] { if {[[$t getMTerm] getName] eq "CLK"} { lappend sf_leaf $i; break } }
}
# level of every clock buffer = hops from the clock port
proc sf_level {i} {
  set k 0
  while {$i ne "NULL" && $k < 64} { set n [sf_inet $i]; if {$n eq "NULL"} break; set i [sf_drv $n]; incr k }
  return $k
}
set sf_bad {}
foreach l $sf_leaf {
  lassign [sf_c $l] x y
  if {![sf_in $x $y]} continue
  set p [sf_drv [sf_inet $l]]; if {$p eq "NULL"} continue
  lassign [sf_c $p] px py
  if {[sf_in $px $py]} continue
  lappend sf_bad [list $l $p $x $y]
}
puts "OT_SF leaves [llength $sf_leaf] strip_leaves_with_outside_parent [llength $sf_bad] mode $sf_mode rect $sf_x0 $sf_y0 $sf_x1 $sf_y1"
if {![llength $sf_bad]} return
# candidate input nets by level
proc sf_nearest_net {lvl x y} {
  global sf_b
  set best ""; set bd 1e18
  foreach i [$sf_b getInsts] {
    if {![sf_isbuf $i]} continue
    set o [sf_onet $i]; if {$o eq "NULL" || [$o getSigType] ne "CLOCK"} continue
    if {[sf_level $i] != $lvl} continue
    lassign [sf_c $i] ix iy
    set d [expr {abs($ix-$x)+abs($iy-$y)}]
    if {$d < $bd} { set bd $d; set best $o }
  }
  return [list $best $bd]
}
proc sf_mkbuf {name x y innet} {
  global sf_b sf_u sf_master
  set i [odb::dbInst_create $sf_b $sf_master $name]
  $i setLocation [expr {round($x*$sf_u)}] [expr {round($y*$sf_u)}]
  $i setPlacementStatus PLACED
  set on [odb::dbNet_create $sf_b "${name}_net"]; $on setSigType CLOCK
  [$i findITerm A] connect $innet
  [$i findITerm Y] connect $on
  return $on
}
set sf_mid [expr {($sf_x0+$sf_x1)/2.0}]
set sf_plevel [sf_level [lindex $sf_bad 0 1]]
foreach side {W E} {
  set grp {}
  foreach b $sf_bad { lassign $b l p x y; if {($side eq "W") == ($x < $sf_mid)} { lappend grp $l } }
  if {![llength $grp]} continue
  lassign [sf_env OT_SF_${side}_XY ""] fx fy
  if {$sf_mode eq "sibling"} {
    lassign [sf_nearest_net [expr {$sf_plevel-1}] $fx $fy] innet d
    set feed [sf_mkbuf ot_sf_${sf_prefix}_${side} $fx $fy $innet]
    puts "OT_SF $side feed ot_sf_$side @($fx,$fy) <- [$innet getName] (driver dist [format %.1f $d] um, level [expr {$sf_plevel-1}]) leaves [llength $grp]"
  } else {
    lassign [sf_env OT_SF_${side}TOP_XY ""] tx ty
    lassign [sf_nearest_net [expr {$sf_plevel-2}] $tx $ty] innet d
    set n1 [sf_mkbuf ot_sf_${sf_prefix}_${side}top $tx $ty $innet]
    set feed [sf_mkbuf ot_sf_${sf_prefix}_${side} $fx $fy $n1]
    puts "OT_SF $side chain ot_sf_${sf_prefix}_${side}top @($tx,$ty) <- [$innet getName] (driver dist [format %.1f $d] um, level [expr {$sf_plevel-2}]) -> ot_sf_$side @($fx,$fy) leaves [llength $grp]"
  }
  foreach l $grp {
    set a [$l findITerm A]; set old [$a getNet]; $a disconnect; $a connect $feed
    puts "OT_SF   [$l getName] [[sf_drv $old] getName] -> [$feed getName]"
  }
}
# parents left with no load are removed (no floating clock buffers)
set sf_gone {}
foreach b $sf_bad {
  set p [lindex $b 1]; set pn [$p getName]
  if {[lsearch -exact $sf_gone $pn] >= 0} continue
  set o [sf_onet $p]; if {$o eq "NULL"} continue
  if {[llength [$o getITerms]] <= 1 && ![llength [$o getBTerms]]} { puts "OT_SF remove unloaded $pn"; lappend sf_gone $pn; odb::dbInst_destroy $p; odb::dbNet_destroy $o }
}
if {[catch {detailed_placement} m]} { error "OT_SF detailed_placement failed: $m" }
check_placement -verbose
estimate_parasitics -placement
puts "OT_SF done"
