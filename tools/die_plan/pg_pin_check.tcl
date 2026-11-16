# pg_pin_check.tcl (PG-PINBAND-1 2026-11-14, FABLE-ROUTE lever 2): pin-access check at floorplan time.
# Class: 59 of 189 detail routes died on DRT-0255 (maze route cannot find path) about 2 h into iteration 0; 25 of the 48 on
# S81/QC/HEAD sit within 80 um of the west face, nets = ports and first station ranks.  The proof (PG-AWARE-1) needed the
# 2 h route.  Both mechanisms are decided before any route, from geometry that exists right after PDN:
#   (A) PIN: a block pin box on M5/M6/M7 within BAND um of a die face whose same-layer clearance to a PG stripe is below the
#       layer spacing (or that overlaps it): no legal access point, DRT-0073 / DRT-0255 on that net.
#   (B) CELL (CELLS=1, needs a placed DB): a movable standard cell in the band under an M5-pair x M6-pair PG crossing
#       (the PG-AWARE-1 mechanism b; pg_cell_keepout.tcl removes it).
# Usage (OpenROAD):  ODB=2_floorplan.odb OUT=pg_pin_check.tsv [BAND_UM=80] [CELLS=0|1] [MAXPRINT=40] [PIN_ACCESS=0|1]
#                    openroad -exit pg_pin_check.tcl
# Output: PG_PIN_CHECK lines; "[ERROR PGPIN-0255] ..." per failing pin (evidence like DRT-0255: net, layer, box, PG stripe, gap);
#         final "PG_PIN_CHECK RESULT PASS|FAIL pins=N bad_pins=B bad_cells=C band_um=..."; OUT = one TSV row per bad item.
# exit status 0 = PASS, 3 = FAIL (the kit stops early, before place/CTS/route, with the evidence above).
proc pgpc_env {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }; return $d }
proc pgpc_gap {a b} {
  # edge gap (dbu) of two boxes {x0 y0 x1 y1}; negative = overlap depth along the smaller axis
  lassign $a ax0 ay0 ax1 ay1; lassign $b bx0 by0 bx1 by1
  set dx [expr {max($bx0-$ax1, $ax0-$bx1)}]; set dy [expr {max($by0-$ay1, $ay0-$by1)}]
  if {$dx > 0 && $dy > 0} { return [expr {hypot($dx,$dy)}] }
  if {$dx > 0} { return $dx }
  if {$dy > 0} { return $dy }
  return [expr {max($dx,$dy)}]
}
proc pgpc_run {} {
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]; set dbu [$tech getDbUnitsPerMicron]
  set band [expr {round([pgpc_env BAND_UM 80] * $dbu)}]
  set maxp [pgpc_env MAXPRINT 40]
  set die [$blk getDieArea]; set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set layers {M5 M6 M7}
  # PG stripes per layer inside the band zone (+1 um): list of {x0 y0 x1 y1 net}
  set pg [dict create]; foreach l $layers { dict set pg $l {} }
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] { foreach w [$sw getWires] {
      if {[$w isVia]} continue
      set L [$w getTechLayer]; if {$L eq "NULL"} continue
      set ln [$L getName]; if {$ln ni $layers} continue
      set b [list [$w xMin] [$w yMin] [$w xMax] [$w yMax]]
      if {[lindex $b 2] < $dx0 || [lindex $b 0] > $dx1 || [lindex $b 3] < $dy0 || [lindex $b 1] > $dy1} continue
      dict lappend pg $ln [concat $b [$net getName]]
    } }
  }
  proc pgpc_inband {b dx0 dy0 dx1 dy1 band} {
    lassign $b x0 y0 x1 y1
    return [expr {$x0 < $dx0+$band || $x1 > $dx1-$band || $y0 < $dy0+$band || $y1 > $dy1-$band}]
  }
  proc pgpc_face {b dx0 dy0 dx1 dy1} {
    lassign $b x0 y0 x1 y1
    set d [list [expr {$x0-$dx0}] W [expr {$dx1-$x1}] E [expr {$y0-$dy0}] S [expr {$dy1-$y1}] N]
    set best 1e18; set f ?
    foreach {v n} $d { if {$v < $best} { set best $v; set f $n } }
    return "$f [format %.2f [expr {$best*1.0/[[ord::get_db_tech] getDbUnitsPerMicron]}]]"
  }
  set sp [dict create]
  foreach l $layers { set L [$tech findLayer $l]
    set s 0; catch { set s [$L getSpacing] }
    if {$s <= 0} { set s [$L getWidth] }
    # ASAP7 SPACINGTABLE: next to a stripe wider than 0.025 um the legal clearance is the wide-metal 0.072 um (pg_access.WIDE_SPACING_UM)
    set ws [expr {round([pgpc_env WIDE_SPACING_UM 0.072] * $dbu)}]
    if {$s < $ws} { set s $ws }
    dict set sp $l $s }
  set npins 0; set nbad 0; set rows {}; set printed 0
  foreach bt [$blk getBTerms] {
    if {[$bt getSigType] ne "SIGNAL"} continue
    foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
      set L [$bx getTechLayer]; set ln [$L getName]; if {$ln ni $layers} continue
      set b [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
      if {![pgpc_inband $b $dx0 $dy0 $dx1 $dy1 $band]} continue
      incr npins
      set s [dict get $sp $ln]; set worst 1e18; set wn ""; set wb {}
      foreach p [dict get $pg $ln] {
        set g [pgpc_gap $b [lrange $p 0 3]]
        if {$g < $worst} { set worst $g; set wn [lindex $p 4]; set wb [lrange $p 0 3] }
      }
      if {$worst < $s} {
        incr nbad
        lappend rows [list pin [$bt getName] $ln [lindex $b 0] [lindex $b 1] $wn $worst $s [pgpc_face $b $dx0 $dy0 $dx1 $dy1]]
        if {$printed < $maxp} { incr printed
          puts [format "\[ERROR PGPIN-0255\] pin %s %s box (%.3f %.3f)-(%.3f %.3f) um face %s um: PG %s stripe (%.3f %.3f)-(%.3f %.3f) gap %.3f um < spacing %.3f um: no legal access point (DRT-0255 class)" \
            [$bt getName] $ln [expr {[lindex $b 0]*1.0/$dbu}] [expr {[lindex $b 1]*1.0/$dbu}] [expr {[lindex $b 2]*1.0/$dbu}] [expr {[lindex $b 3]*1.0/$dbu}] \
            [pgpc_face $b $dx0 $dy0 $dx1 $dy1] $wn \
            [expr {[lindex $wb 0]*1.0/$dbu}] [expr {[lindex $wb 1]*1.0/$dbu}] [expr {[lindex $wb 2]*1.0/$dbu}] [expr {[lindex $wb 3]*1.0/$dbu}] \
            [expr {$worst*1.0/$dbu}] [expr {$s*1.0/$dbu}]] }
      }
    } }
  }
  # (B) cells in the band under an M5 x M6 PG crossing
  set ncells 0; set nbadc 0; set nfixed 0
  if {[pgpc_env CELLS 0] eq "1"} {
    source [file join [file dirname [info script]] pg_cell_keepout.tcl]
    set xs {}
    foreach c [ot_pgcko_crossings $blk 0.0] { lappend xs $c }
    set idx [ot_pgcko_index $xs]
    foreach i [$blk getInsts] {
      set ms [$i getMaster]; if {[$ms isBlock] || [$ms getType] ne "CORE"} continue
      set bb [$i getBBox]; set b [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
      if {![pgpc_inband $b $dx0 $dy0 $dx1 $dy1 $band]} continue
      incr ncells
      if {[$i getPlacementStatus] in {FIRM LOCKED FIXED COVER}} { if {[ot_pgcko_hit $idx $bb]} { incr nfixed }; continue }
      if {[ot_pgcko_hit $idx $bb]} { incr nbadc
        lappend rows [list cell [$i getName] [$ms getName] [lindex $b 0] [lindex $b 1] M5xM6 0 0 [pgpc_face $b $dx0 $dy0 $dx1 $dy1]]
        if {$nbadc <= $maxp} { puts [format "\[ERROR PGPIN-0255\] cell %s (%s) at (%.3f %.3f) um face %s um: under an M5 x M6 PG crossing, pin exits are spacing-dead tracks (DRT-0255 class)" \
          [$i getName] [$ms getName] [expr {[lindex $b 0]*1.0/$dbu}] [expr {[lindex $b 1]*1.0/$dbu}] [pgpc_face $b $dx0 $dy0 $dx1 $dy1]] } }
    }
  }
  # optional OpenROAD pin access analysis (DRT-0073 = no access point), evidence only
  if {[pgpc_env PIN_ACCESS 0] eq "1"} {
    if {[catch {pin_access -verbose} e]} { puts "PG_PIN_CHECK pin_access unavailable: $e" } else { puts "PG_PIN_CHECK pin_access done" }
  }
  if {[pgpc_env OUT ""] ne ""} {
    set f [open [pgpc_env OUT ""] w]
    puts $f "kind\tname\tlayer_or_master\tx_dbu\ty_dbu\tpg_net\tgap_dbu\tspacing_dbu\tface_um"
    foreach r $rows { puts $f [join $r "\t"] }
    close $f
  }
  set res [expr {($nbad + $nbadc) == 0 ? "PASS" : "FAIL"}]
  puts [format "PG_PIN_CHECK RESULT %s pins=%d bad_pins=%d cells=%d bad_cells=%d fixed_under_crossing=%d band_um=%s dbu=%d" $res $npins $nbad $ncells $nbadc $nfixed [pgpc_env BAND_UM 80] $dbu]
  return $res
}
# Hook mode (gen OT_PG_PIN_CHECK=1: sourced from POST_PDN_TCL with ::pgpc_hook 1): the open DB is checked, FAIL raises an error
# "FAIL_PREFLOOR pg_pin_check ..." so the kit stops after PDN (minutes) instead of failing DRT-0255 hours later in route.
if {[info exists ::pgpc_hook] && $::pgpc_hook} {
  set ::pgpc_res [pgpc_run]
  if {$::pgpc_res ne "PASS" && [pgpc_env OT_PG_PIN_CHECK_WARN 0] ne "1"} { error "FAIL_PREFLOOR pg_pin_check: pins on PG tracks within the face band (PGPIN-0255 lines above)" }
  return
}
read_db [pgpc_env ODB ""]
set ::pgpc_res [pgpc_run]
# APPLY_KEEPOUT=1 (proof mode): apply the PG-AWARE-1 cell keepout (blockages + detailed_placement) to this DB and check again;
# the AFTER result is the gate result (cells moved out of every crossing in the band).
if {[pgpc_env APPLY_KEEPOUT 0] eq "1"} {
  set ::env(OT_PG_CELL_KEEPOUT) 1
  source [file join [file dirname [info script]] pg_cell_keepout.tcl]
  ot_pgcko_add
  puts "PG_PIN_CHECK AFTER_KEEPOUT"
  set ::pgpc_res [pgpc_run]
}
if {[pgpc_env NOEXIT 0] ne "1"} { exit [expr {$::pgpc_res eq "PASS" ? 0 : 3}] }
