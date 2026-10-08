# ORFS PRE_CTS hook for ot_s81_bf_native RECUT (s81-bf, 2026-10-07): the element clock gate's enable FF g_qz_cg.u_z
# drives only the root-level ICG g_cg.u_cg.u_icg.  Routed bf_recut_5e31c66a7 at TT: the only failing check was that
# gating check, -16.0 ps (u_z leaf clock 760 ps after 29 buffer levels, ICG CLK 241 ps).  Unlike HALF_PHL's phase FF,
# u_z's D cone comes from leaf-clocked element state (go, walkers, drain), so u_z cannot sit at the ICG's own clock
# arrival without starving that cone.  This hook moves u_z's CLK to an ANCESTOR net of its own CTS branch, a fraction
# OT_CGL_FRAC (default 0.5) of the buffer levels from the root, splitting the leaf-to-root skew between the enable
# path (u_z -> ICG ENA) and the cone path (element leaves -> u_z D).  Real CTS nets, propagated clocks, no constraint
# change; STA times both paths.  Runs after clock_tree_synthesis, before the post-CTS repair (wraps
# repair_timing_helper); fails closed.  Also carries the karb buffer-cap wrapper (one PRE_CTS hook per step).
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl

proc ot_cgl_find {} {
  set b [ord::get_db_block]
  set icg {}; set z {}
  foreach inst [$b getInsts] {
    set n [string map {\\ {} / .} [$inst getName]]
    set m [[$inst getMaster] getName]
    if {[string match {*g_rc.u_elem.g_cg.u_cg.u_icg} $n] && [string match {ICG*} $m]} {lappend icg $inst}
    if {[string match {*g_rc.u_elem.g_qz_cg.u_z.q[$]*} $n] && [string match {DFF*} $m]} {lappend z $inst}
  }
  if {[llength $icg] != 1 || [llength $z] != 1} {error "BF_CGL expected 1 ICG and 1 enable FF, got [llength $icg] / [llength $z]"}
  return [list [lindex $icg 0] [lindex $z 0]]
}

# the chain of clock nets from the FF's CLK net up to the root (driver = a buffer: follow its input)
proc ot_cgl_ancestors {net} {
  set chain [list $net]
  for {set i 0} {$i < 200} {incr i} {
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} {set drv $it} }
    if {$drv eq ""} break
    set inst [$drv getInst]
    set in ""
    foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL" && [[$it getNet] getSigType] ne "POWER" && [[$it getNet] getSigType] ne "GROUND"} {set in [$it getNet]} }
    if {$in eq "" || ![string match {BUF*} [[$inst getMaster] getName]]} break
    set net $in
    lappend chain $net
  }
  return $chain
}

if {![info exists ::ot_cgl_done]} {set ::ot_cgl_done 0}
proc ot_cgl_rewire {} {
  if {$::ot_cgl_done} return
  lassign [ot_cgl_find] icg z
  set frac [expr {[info exists ::env(OT_CGL_FRAC)] ? $::env(OT_CGL_FRAC) : 0.5}]
  set ck [$z findITerm CLK]
  set chain [ot_cgl_ancestors [$ck getNet]]
  set lv [expr {[llength $chain] - 1}]
  # chain index 0 = the FF's leaf net, lv = the root-most net reached; target net frac of the levels from the root
  set k [expr {$lv - int(round($frac * $lv))}]
  if {$k < 0} {set k 0}
  set tgt [lindex $chain $k]
  set old [$ck getNet]
  if {[$old getName] ne [$tgt getName]} { $ck disconnect; $ck connect $tgt }
  # place the FF beside the driver of the target net (detailed_placement legalises it)
  foreach it [$tgt getITerms] { if {[$it isOutputSignal]} { lassign [[$it getInst] getLocation] x y; $z setLocation $x $y; $z setPlacementStatus PLACED } }
  set ::ot_cgl_done 1
  puts "BF_CGL_REWIRED [$z getName] CLK: [$old getName] -> [$tgt getName] (level $k of $lv from the leaf, frac $frac)"
}

proc ot_cgl_check {tag} {
  lassign [ot_cgl_find] icg z
  puts "BF_CGL_CHECK $tag ff=[$z getName] clknet=[[[$z findITerm CLK] getNet] getName]"
}

if { [info procs repair_timing_helper] ne "" && [info procs ot_cgl_inner_repair_timing_helper] eq "" } {
  rename repair_timing_helper ot_cgl_inner_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_cgl_rewire
    estimate_parasitics -placement
    ot_cgl_inner_repair_timing_helper {*}$args
  }
} else {
  error "BF_CGL: repair_timing_helper missing (cts.tcl changed?)"
}
