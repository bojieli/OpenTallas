# Landed from DRT0255-PROOF-1115 variant C3b (drt0255-proof tools/pg_pair_cap.tcl, byte-identical body; C3b: iteration 1 of t37 detail route 0 x DRT-0255).
# Sourced last from grt_pre.tcl only with OT_PGCAP=1 (gen env; default off = kits byte-equal).  No file change in the DB: GRT-internal setting.
# DRT0255-PROOF-1115 variant C (FABLE-PD-DRT-1350 fix 1): per-gcell GRT capacity cut on the PG-pair rows/columns of the
# PG layers themselves: M6 (horizontal) rows covering an M6 stripe, M5/M7 (vertical) columns covering an M5/M7 stripe.
# set_global_routing_region_adjustment is a GRT-internal setting (not in the DB): nothing to remove afterwards.
# env OT_PGCAP_LAYERS (default "M5 M6 M7"), OT_PGCAP_ADJ (default 1.0), OT_PGCAP_MARGIN_DBU (default 0).
# OT_PGCAP_FINITE_EXTENT=1: macro PG straps reserve only their actual longitudinal
# extent, enlarged by signal half-width + the PG-width spacing and by full gcells.
# The old full-die extrusion remains the default until the physical pilot passes.
proc ot_pgcap_finite_region {reg die gc eps} {
  lassign $reg a b c d
  lassign $die dx0 dy0 dx1 dy1
  if {$gc > 0} {
    set a [expr {int(floor(double($a)/$gc))*$gc-$eps}]
    set b [expr {int(floor(double($b)/$gc))*$gc-$eps}]
    set c [expr {int(ceil(double($c)/$gc))*$gc+$eps}]
    set d [expr {int(ceil(double($d)/$gc))*$gc+$eps}]
  }
  return [list [expr {max($a,$dx0)}] [expr {max($b,$dy0)}] [expr {min($c,$dx1)}] [expr {min($d,$dy1)}]]
}
proc ot_pgcap_add {} {
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  set layers {M5 M6 M7}; if {[info exists ::env(OT_PGCAP_LAYERS)] && $::env(OT_PGCAP_LAYERS) ne ""} { set layers $::env(OT_PGCAP_LAYERS) }
  set adj 1.0; if {[info exists ::env(OT_PGCAP_ADJ)] && $::env(OT_PGCAP_ADJ) ne ""} { set adj $::env(OT_PGCAP_ADJ) }
  set mg 0; if {[info exists ::env(OT_PGCAP_MARGIN_DBU)] && $::env(OT_PGCAP_MARGIN_DBU) ne ""} { set mg $::env(OT_PGCAP_MARGIN_DBU) }
  set gcum 0.57; if {[info exists ::env(OT_PGCAP_GCELL_UM)] && $::env(OT_PGCAP_GCELL_UM) ne ""} { set gcum $::env(OT_PGCAP_GCELL_UM) }
  set die [$blk getDieArea]; set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set finite [expr {[info exists ::env(OT_PGCAP_FINITE_EXTENT)] && $::env(OT_PGCAP_FINITE_EXTENT) eq "1"}]
  array set seen {}; array set n {}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] { foreach w [$sw getWires] {
      if {[$w isVia]} continue
      set L [$w getTechLayer]; if {$L eq "NULL"} continue
      set ln [$L getName]; if {[lsearch $layers $ln] < 0} continue
      set x0 [$w xMin]; set y0 [$w yMin]; set x1 [$w xMax]; set y1 [$w yMax]
      if {[$L getDirection] eq "HORIZONTAL"} { if {($x1-$x0) <= ($y1-$y0)} continue; set key "$ln $y0 $y1"; set reg [list $dx0 [expr {$y0-$mg}] $dx1 [expr {$y1+$mg}]]
      } else { if {($y1-$y0) <= ($x1-$x0)} continue; set key "$ln $x0 $x1"; set reg [list [expr {$x0-$mg}] $dy0 [expr {$x1+$mg}] $dy1] }
      if {$finite} {
        set sp [$L getSpacing]
        if {$ln eq "M6"} { set width [expr {$y1-$y0}]; set length [expr {$x1-$x0}]
        } else { set width [expr {$x1-$x0}]; set length [expr {$y1-$y0}] }
        if {![catch {$L getSpacing $width $length} wide_sp] && $wide_sp > $sp} {set sp $wide_sp}
        set end_guard [expr {$sp + ([$L getWidth]+1)/2}]
        if {$ln eq "M6"} {set reg [list [expr {$x0-$end_guard}] [expr {$y0-$mg}] [expr {$x1+$end_guard}] [expr {$y1+$mg}]]
        } else {set reg [list [expr {$x0-$mg}] [expr {$y0-$end_guard}] [expr {$x1+$mg}] [expr {$y1+$end_guard}]]}
        set key [list $ln {*}$reg]
      }
      if {[info exists seen($key)]} continue
      set seen($key) 1
      lassign $reg a b c d
      set eps 10; if {[info exists ::env(OT_PGCAP_EPS_DBU)] && $::env(OT_PGCAP_EPS_DBU) ne ""} { set eps $::env(OT_PGCAP_EPS_DBU) }
      # gcell-aligned (FABLE/GENBUG: region adjustment only reaches gcells lying fully inside the region): origin 0, tile OT_PGCAP_GCELL_UM (0.57)
      set gc [expr {int(round($gcum*[$tech getDbUnitsPerMicron]))}]
      if {$gc > 0} {
        if {$ln eq "M6"} { set b [expr {($b/$gc)*$gc}]; set d [expr {(($d+$gc-1)/$gc)*$gc}]
          set b [expr {$b-$eps}]; set d [expr {$d+$eps}]; set c [expr {((($c+$gc-1)/$gc)+1)*$gc}]
        } else { set a [expr {($a/$gc)*$gc}]; set c [expr {(($c+$gc-1)/$gc)*$gc}]
          set a [expr {$a-$eps}]; set c [expr {$c+$eps}]; set d [expr {((($d+$gc-1)/$gc)+1)*$gc}] }
      }
      if {$finite} {
        # Start from the real stripe again: the legacy branch above deliberately
        # extrudes a full row/column. This branch rounds every finite edge out.
        if {$ln eq "M6"} {set reg [list [expr {$x0-$end_guard}] [expr {$y0-$mg}] [expr {$x1+$end_guard}] [expr {$y1+$mg}]]
        } else {set reg [list [expr {$x0-$mg}] [expr {$y0-$end_guard}] [expr {$x1+$mg}] [expr {$y1+$end_guard}]]}
        lassign [ot_pgcap_finite_region $reg [list $dx0 $dy0 $dx1 $dy1] $gc $eps] a b c d
      }
      # clamp to the die (GRT-0067: region must lie inside the die area)
      if {$a < $dx0} {set a $dx0}; if {$b < $dy0} {set b $dy0}; if {$c > $dx1} {set c $dx1}; if {$d > $dy1} {set d $dy1}
      # microns for the Tcl command
      set u [$tech getDbUnitsPerMicron]
      if {[catch {set_global_routing_region_adjustment [list [expr {double($a)/$u}] [expr {double($b)/$u}] [expr {double($c)/$u}] [expr {double($d)/$u}]] -layer $ln -adjustment $adj} err]} {
        puts "OT_PGCAP error $ln: $err"; if {![info exists nerr]} {set nerr 0}; incr nerr; continue
      }
      if {![info exists n($ln)]} { set n($ln) 0 }; incr n($ln)
    } }
  }
  if {[info exists nerr]} {puts "OT_PGCAP errors $nerr"}
  puts "OT_PGCAP region adjustments (adj $adj margin $mg dbu gcell_um $gcum eps_dbu $eps) by layer [array get n]"
}
