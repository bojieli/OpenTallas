# QC-SU-F4G PRE_DETAIL_ROUTE_TCL, the ONE signal route: input 5_1_grt.odb = clock-routed DB of f4g_clock_route.tcl.
# Clock nets keep their routed wires (locked, OT_F4G_LOCK), signals get the full rewritten guide set, M6 is obstructed
# everywhere except the locked tree M6 shapes (m6_strip.py of that same DB, side 80 / end 160), signals <= M5 in effect.
# The B1 NDR (2x M6 spacing) is CLEARED here: try 1 (rp1 22:00) kept it and the NDR spacing (96) to the strip
# obstruction (80) put DRC markers on every tree M6 wire -> 46/113 clock nets ripped up, tree M6 1060 -> 41 um (FAIL,
# retained f4g_chain_try1_FAIL.txt). The trunk separation already sits in the B1 geometry; the strip keeps signals out.
read_guides $::env(OT_F4G_G1)
set top [expr {[info exists ::env(OT_F4G_SIGTOP)] ? $::env(OT_F4G_SIGTOP) : "M6"}]
set blk [ord::get_db_block]; set c [dict create]; set nl 0; set nndr 0
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  set t [expr {[string match ot_ms_*_n [$n getName]] ? "tree" : "other"}]
  foreach g [$n getGuides] { dict incr c "$t:[[$g getLayer] getName]" }
  if {[isclk $n]} {
    set w [$n getWire]; if {$w eq "NULL" || $w eq ""} { error "F4G: clock net [$n getName] not pre-routed" }
    if {$::env(OT_F4G_LOCK) eq "fixed"} { $n setWireType FIXED }
    if {$::env(OT_F4G_LOCK) eq "dnt"} { $n setDoNotTouch 1 }
    # try 6: NDR kept (the cleared form of tries 2-5 let signals into the 160-dbu channel between NDR trunk pairs)
    if {[info exists ::env(OT_F4G_CLEAR_NDR)] && [$n getNonDefaultRule] ne "NULL"} { $n setNonDefaultRule NULL; incr nndr }
    # try 3a (22:10) FAILED DRT-0155: tree guides on M6 outside M2-M5. A pre-routed clock net needs no guide: with its
    # guides removed DRT skips it as a route target (B1 showed guide-less nets are skipped) and sees its wires as shapes.
    # try 3b (22:12) FAILED: M2-M5 with pre-routed M6 tree wires crashes DRT (initMazeIdx_connFig pathseg no idx M6).
    # try 4: back to M2-M6 + strip, clock guides still removed so DRT does not re-route (vacate) the pre-routed tree.
    $n clearGuides
    incr nl
  }
}
puts "OT_TREE_GUIDE loaded $::env(OT_F4G_G1) :: $c"
if {[dict exists $c other:M6]} { error "OT_TREE_GUIDE: non-tree net has an M6 guide" }
# try 2 (rp1 22:07, strip side 80, NDR cleared): DRC 0, tree M6 intact (1060.7 um, 5/113 clock nets locally re-routed
# in pin areas), but 12 signal nets (22 um) still took M6 where the tree vacated a strip segment (FAIL, retained).
# try 3 default OT_F4G_SIGTOP=M5: with the clock pre-routed the signal route needs no M6 at all -> routing layers
# M2-M5, so no signal can reach M6 by construction (no strip obstruction, nothing for the tree to collide with).
set nob 0
if {$top eq "M6"} {
  set m6 [[[ord::get_db] getTech] findLayer M6]
  set fh [open $::env(OT_M6_STRIP)]
  while {[gets $fh l] >= 0} { lassign $l a b cc d; odb::dbObstruction_create $blk $m6 $a $b $cc $d; incr nob }
  close $fh
}
puts "F4G_SIG_PRE clock_nets_prerouted $nl ndr_cleared $nndr lock $::env(OT_F4G_LOCK) signal_top $top m6_obstructions $nob"
set_routing_layers -signal M2-$top
