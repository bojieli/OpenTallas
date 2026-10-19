# die_tie_rows.tcl -- r8 die PDN (Q-COMPUTE-DIE, 2026-10-15): standard-cell rows ONLY where die-top cells sit.
#
# WHY (measured): the compute die top holds hard masters plus 4,747 ASAP7 tie cells (strap constants).  Since 58533b5a0
# the die PDN gives those cells a die-wide M1/M2 followpin + M3..M7 ladder: 96,064 full-width rows (32.4 mm) and
# 4.32/8.64-um stripes over 841 mm2, i.e. ~10^9 rail/stripe crossings to via and trim against 6,386 macro obstructions.
# C19s and C21sa were killed by the 420 GiB cgroup (4 h 47 min / 2 h 57 min, still "Inserting grid: core"); the r7 PDN
# without that ladder took 66 min / 27 GB on the C3 case.
# r8: every die-top standard cell keeps a REAL supply: literal M1/M2 followpin rails on rows that exist only around the
# cells (row segment = cell +- OT_TIE_ROW_HALF um inside the free run), each rail stacked M2 -> M9 onto the die core
# M9 bump stripes (add_pdn_connect {M2 M9}).  A cell whose row segment would not cross both a VDD and a VSS M9 stripe,
# or whose VDD/VSS rail lies under an opposite-net core M8 stripe (the stack would short), is moved to the nearest row
# position that satisfies both (a tie is a constant source: position only changes its signal wire); rows keep a
# 1.08-um halo from every macro so no rail or stack lands on a macro edge.  check_power_grid
# VDD/VSS and the literal M1 contact check (die_constant_pg_check.tcl) still decide PASS; nothing is waived.
#
# Usage (inside run_pdn.tcl, after read_db, before pdn.tcl):
#   source die_tie_rows.tcl; ot_tie_rows <m8_pitch> <m8_width> <m9_pitch> <m9_width>
namespace eval ot_tie_rows {}

