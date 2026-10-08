# Procedures for ph_local.tcl (PRE_CTS) and ph_local_post.tcl (POST_CTS); see ph_local.tcl.
proc ot_phl_find {} {
  set b [ord::get_db_block]
  set icg {}; set ph {}
  foreach inst [$b getInsts] {
    set n [string map {/ .} [$inst getName]]
    set m [[$inst getMaster] getName]
    if {[string match {*g_half.u_hcg.u_icg} $n] && [string match {ICG*} $m]} {lappend icg $inst}
    if {[string match {*g_half.ph[$]*} $n] && [string match {DFF*} $m]} {lappend ph $inst}
  }
  if {[llength $icg] != 1 || [llength $ph] != 1} {
    error "BF_PHL expected 1 ICG and 1 phase FF, got [llength $icg] / [llength $ph]"
  }
  return [list [lindex $icg 0] [lindex $ph 0]]
}

proc ot_phl_check {tag} {
  lassign [ot_phl_find] icg ph
  set b [ord::get_db_block]
  set dbu [$b getDbUnitsPerMicron]
  set gnet [[$icg findITerm CLK] getNet]
  set pnet [[$ph findITerm CLK] getNet]
  if {$gnet eq "NULL" || $pnet eq "NULL" || [$gnet getName] ne [$pnet getName]} {
    error "BF_PHL $tag: phase FF clock net [expr {$pnet eq "NULL" ? "NULL" : [$pnet getName]}] != ICG clock net [expr {$gnet eq "NULL" ? "NULL" : [$gnet getName]}]"
  }
  lassign [$icg getLocation] gx gy
  lassign [$ph getLocation] x y
  set span [expr {(abs($x-$gx)+abs($y-$gy))/double($dbu)}]
  puts "BF_PHL_CHECK $tag net=[$gnet getName] ph=[$ph getName] span_um=$span"
  if {$span > 30.0} {error "BF_PHL $tag: phase FF $span um from the ICG"}
}

if {![info exists ::ot_phl_done]} {set ::ot_phl_done 0}
proc ot_phl_rewire {} {
  if {$::ot_phl_done} return
  lassign [ot_phl_find] icg ph
  set gck [$icg findITerm CLK]
  set gnet [$gck getNet]
  if {$gnet eq "NULL"} {error "BF_PHL ICG CLK unconnected"}
  set pck [$ph findITerm CLK]
  set old [$pck getNet]
  set oldn [expr {$old eq "NULL" ? "NULL" : [$old getName]}]
  if {$oldn ne [$gnet getName]} {
    # drive-1143: clk_net_protect.tcl (OT_CTS_FIX_HOOKS) marks every CTS clock net dont_touch before this rewire runs
    # (ODB-0372 on clknet_*_leaf_clk_regs); this is a deliberate clock edit, so lift dont_touch on the two nets for
    # the move only and restore it.
    set dt {}
    foreach n [list $old $gnet] { if {$n ne "NULL"} { lappend dt $n [$n isDoNotTouch]; $n setDoNotTouch 0 } }
    $pck disconnect
    $pck connect $gnet
    foreach {n v} $dt { $n setDoNotTouch $v }
  }
  lassign [$icg getLocation] gx gy
  set dbu [[ord::get_db_block] getDbUnitsPerMicron]
  $ph setLocation [expr {$gx + int(3*$dbu)}] $gy
  $ph setPlacementStatus PLACED
  set ::ot_phl_done 1
  puts "BF_PHL_REWIRED [$ph getName] CLK: $oldn -> [$gnet getName] (ICG [$icg getName] CLK net); placed at the ICG"
}

