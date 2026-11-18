# private_leaf.tcl (HEAD-SERDES-1115, COORD 17:05): clock.private_leaf plan row -> OT_PRIVATE_LEAF_RE (config.mk).
# Post-CTS kit step (run_kit.sh, after CTS and the GRT-RC tap pre-pass, before the TT setup repair).  The row names an ANCHOR
# instance (OT_PRIVATE_LEAF_LIKE, exact instance name, e.g. a macro) and a sink regex (OT_PRIVATE_LEAF_RE).  The step clones the
# leaf buffer that drives the anchor's clock pin (same master, same input net, placed at the original), legalises it with
# detailed_placement, and moves exactly the matching sinks' clock pins to the clone's output net.  The anchor and every other
# sink stay where they are.  The matching sinks therefore get the anchor's clock arrival (the anchor tap) on a leaf of their
# own, without adding load to the anchor's leaf.
# Why: hd_serdes u_syn done[0] x3 launch at 900 ps into ot_s81_kp4_dchn k_lo whose clock pin arrives at 589 ps and whose lib
# setup is 233 ps: -109 ps.  On the anchor's own leaf: -42 ps (3 extra loads on the macro leaf); on a clone of that leaf:
# -33.9 ps (placement RC).  A clone of the sinks' OWN leaf changes nothing (same arrival).
# FAIL-OPEN: any problem (no match, driver is not a single-input single-output cell, no legal placement, check_placement
# errors) prints one "OT_PRIVATE_LEAF FALLBACK <reason>" line and leaves the database untouched (nothing is written).
# env ODB (input), OUT (output, default = ODB), OT_PRIVATE_LEAF_RE (read from /work/config.mk when unset),
# OT_PRIVATE_LEAF_AT=anchor (default: start at the centroid of the moved sinks), OT_PRIVATE_LEAF_GRT=1 (a DB that already carries route guides, e.g. 5_1_grt.odb: route the clone and the moved pins incrementally).
if {[file exists /work/config.mk]} {
  set fh [open /work/config.mk]
  foreach ln [split [read $fh] "\n"] {
    if {[regexp {^export\s+(OT_PRIVATE_LEAF_RE|OT_PRIVATE_LEAF_LIKE)\s*\??=\s*(\S+)\s*$} $ln -> k v] && ![info exists ::env($k)]} { set ::env($k) $v }
  }
  close $fh
}
proc ot_pl_fallback {why} { puts "OT_PRIVATE_LEAF FALLBACK $why: database unchanged"; exit 0 }
if {![info exists ::env(OT_PRIVATE_LEAF_RE)] || $::env(OT_PRIVATE_LEAF_RE) eq ""} { ot_pl_fallback "OT_PRIVATE_LEAF_RE unset" }
if {![info exists ::env(OT_PRIVATE_LEAF_LIKE)] || $::env(OT_PRIVATE_LEAF_LIKE) eq ""} { ot_pl_fallback "OT_PRIVATE_LEAF_LIKE unset" }
set ot_pl_re $::env(OT_PRIVATE_LEAF_RE)
set ot_pl_like $::env(OT_PRIVATE_LEAF_LIKE)
if {[catch {regexp -- $ot_pl_re x} err]} { ot_pl_fallback "bad regex ($err)" }
if {[catch {
  read_db $::env(ODB)
  set blk [ord::get_db_block]
  set ot_pl_grt [expr {[info exists ::env(OT_PRIVATE_LEAF_GRT)] && $::env(OT_PRIVATE_LEAF_GRT) eq "1"}]
  if {$ot_pl_grt} { global_route -start_incremental -allow_congestion }
  set dbu [expr {double([$blk getDbUnitsPerMicron])}]
  # the match is on the instance name as written and with the odb bracket escapes removed (g_bm\[0\] -> g_bm[0])
  proc ot_pl_match {re n} { return [expr {[regexp -- $re $n] || [regexp -- $re [string map {\\ {}} $n]]}] }
  # anchor: the leaf net of its clock pin and that net's single driver
  proc ot_pl_clk_iterm {inst} {
    foreach it [$inst getITerms] {
      if {[[$it getMTerm] getSigType] eq "CLOCK" && [[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} { return $it }
    }
    return ""
  }
  set anchor ""
  foreach inst [$blk getInsts] {
    if {[string map {\\ {}} [$inst getName]] eq [string map {\\ {}} $ot_pl_like]} { set anchor $inst; break }
  }
  if {$anchor eq ""} { error "anchor instance $ot_pl_like not found" }
  set ait [ot_pl_clk_iterm $anchor]
  if {$ait eq ""} { error "anchor $ot_pl_like has no clock pin on a net" }
  set anet [$ait getNet]
  set drv ""; set ndrv 0
  foreach it [$anet getITerms] { if {[$it isOutputSignal]} { set drv $it; incr ndrv } }
  if {$ndrv != 1} { error "anchor leaf net [$anet getName] has $ndrv drivers" }
  set dinst [$drv getInst]
  set nin 0; set nout 0; set innet ""
  foreach it [$dinst getITerms] {
    if {[$it isInputSignal]} { incr nin; set innet [$it getNet] }
    if {[$it isOutputSignal]} { incr nout }
  }
  if {$nin != 1 || $nout != 1 || $innet eq "NULL" || $innet eq ""} { error "anchor leaf driver [$dinst getName] is not a single-input single-output cell" }
  set sinks {}; set nmatch 0
  foreach inst [$blk getInsts] {
    if {$inst eq $anchor || ![ot_pl_match $ot_pl_re [$inst getName]]} continue
    incr nmatch
    set cit [ot_pl_clk_iterm $inst]
    if {$cit eq ""} { puts "OT_PRIVATE_LEAF skip [$inst getName]: no clock pin on a net"; continue }
    if {[$cit getNet] eq $anet} { puts "OT_PRIVATE_LEAF skip [$inst getName]: already on the anchor leaf"; continue }
    lappend sinks [list $inst $cit]
  }
  if {[llength $sinks] == 0} { error "no sink to move ($nmatch matching instances)" }
  set cnt 1
  set cl [odb::dbInst_create $blk [$dinst getMaster] "ot_private_leaf_1"]
  if {$cl eq "NULL"} { error "cannot create clone of [$dinst getName]" }
  lassign [$dinst getLocation] lx ly
  # start the clone at the centroid of the moved sinks (default; GRT-RC proof on hd_serdes sd9k: -40.58 ps vs -46.68 ps when
  # started at the anchor's leaf buffer): the clone->sink wires are the long ones.  OT_PRIVATE_LEAF_AT=anchor keeps the anchor spot.
  if {![info exists ::env(OT_PRIVATE_LEAF_AT)] || $::env(OT_PRIVATE_LEAF_AT) ne "anchor"} {
    set sx 0; set sy 0
    foreach s $sinks { lassign [[lindex $s 0] getLocation] ix iy; incr sx $ix; incr sy $iy }
    set lx [expr {$sx / [llength $sinks]}]; set ly [expr {$sy / [llength $sinks]}]
  }
  $cl setOrient [$dinst getOrient]
  $cl setLocation $lx $ly
  $cl setPlacementStatus PLACED
  set newnet [odb::dbNet_create $blk "ot_private_leaf_net_1"]
  $newnet setSigType CLOCK
  foreach it [$cl getITerms] {
    if {[$it isInputSignal]} { $it connect $innet }
    if {[$it isOutputSignal]} { $it connect $newnet }
  }
  foreach s $sinks { set it [lindex $s 1]; $it disconnect; $it connect $newnet }
  $cl setDoNotTouch 1
  $newnet setDoNotTouch 1
  puts "OT_PRIVATE_LEAF clone [$dinst getName] ([[$dinst getMaster] getName]) = leaf of anchor [$anchor getName] (net [$anet getName]): [llength $sinks] sinks -> private net ot_private_leaf_net_1"
  set clones [list [list $cl [$dinst getName] $lx $ly]]
  if {$cnt == 0} { error "nothing cloned" }
  detailed_placement
  if {$ot_pl_grt} { global_route -end_incremental -allow_congestion }
  set bad 0
  if {[catch {check_placement -verbose} cpe]} { set bad 1; puts "OT_PRIVATE_LEAF check_placement: $cpe" }
  foreach c $clones {
    set cl [lindex $c 0]
    lassign [$cl getLocation] x y
    if {[$cl getPlacementStatus] ne "PLACED"} { incr bad }
    puts [format "OT_PRIVATE_LEAF placed %s at %.3f %.3f um (original %s at %.3f %.3f) moved %.3f um" [$cl getName] \
      [expr {$x/$dbu}] [expr {$y/$dbu}] [lindex $c 1] [expr {[lindex $c 2]/$dbu}] [expr {[lindex $c 3]/$dbu}] \
      [expr {(abs($x-[lindex $c 2])+abs($y-[lindex $c 3]))/$dbu}]]
  }
  if {$bad} { error "placement of the clone is not legal" }
  set out $::env(ODB); if {[info exists ::env(OUT)] && $::env(OUT) ne ""} { set out $::env(OUT) }
  write_db $out
  puts "OT_PRIVATE_LEAF wrote $out ($cnt clone(s), $nmatch matching sink(s))"
} err]} {
  ot_pl_fallback $err
}