proc ot_tie_rows {p8 w8 p9 w9 {half 12.0} {clear 0.6} {halo 1.08} {off8 0.0} {off9 0.0} {preserve_clock_cells {}}} {
  # Default off. The final argument is an explicit manifest-derived list, not a
  # name-pattern exemption. Clocks must already occupy PG-safe fixed sites.
  # This remains a row/PG candidate: continuity, literal contact, short and
  # independent actual-pin reach audits must pass before any timing adoption.
  # off8 / off9 (KV die 2026-10-15): the core M8 / M9 -offset of the grid (the compute die's is 0; the KV die's 2.0)
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  set core [$block getCoreArea]
  set cx0 [expr {[$core xMin] + round($off9*$dbu)}]; set cy0 [expr {[$core yMin] + round($off8*$dbu)}]
  set P8 [expr {round($p8*$dbu)}]; set P9 [expr {round($p9*$dbu)}]
  set HALF [expr {round($half*$dbu)}]; set CLR [expr {round($clear*$dbu)}]
  set W9 [expr {round($w9*$dbu)}]
  # macro halo: rails and their M2->M9 stacks stay clear of macro edges (C21sa-r8 try 1: a rail on band_lanes_1's top
  # edge left a VSS M2 channel PDN-0179 could not repair)
  set HL [expr {round($halo*$dbu)}]
  set rows {}; set site NULL
  foreach row [$block getRows] {
    set bb [$row getBBox]
    if {$site eq "NULL"} { set site [$row getSite] }
    lappend rows [list [$bb yMin] [$bb xMin] [$bb xMax] [$bb yMax] [$row getSpacing] [$row getOrient]]
  }
  if {![llength $rows]} { error "OT_TIE_ROWS: no rows" }
  set rows [lsort -integer -index 0 $rows]
  set cells {}; set obstacles {}
  foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {[$m isBlock] || [$m isPad]} {
      set bb [$inst getBBox]
      lappend obstacles [list [expr {[$bb xMin]-$HL}] [expr {[$bb yMin]-$HL}] [expr {[$bb xMax]+$HL}] [expr {[$bb yMax]+$HL}]]
    } else { lappend cells $inst }
  }
  set ::ot_tie_rows::actual_m8 {}; set ::ot_tie_rows::actual_m9 {}
  set preserved {}; set fixed_segs {}; set clock_occupied {}
  if {[llength $preserve_clock_cells]} {
    lassign [ot_clock_rows_prepare $block $dbu $obstacles $preserve_clock_cells $HALF $CLR $P8 $w8 $site] preserved fixed_segs clock_occupied
  }
  # core M8 stripe centres per net (pdngen -starts_with GROUND, two nets per pitch: VSS at offset, VDD at offset+P/2,
  # offset measured to the stripe edge) -- verified against the written shapes by ot_tie_rows_verify after pdngen
  proc ::ot_tie_rows::m8net {yc cy0 P8 w8dbu CLR} {
    if {[dict size $::ot_tie_rows::actual_m8]} {
      dict for {net edge} $::ot_tie_rows::actual_m8 {
        set k [expr {floor(($yc-$edge)/$P8)}]
        foreach kk [list [expr {$k-1}] $k [expr {$k+1}]] {
          set a [expr {$edge+$kk*$P8}]
          if {$yc >= $a-$CLR && $yc <= $a+$w8dbu+$CLR} { return $net }
        }
      }
      return ""
    }
    # returns VSS / VDD if a stripe of that net is within CLR of yc, else ""
    set r [expr {fmod(fmod($yc - $cy0, $P8) + $P8, $P8)}]
    set h [expr {$w8dbu/2.0}]
    foreach {c net} [list $h VSS [expr {$P8/2.0+$h}] VDD [expr {$P8+$h}] VSS [expr {-$P8/2.0+$h}] VDD] {
      if {abs($r-$c) <= $h+$CLR} { return $net }
    }
    return ""
  }
  set w8d [expr {round($w8*$dbu)}]
  proc ::ot_tie_rows::m9ok {lo hi cx0 P9 W9} {
    if {[dict size $::ot_tie_rows::actual_m9]} {
      dict for {net stripes} $::ot_tie_rows::actual_m9 {
        set found 0
        set start [expr {max(0,[lsearch -bisect -integer -index 0 $stripes $lo])}]
        foreach r [lrange $stripes $start end] {
          lassign $r a b c d
          if {$a > $hi} break
          if {$a >= $lo+300 && $c <= $hi-300} {set found 1; break}
        }
        if {!$found} {return 0}
      }
      return 1
    }
    # need a VSS (offset edge 0) and a VDD (P9/2) stripe fully inside [lo,hi] with 0.3 um margin
    set got {}
    set k [expr {int(floor(double($lo-$cx0)/$P9))-1}]
    while {$cx0 + $k*$P9 <= $hi} {
      foreach {off net} [list 0 VSS [expr {$P9/2.0}] VDD] {
        set a [expr {$cx0 + $k*$P9 + $off}]
        if {$a >= $lo+300 && $a+$W9 <= $hi-300} { dict set got $net 1 }
      }
      incr k
    }
    return [expr {[dict exists $got VSS] && [dict exists $got VDD]}]
  }
  set moved 0; set maxd 0; set segs $fixed_segs; set mspan {}; set kspan {}
  foreach inst $cells {
    if {[dict exists $preserved [$inst getName]]} { continue }
    lassign [$inst getLocation] tx ty
    set to [$inst getOrient]
    $inst setPlacementStatus PLACED
    set mw [[$inst getMaster] getWidth]; set mh [[$inst getMaster] getHeight]
    set start [lsearch -bisect -integer -index 0 $rows $ty]; if {$start < 0} { set start 0 }
    set done 0
    for {set delta 0} {$delta < [llength $rows] && !$done} {incr delta} {
      foreach ri [expr {$delta ? [list [expr {$start-$delta}] [expr {$start+$delta}]] : [list $start]}] {
        if {$ri < 0 || $ri >= [llength $rows] || $done} continue
        lassign [lindex $rows $ri] ry rx ex ey pitch orient
        if {$mh > $ey-$ry} continue
        # rails of this row for this master: set tentatively and read the actual pin boxes
        $inst setOrient $orient; $inst setLocation $tx $ry
        set bad 0
        foreach net {VDD VSS} {
          set bb [[$inst findITerm $net] getBBox]
          set under [::ot_tie_rows::m8net [expr {([$bb yMin]+[$bb yMax])/2.0}] $cy0 $P8 $w8d $CLR]
          if {$under ne "" && $under ne $net} { set bad 1 }
        }
        if {$bad} continue
        if {![dict exists $mspan $ri]} {
          set sp {}
          foreach b $obstacles { lassign $b a bb c d; if {$bb < $ry+$mh && $d > $ry} { lappend sp [list $a $c] } }
          dict set mspan $ri $sp
        }
        set spans [dict get $mspan $ri]
        foreach r $clock_occupied {
          lassign $r a b c d
          if {$b < $ry+$mh && $d > $ry} { lappend spans [list $a $c] }
        }
        if {[dict exists $kspan $ri]} { set spans [concat $spans [dict get $kspan $ri]] }
        lappend spans [list $ex $ex]
        set cursor $rx; set best {}; set bd Inf
        foreach sp [lsort -integer -index 0 $spans] {
          lassign $sp left right
          set lo $cursor; set hi [expr {min($left,$ex)}]
          if {$hi - $lo >= $mw} {
            set x [expr {max($lo, min($tx, $hi-$mw))}]
            set x [expr {$rx + int(ceil(double($x-$rx)/$pitch))*$pitch}]
            if {$x+$mw <= $hi && abs($x-$tx) < $bd} {
              # PG reach uses the macro-free run (other die-top cells share the rails)
              set flo $rx; set fhi $ex
              foreach m [dict get $mspan $ri] { lassign $m ma mc; if {$mc <= $x && $mc > $flo} { set flo $mc }; if {$ma >= $x+$mw && $ma < $fhi} { set fhi $ma } }
              set s0 [expr {max($flo, $x-$HALF)}]; set s1 [expr {min($fhi, $x+$mw+$HALF)}]
              if {[::ot_tie_rows::m9ok $s0 $s1 $cx0 $P9 $W9]} { set best [list $x $s0 $s1]; set bd [expr {abs($x-$tx)}] }
            }
          }
          set cursor [expr {max($cursor,$right)}]
          if {$cursor >= $ex} break
        }
        if {$best eq ""} continue
        lassign $best x s0 s1
        $inst setLocation $x $ry; $inst setPlacementStatus FIRM
        dict lappend kspan $ri [list $x [expr {$x+$mw}]]
        lappend segs [list $ry $orient [expr {$rx + (($s0-$rx+$pitch-1)/$pitch)*$pitch}] [expr {$rx + (($s1-$rx)/$pitch)*$pitch}] $pitch]
        if {$delta || $x != $tx} { incr moved; set d [expr {abs($ry-$ty)+abs($x-$tx)}]; if {$d > $maxd} { set maxd $d } }
        set done 1
      }
    }
    if {!$done} { error "OT_TIE_ROWS: no legal PG-connectable position for [$inst getName]" }
  }
  # No clock mutation until every preserved site has passed preflight. Bind
  # literal PG pins without changing any signal net or clock coordinate.
  dict for {name original} $preserved {
    set inst [$block findInst $name]
    if {[list [$inst getLocation] [$inst getOrient]] ne $original} {error "OT_CLOCK_ROWS: fixed clock moved: $name"}
    foreach net {VDD VSS} {[$inst findITerm $net] connect [$block findNet $net]}
    $inst setPlacementStatus FIRM
  }
  # rebuild rows: merged segments per (y, orient)
  set merged {}
  foreach s [lsort -integer -index 2 $segs] {
    lassign $s y o a b pitch
    set k "$y/$o"
    if {[dict exists $merged $k]} {
      set L [dict get $merged $k]; lassign [lindex $L end] pa pb
      if {$a <= $pb} { lset L end [list $pa [expr {max($pb,$b)}]] } else { lappend L [list $a $b] }
      dict set merged $k $L
    } else { dict set merged $k [list [list $a $b]] }
  }
  set nold [llength [$block getRows]]
  foreach row [$block getRows] { odb::dbRow_destroy $row }
  set n 0; set sites 0
  dict for {k L} $merged {
    lassign [split $k /] y o
    foreach iv $L {
      lassign $iv a b
      set num [expr {($b-$a)/54}]
      if {$num < 1} continue
      odb::dbRow_create $block "TROW_$n" $site $a $y $o HORIZONTAL $num 54
      incr n; incr sites $num
    }
  }
  puts "OT_TIE_ROWS cells=[llength $cells] moved=$moved max_move_um=[expr {$maxd/double($dbu)}] rows_before=$nold rows_after=$n sites=$sites preserved_clock_cells=[dict size $preserved] power_qualified=0"
}

