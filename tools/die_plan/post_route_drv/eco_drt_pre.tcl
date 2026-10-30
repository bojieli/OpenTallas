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
