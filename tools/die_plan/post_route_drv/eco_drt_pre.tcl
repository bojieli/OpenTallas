# Opt-in continuation of an already repaired route-keeping ECO whose DRT has
# exhausted stale kept-route pin access (e.g. DRT-1231 after a full AP wipe).
# Run on the retained 5_1_grt DB: no repair_timing or SPEF replay is performed.
# Ordinary ECOs retain their existing incremental-route behavior.
proc ot_eco_reroute_data {} {
  if {![info exists ::env(RESULTS_DIR)]} { error "OT_ECO_REROUTE_DATA: RESULTS_DIR missing" }
  set rd $::env(RESULTS_DIR)
  set nf [file join $rd clk_freeze_nets.txt]
  set here [file dirname [info script]]
  foreach f [list $nf [file join $here clk_freeze.tcl] [file join $here clk_geom_diff.py]] {
    if {![file exists $f]} { error "OT_ECO_REROUTE_DATA: required file missing: $f" }
  }
  source [file join $here clk_freeze.tcl]
  set b [ord::get_db_block]
  set fh [open $nf r]; set keep [dict create]
  foreach nm [split [read $fh] \n] {
    if {$nm eq ""} continue
    set n [$b findNet $nm]
    if {$n eq "NULL" || $n eq ""} { close $fh; error "OT_ECO_REROUTE_DATA: frozen net missing: $nm" }
    dict set keep $nm 1
  }
  close $fh
  if {![dict size $keep]} { error "OT_ECO_REROUTE_DATA: frozen clock list empty" }
  # Keep every recognized clock net as well as the immutable ECO freeze list.
  foreach n [ot_clk_dbnets] { dict set keep [$n getName] 1 }
  set rip {}
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND} || [dict exists $keep [$n getName]]} continue
    set w [$n getWire]
    if {$w eq "NULL" || $w eq ""} continue
    if {![llength [$n getGuides]] && [llength [$n getITerms]]+[llength [$n getBTerms]]>1} {
      error "OT_ECO_REROUTE_DATA: wired data net has no retained guides: [$n getName]"
    }
    lappend rip $w
  }
  set pre [file join $rd data_reroute_clock_before.tsv]
  set post [file join $rd data_reroute_clock_after.tsv]
  ot_clk_dump $pre before_data_unwire $nf
  foreach w $rip { odb::dbWire_destroy $w }
  ot_clk_dump $post after_data_unwire $nf
  if {[catch {exec python3 -I [file join $here clk_geom_diff.py] $pre $post --json [file join $rd data_reroute_clock.json]} msg]} {
    puts $msg; error "OT_ECO_REROUTE_DATA: frozen clock geometry changed"
  }
  puts $msg
  puts "OT_ECO_REROUTE_DATA ripped_data_nets [llength $rip] preserved_clock_nets [dict size $keep]"
  write_db [file join $rd 5_1_grt_data_unwired.odb]
}
if {[info exists ::env(OT_ECO_REROUTE_DATA)] && $::env(OT_ECO_REROUTE_DATA) eq "1"} {
  ot_eco_reroute_data
  # A fully ripped data route needs fresh PA for all masters, including insts
  # whose old index happened to be nonnegative. The canonical wipe below clears
  # the MPin and block catalogs after these indices become invalid.
  foreach i [[ord::get_db_block] getInsts] { $i setPinAccessIdx -1 }
}

# FLOW-9 2026-10-30 (shared form of KVHEAD-KITS-2 rx259_eco8 drt_pre.tcl): PRE_DETAIL_ROUTE hook for DRT on an ECO'd
# GRT DB (clk_freeze FIXED + setSpecial clock nets, swapMaster / inserted ECO cells, custom global_route + write_db).
# Stock ORFS detail_route.tcl SIGSEGVs on two kinds of stale state such a DB can carry:
#   (1) dbGuides from the ORIGINAL route left on SPECIAL signal nets: GRT skips special nets, so grt::have_routes ->
#       mergeSegments meets a net with no GRT pins.  DRT never routes a special net, so their guides are dropped
#       (wires untouched).
#   (2) a mixed pin-access catalog: the original route's access points (inst pin_access_idx >= 0) next to ECO'd insts at
#       pin_access_idx -1 (swapMaster clears it): DRT finishes, then io::Writer::updateDbAccessPoints SIGSEGVs in
#       dbITerm::setAccessPoint.  The whole catalog is wiped so DRT recomputes pin access for every inst (as on a fresh
#       placement); no geometry change.
# Each part is a NO-OP on an ordinary DB (no guided special signal net / no inst at -1 or no catalog) and prints what it
# did.  Fails closed on a catalog index this wipe cannot clear.  Opt-in: PRE_DETAIL_ROUTE_TCL=<this file> (prd_mk.sh
# stages it for the post-route drive repair); OT_ECO_DRT_PRE_CHAIN=<tcl> sources a kit's own PRE_DETAIL_ROUTE hook after.
proc ot_eco_drt_pre {} {
  set b [ord::get_db_block]
  set nsp 0; set ncl 0
  foreach n [$b getNets] {
    if {![$n isSpecial] || [$n getSigType] in {POWER GROUND}} continue
    incr nsp
    if {[llength [$n getGuides]]} { $n clearGuides; incr ncl }
  }
  puts "OT_ECO_DRT_PRE guides: special_signal_nets $nsp guides_cleared $ncl"
  set insts [$b getInsts]
  set nneg 0; set npos 0; set maxidx -1
  foreach i $insts {
    set k [$i getPinAccessIdx]
    if {$k < 0} { incr nneg } else { incr npos; if {$k > $maxidx} { set maxidx $k } }
  }
  set aps [$b getAccessPoints]
  if {!$nneg || (!$npos && ![llength $aps])} {
    puts "OT_ECO_DRT_PRE access points: catalog consistent (insts idx -1 $nneg / idx>=0 $npos, block aps [llength $aps]): unchanged"
    return
  }
  set nslot 16
  if {$maxidx >= $nslot} { error "OT_ECO_DRT_PRE FAIL: pin_access_idx $maxidx >= $nslot: stale catalog cannot be cleared" }
  set masters [dict create]
  foreach i $insts { dict set masters [[$i getMaster] getName] [$i getMaster]; $i setPinAccessIdx -1 }
  set nm 0
  dict for {mn m} $masters {
    foreach t [$m getMTerms] { foreach p [$t getMPins] { for {set k 0} {$k < $nslot} {incr k} { $p clearPinAccess $k }; incr nm } }
  }
  # DIE-HEAD-42 10-30 (LEP ECO4 SIGSEGV in dbAccessPoint::destroy): clearPinAccess already frees the mpin-owned access
  # points, so the list read before the clear dangles; destroy only what a fresh read still returns.
  set nap 0
  foreach ap [$b getAccessPoints] { odb::dbAccessPoint_destroy $ap; incr nap }
  puts "OT_ECO_DRT_PRE access points: STALE catalog (insts idx -1 $nneg / idx>=0 $npos) wiped: masters [dict size $masters]\
 mpins $nm block_aps_destroyed $nap insts_idx_reset [llength $insts]"
}
ot_eco_drt_pre
if {[info exists ::env(OT_ECO_DRT_PRE_CHAIN)] && $::env(OT_ECO_DRT_PRE_CHAIN) ne ""} {
  puts "OT_ECO_DRT_PRE chain: $::env(OT_ECO_DRT_PRE_CHAIN)"
  source $::env(OT_ECO_DRT_PRE_CHAIN)
}