# Readonly preflight for explicit fixed clock cells. Actual core stripe phase is
# read from the existing supply polygons, because getCoreArea changes with rows.
# Return row segments/occupancy only after ALL sites pass. No row-only PASS.
proc ot_clock_rows_prepare {block dbu obstacles names HALF CLR P8 w8 site} {
  set die [$block getDieArea]; set phases {}; set stripes {}
  set width [expr {round($w8*$dbu)}]; set margin [expr {round(.3*$dbu)}]
  set pitch [$site getWidth]; set height [$site getHeight]
  if {$pitch != 54 || $height != 270 || $dbu != 1000} {error "OT_CLOCK_ROWS: unsupported physical site/DBU"}
  foreach name {VDD VSS} {
    set net [$block findNet $name]
    if {$net eq "NULL"} {error "OT_CLOCK_ROWS: actual supply missing: $name"}
    set edges {}; set vertical {}
    foreach sw [$net getSWires] {
      foreach r [$sw getWires] {
        if {[$r isVia]} continue
        set layer [[$r getTechLayer] getName]
        if {$layer eq "M8" && [$r xMax]-[$r xMin] > ([$die xMax]-[$die xMin])/2} {
          if {[$r yMax]-[$r yMin] != $width} {error "OT_CLOCK_ROWS: unexpected actual M8 width"}
          dict set edges [expr {(([$r yMin]%$P8)+$P8)%$P8}] 1
        }
        if {$layer eq "M9" && [$r yMax]-[$r yMin] > ([$die yMax]-[$die yMin])/2} {
          lappend vertical [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
        }
      }
    }
    if {[dict size $edges] != 1 || ![llength $vertical]} {error "OT_CLOCK_ROWS: ambiguous/missing actual mesh $name"}
    dict set phases $name [lindex [dict keys $edges] 0]
    dict set stripes $name [lsort -integer -index 0 $vertical]
  }
  set preserved {}; set segs {}; set occupied {}; set obstacle_bins {}
  foreach r $obstacles {
    lassign $r a b c d
    for {set bin [expr {int(floor(double($b)/100000))}]} {$bin <= int(floor(double($d)/100000))} {incr bin} {
      dict lappend obstacle_bins $bin $r
    }
  }
  foreach name $names {
    if {[dict exists $preserved $name]} {error "OT_CLOCK_ROWS: duplicate clock $name"}
    set inst [$block findInst $name]
    if {$inst eq "NULL"} {error "OT_CLOCK_ROWS: clock missing: $name"}
    set master [$inst getMaster]
    if {[$master isBlock] || [$master isPad] || ![$inst isPlaced]} {error "OT_CLOCK_ROWS: not a placed clock cell: $name"}
    lassign [$inst getLocation] x y
    set orient [expr {($y/$height)%2 ? "MX" : "R0"}]
    if {$x%$pitch || $y%$height || [$inst getOrient] ne $orient || [$master getHeight] != $height} {error "OT_CLOCK_ROWS: unsupported clock site: $name"}
    set bb [$inst getBBox]; set xmin [$bb xMin]; set xmax [$bb xMax]; set bottom [$bb yMin]; set top [$bb yMax]
    foreach net {VDD VSS} {
      set pin [$inst findITerm $net]
      if {$pin eq "NULL"} {error "OT_CLOCK_ROWS: missing actual PG pin $name/$net"}
      if {[$pin getNet] ne "NULL" && [$pin getNet] ne [$block findNet $net]} {error "OT_CLOCK_ROWS: wrong clock PG net $name/$net"}
      set q [$pin getBBox]
      set xmin [expr {min($xmin,[$q xMin])}]; set xmax [expr {max($xmax,[$q xMax])}]
      set bottom [expr {min($bottom,[$q yMin])}]; set top [expr {max($top,[$q yMax])}]
      set other [expr {$net eq "VDD" ? "VSS" : "VDD"}]; set edge [dict get $phases $other]
      set k [expr {int(floor(double([$q yMin]-$edge)/$P8))}]
      foreach kk [list [expr {$k-1}] $k [expr {$k+1}]] {
        set a [expr {$edge+$kk*$P8}]
        if {[$q yMin] <= $a+$width+$CLR && [$q yMax] >= $a-$CLR} {error "OT_CLOCK_ROWS: unsafe actual M8 phase $name/$net"}
      }
    }
    set lo [$die xMin]; set hi [$die xMax]
    set nearby {}
    for {set bin [expr {int(floor(double($bottom)/100000))}]} {$bin <= int(floor(double($top)/100000))} {incr bin} {
      if {[dict exists $obstacle_bins $bin]} {set nearby [concat $nearby [dict get $obstacle_bins $bin]]}
    }
    foreach r $nearby {
      lassign $r a b c d
      if {$b < $top && $d > $bottom} {
        if {$a < $xmax && $c > $xmin} {error "OT_CLOCK_ROWS: clock PG footprint inside macro halo: $name"}
        if {$c <= $xmin} {set lo [expr {max($lo,$c)}]}
        if {$a >= $xmax} {set hi [expr {min($hi,$a)}]}
      }
    }
    set lo [expr {int(ceil(double(max($lo,$x-$HALF))/$pitch))*$pitch}]
    set hi [expr {int(floor(double(min($hi,[$bb xMax]+$HALF))/$pitch))*$pitch}]
    foreach net {VDD VSS} {
      set q [[$inst findITerm $net] getBBox]; set found 0
      set vertical [dict get $stripes $net]
      set start [expr {max(0,[lsearch -bisect -integer -index 0 $vertical $lo])}]
      foreach r [lrange $vertical $start end] {
        lassign $r a b c d
        if {$a > $hi} break
        if {$a >= $lo+$margin && $c <= $hi-$margin && $b <= [$q yMin] && $d >= [$q yMax]} {set found 1; break}
      }
      if {!$found} {error "OT_CLOCK_ROWS: no actual M9 stack budget $name/$net"}
    }
    dict set preserved $name [list [$inst getLocation] [$inst getOrient]]
    lappend occupied [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    lappend segs [list $y $orient $lo $hi $pitch]
  }
  set ::ot_tie_rows::actual_m8 $phases; set ::ot_tie_rows::actual_m9 $stripes
  return [list $preserved $segs $occupied]
}

# Explicit post-clock candidate entry: preserve EVERY existing cell coordinate
# and existing row coverage. This adds rows/bindings only; no rails or PASS.
# It is not invoked by the default constant-row flow.
proc ot_clock_rows_candidate {names} {
  if {![llength $names]} {error "OT_CLOCK_ROWS: explicit clock manifest required"}
  set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
  if {![llength [$block getRows]]} {error "OT_CLOCK_ROWS: physical site template missing"}
  set site [[lindex [$block getRows] 0] getSite]; set obstacles {}; set old_segs {}
  foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {[$m isBlock] || [$m isPad]} {
      set q [$inst getBBox]
      lappend obstacles [list [expr {[$q xMin]-1080}] [expr {[$q yMin]-1080}] [expr {[$q xMax]+1080}] [expr {[$q yMax]+1080}]]
    }
  }
  lassign [ot_clock_rows_prepare $block $dbu $obstacles $names 12000 600 8640 .48 $site] preserved segs occupied
  foreach row [$block getRows] {
    set q [$row getBBox]
    if {[$row getDirection] ne "HORIZONTAL" || [$row getSpacing] != 54} {error "OT_CLOCK_ROWS: unsupported existing row"}
    lappend old_segs [list [$q yMin] [$row getOrient] [$q xMin] [$q xMax] 54]
  }
  set merged {}; set orientations {}
  foreach s [lsort -integer -index 2 [concat $old_segs $segs]] {
    lassign $s y orient a b pitch
    if {[dict exists $orientations $y] && [dict get $orientations $y] ne $orient} {error "OT_CLOCK_ROWS: conflicting existing row orientation"}
    dict set orientations $y $orient
    set key "$y/$orient"
    if {[dict exists $merged $key]} {
      set intervals [dict get $merged $key]; lassign [lindex $intervals end] pa pb
      if {$a <= $pb} {lset intervals end [list $pa [expr {max($pb,$b)}]]} else {lappend intervals [list $a $b]}
      dict set merged $key $intervals
    } else {dict set merged $key [list [list $a $b]]}
  }
  # All rejecting preflight above precedes physical changes.
  foreach row [$block getRows] {odb::dbRow_destroy $row}
  set count 0
  dict for {key intervals} $merged {
    lassign [split $key /] y orient
    foreach iv $intervals {
      lassign $iv a b
      odb::dbRow_create $block "CLOCK_PG_ROW_$count" $site $a $y $orient HORIZONTAL [expr {($b-$a)/54}] 54
      incr count
    }
  }
  dict for {name original} $preserved {
    set inst [$block findInst $name]
    if {[list [$inst getLocation] [$inst getOrient]] ne $original} {error "OT_CLOCK_ROWS: fixed clock changed: $name"}
    foreach net {VDD VSS} {[$inst findITerm $net] connect [$block findNet $net]}
    $inst setPlacementStatus FIRM
  }
  puts "OT_CLOCK_ROWS_CANDIDATE fixed_clocks=[dict size $preserved] rows=$count rails_created=0 power_qualified=0 timing_qualified=0"
}

# A logical PG binding is insufficient. The explicit clock set must contact
# same-net actual M1 rail polygons; complete check_power_grid and stack-short
# checks are additionally required. The old constant-only check excludes clocks.
proc ot_clock_pg_contact_check {names} {
  if {![llength $names]} {error "OT_CLOCK_PG: explicit clock manifest required"}
  set block [ord::get_db_block]; set rails {}; set checked 0
  foreach netname {VDD VSS} {
    set net [$block findNet $netname]
    if {$net eq "NULL"} {error "OT_CLOCK_PG: supply missing $netname"}
    foreach sw [$net getSWires] {
      foreach r [$sw getWires] {
        if {[$r isVia]} continue
        set layer [$r getTechLayer]
        if {$layer eq "NULL" || [$layer getName] ne "M1"} continue
        for {set bin [expr {int(floor(double([$r yMin])/1000))}]} {$bin <= int(floor(double([$r yMax])/1000))} {incr bin} {
          dict lappend rails "$netname/$bin" [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
        }
      }
    }
  }
  foreach name $names {
    set inst [$block findInst $name]
    if {$inst eq "NULL"} {error "OT_CLOCK_PG: clock missing $name"}
    foreach netname {VDD VSS} {
      set pin [$inst findITerm $netname]
      if {$pin eq "NULL" || [$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $netname} {error "OT_CLOCK_PG: missing actual PG binding $name/$netname"}
      set geometries 0
      foreach mp [[$pin getMTerm] getMPins] {
        foreach g [$mp getGeometry] {
          if {[[$g getTechLayer] getName] ne "M1"} {error "OT_CLOCK_PG: unsupported clock PG pin layer"}
          incr geometries
        }
      }
      if {$geometries != 1} {error "OT_CLOCK_PG: unsupported clock PG pin geometry"}
      set q [$pin getBBox]; set contact 0
      for {set bin [expr {int(floor(double([$q yMin])/1000))}]} {$bin <= int(floor(double([$q yMax])/1000)) && !$contact} {incr bin} {
        if {![dict exists $rails "$netname/$bin"]} continue
        foreach r [dict get $rails "$netname/$bin"] {
          lassign $r a b c d
          if {[$q xMin] < $c && [$q xMax] > $a && [$q yMin] < $d && [$q yMax] > $b} {set contact 1; break}
        }
      }
      if {!$contact} {error "OT_CLOCK_PG: no literal M1 contact $name/$netname"}
      incr checked
    }
  }
  puts "OT_CLOCK_PG_CONTACT checked_pins=$checked continuity_qualified=0"
}

# after pdngen (fail closed): no M7-M8 / M8-M9 via of a die-top-cell rail stack may overlap an opposite-net M8 wire
# (core stripe OR macro-grid stripe).  Connectivity is check_power_grid's job; this is the short check of the stacks.
proc ot_tie_rows_verify {p8 w8} {
  set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
  set bands {}
  foreach row [$block getRows] { set bb [$row getBBox]; lappend bands [list [expr {[$bb yMin]-300}] [expr {[$bb yMax]+300}] [$bb xMin] [$bb xMax]] }
  set bands [lsort -integer -index 0 $bands]; set bys [lmap b $bands {lindex $b 0}]
  foreach name {VDD VSS} { set m8($name) {}; set st($name) {} }
  foreach name {VDD VSS} {
    foreach sw [[$block findNet $name] getSWires] {
      foreach s [$sw getWires] {
        if {[$s isVia]} {
          set v [$s getBlockVia]
          if {$v eq "NULL" || ![regexp {^via(7_8|8_9)} [$v getName]]} continue
          set x0 [$s xMin]; set y0 [$s yMin]; set x1 [$s xMax]; set y1 [$s yMax]
          set i [lsearch -bisect -integer $bys $y1]
          for {set k $i} {$k >= 0 && $k > $i-4} {incr k -1} {
            lassign [lindex $bands $k] b0 b1 bx0 bx1
            if {$b1 >= $y0 && $b0 <= $y1 && $bx0 <= $x1 && $bx1 >= $x0} { lappend st($name) [list $x0 $y0 $x1 $y1]; break }
          }
        } elseif {[[$s getTechLayer] getName] eq "M8"} {
          lappend m8($name) [list [$s yMin] [$s yMax] [$s xMin] [$s xMax]]
        }
      }
    }
  }
  set short 0; set checked 0
  foreach {n o} {VDD VSS VSS VDD} {
    set w [lsort -integer -index 0 $m8($o)]; set wy [lmap e $w {lindex $e 0}]
    foreach v $st($n) {
      lassign $v x0 y0 x1 y1; incr checked
      set i [lsearch -bisect -integer $wy $y1]
      for {set k $i} {$k >= 0} {incr k -1} {
        lassign [lindex $w $k] a b c d
        if {$a < $y0 - 2*$dbu} break
        if {$b > $y0 && $a < $y1 && $d > $x0 && $c < $x1} { incr short; break }
      }
    }
  }
  if {!$checked} { error "OT_TIE_ROWS_VERIFY: no rail stack vias found near the die-top rows" }
  if {$short} { error "OT_TIE_ROWS_VERIFY: $short of $checked rail-stack M8 vias overlap an opposite-net M8 wire" }
  puts "OT_TIE_ROWS_VERIFY rail_stack_m8_vias=$checked opposite_net_overlaps=0"
}
