# HOLD-FLOW-R 11-16 (closure lever 1): targeted INTERNAL-endpoint hold insert for the post-route ECO.
# Sourced by prd_hook.tcl in place of repair_timing -hold when OT_PRD_HOLD_PLAN=<plan.tsv> (hold_eco_internal.py plan).
# Each plan row "capture_pin<TAB>n" gets n HB4xp67 in series in front of that capture pin, on free row sites (or removed
# filler) within OT_HOLD_SLOT_RADIUS_UM (7.2) of the capture flop.  Only the capture pin moves to the new chain: every other
# sink of the net, every placement, master and clock stays as it was.  prd_hook.tcl then runs its normal incremental
# GRT + route-keep DRT, so only the touched nets are re-routed.  Fails closed (error) on any structural surprise.
proc ot_hei_read_plan {path} {
  set fh [open $path r]; set rows {}
  foreach ln [split [read $fh] \n] {
    if {$ln eq "" || [string index $ln 0] eq "#"} continue
    lassign [split $ln \t] pin n
    if {![string is integer -strict $n] || $n < 1} { close $fh; error "OT_HEI bad plan row: $ln" }
    lappend rows [list $pin $n]
  }
  close $fh
  return $rows
}
proc ot_hei_run {} {
  set plan [ot_hei_read_plan $::env(OT_PRD_HOLD_PLAN)]
  set radius [expr {[info exists ::env(OT_HOLD_SLOT_RADIUS_UM)] && $::env(OT_HOLD_SLOT_RADIUS_UM) ne "" ? $::env(OT_HOLD_SLOT_RADIUS_UM) : 7.2}]
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set cells [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
  if {[llength $cells] != 1} { error "OT_HEI HB4 source is not unique" }
  unset_dont_use $cells
  set master [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
  if {$master eq "NULL"} { error "OT_HEI no HB4xp67 master in the DB" }
  set mw [$master getWidth]
  # rows first: a macro spans many rows, so its occupancy (plus a halo) goes into every row it overlaps
  set rows {}; set rowh 0
  foreach r [$blk getRows] {
    set bb [$r getBBox]; lappend rows [list [$bb yMin] [$bb xMin] [$bb xMax] [$r getOrient] [[$r getSite] getWidth]]
    set rowh [expr {max($rowh, [$bb yMax] - [$bb yMin])}]
  }
  set halo [expr {round([expr {[info exists ::env(OT_HEI_MACRO_HALO_UM)] && $::env(OT_HEI_MACRO_HALO_UM) ne "" ? $::env(OT_HEI_MACRO_HALO_UM) : 0.0}] * $dbu)}]
  set occ [dict create]; set fill [dict create]
  foreach i [$blk getInsts] {
    set bb [$i getBBox]; set y [$bb yMin]
    if {[string match FILLER* [$i getName]] || [[$i getMaster] getType] eq "CORE_SPACER"} {
      dict lappend fill $y [list [$bb xMin] [$bb xMax] $i]
    } elseif {[[$i getMaster] isBlock] || ([$bb yMax] - $y) > $rowh} {
      foreach rw $rows {
        set ry [lindex $rw 0]
        if {$ry < [$bb yMax] + $halo && $ry + $rowh > $y - $halo} { dict lappend occ $ry [list [expr {[$bb xMin] - $halo}] [expr {[$bb xMax] + $halo}]] }
      }
    } else {
      dict lappend occ $y [list [$bb xMin] [$bb xMax]]
    }
  }
  set total 0; set nruns 0; set removed 0; set out [open $::env(RESULTS_DIR)/hold_eco_internal_cells.tsv w]
  puts $out "capture\tstage\tname\tx_um\ty_um\torient"
  foreach row $plan {
    lassign $row capture n
    set p [get_pins -quiet $capture]
    if {[llength $p] != 1} { error "OT_HEI capture not unique: $capture" }
    set it [sta::sta_to_db_pin $p]
    if {$it eq "NULL" || $it eq "" || ![$it isInputSignal]} { error "OT_HEI not a signal input: $capture" }
    set oldnet [$it getNet]
    if {$oldnet eq "NULL" || [$oldnet getSigType] ne "SIGNAL"} { error "OT_HEI capture not on an ordinary data net: $capture" }
    set inst [$it getInst]
    # the capture PIN decides the radius (a macro input pin sits at the macro edge, not at the macro centre)
    set bb [$it getBBox]
    if {$bb eq "NULL" || $bb eq ""} { set bb [$inst getBBox] }
    set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]; set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
    set rad [expr {round($radius * $dbu)}]
    set cands {}
    foreach rw $rows {
      lassign $rw ry rx0 rx1 ror sw
      if {abs($ry - $cy) > $rad} continue
      set busy [expr {[dict exists $occ $ry] ? [lsort -integer -index 0 [dict get $occ $ry]] : {}}]
      set x $rx0
      foreach b [concat $busy [list [list $rx1 $rx1]]] {
        lassign $b b0 b1
        if {$b0 > $rx1} { set b0 $rx1 }   ;# a row segment ends where its macro cut starts: never plan past the segment
        # free gap [x, b0): candidate x positions snapped to the site grid
        for {set px [expr {$rx0 + (($x - $rx0 + $sw - 1) / $sw) * $sw}]} {$px + $mw <= $b0} {incr px $sw} {
          set d [expr {abs($px + $mw / 2 - $cx) + abs($ry - $cy)}]
          if {$d <= $rad} { lappend cands [list $d $px $ry $ror] }
        }
        if {$b1 > $x} { set x $b1 }
      }
    }
    set cands [lsort -integer -index 0 $cands]
    set chosen {}
    foreach c $cands {
      lassign $c d px ry ror
      set clash 0
      foreach s $chosen { lassign $s sx sy; if {$sy == $ry && $px < $sx + $mw && $sx < $px + $mw} { set clash 1; break } }
      if {$clash} continue
      lappend chosen [list $px $ry $ror]
      dict lappend occ $ry [list $px [expr {$px + $mw}]]
      if {[llength $chosen] == $n} break
    }
    if {[llength $chosen] < $n} { error "OT_HEI no free site within $radius um of $capture: [llength $chosen] of $n" }
    # remove removable filler under the chosen slots
    foreach s $chosen {
      lassign $s px ry ror
      if {![dict exists $fill $ry]} continue
      foreach f [dict get $fill $ry] {
        lassign $f f0 f1 fi
        if {$f0 < $px + $mw && $px < $f1 && [$blk findInst [$fi getName]] ne "NULL"} { odb::dbInst_destroy $fi; incr removed }
      }
    }
    set oldn [$oldnet getName]; set k 0; set prev {}
    foreach s $chosen {
      lassign $s px ry ror
      regsub -all {[^A-Za-z0-9_]} $capture _ safe
      set name hold_int_${safe}_$k
      if {[$blk findInst $name] ne "NULL"} { error "OT_HEI existing name $name" }
      set x [expr {double($px) / $dbu}]; set y [expr {double($ry) / $dbu}]
      set before [llength [$blk getInsts]]
      insert_buffer -buffer_cell HB4xp67_ASAP7_75t_R -load_pins [list $p] -location [list $x $y] -buffer_name $name -net_name ${name}_n
      if {[llength [$blk getInsts]] != $before + 1} { error "OT_HEI insert_buffer made no single cell for $capture" }
      # the new cell drives the capture pin's net (the name asked for is a hint, as in the QC coll_n pilot)
      set drivers {}
      foreach pt [[$it getNet] getITerms] { if {[[$pt getMTerm] getIoType] eq "OUTPUT"} { lappend drivers [$pt getInst] } }
      if {[llength $drivers] != 1} { error "OT_HEI insert_buffer did not leave one driver on $capture" }
      set ni [lindex $drivers 0]
      if {[[$ni getMaster] getName] ne "HB4xp67_ASAP7_75t_R"} { error "OT_HEI inserted master identity $capture" }
      set name [$ni getName]
      $ni setOrient $ror; $ni setLocation $px $ry; $ni setPlacementStatus PLACED
      foreach mt [[$ni getMaster] getMTerms] {
        if {[$mt getSigType] ni {POWER GROUND}} continue
        set pg [$blk findNet [$mt getName]]
        if {$pg eq "NULL"} { error "OT_HEI missing PG net [$mt getName]" }
        if {[[$ni findITerm [$mt getName]] getNet] eq "NULL"} { [$ni findITerm [$mt getName]] connect $pg }
      }
      puts $out "$capture\t$k\t$name\t$x\t$y\t$ror"
      incr k; incr total
    }
    incr nruns
  }
  close $out
  puts "OT_HEI inserted $total HB4 at $nruns capture pins, removed $removed filler cells (radius $radius um)"
  set_dont_use $cells
}
ot_hei_run
