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
# Count surviving parallel tracks in every gcell touched by a stripe. Guards
# include all M5 PG stripes intersecting the finite longitudinal span, so a real
# tight pair remains a zero-capacity reservation. Three tracks are required;
# the DRT0255 zero/one-track pair case is never reopened.
proc ot_pgcap_min_free_tracks {tracks x0 x1 y0 y1 gc guards} {
  set first [expr {int(floor(double($x0)/$gc))}]
  set last [expr {int(floor(double($x1-1)/$gc))}]
  set least 1000000
  for {set i $first} {$i <= $last} {incr i} {
    set lo [expr {$i*$gc}]; set hi [expr {($i+1)*$gc}]
    set k0 [expr {[lsearch -sorted -integer -bisect $tracks [expr {$lo-1}]]+1}]
    set k1 [lsearch -sorted -integer -bisect $tracks [expr {$hi-1}]]
    set free 0
    foreach t [lrange $tracks $k0 $k1] {
      set blocked 0
      foreach r $guards {
        lassign $r a b c d
        if {$b >= $y1 || $d <= $y0} continue
        if {$a < $t && $t < $c} {set blocked 1; break}
      }
      if {!$blocked} {incr free}
    }
    if {$free < $least} {set least $free}
  }
  return $least
}
proc ot_pgcap_tight_pair {own guards} {
  lassign $own a b c d
  foreach r $guards {
    if {$r eq $own} continue
    lassign $r x y z w
    if {$a<$z && $c>$x && $b<$w && $d>$y} {return 1}
  }
  return 0
}
proc ot_pgcap_guard_tracks {blk L tracks x0 y0 x1 y1 guard} {
  set k0 [expr {[lsearch -sorted -integer -bisect $tracks [expr {$x0-$guard}]]+1}]
  set k1 [lsearch -sorted -integer -bisect $tracks [expr {$x1+$guard-1}]]
  if {$k1 < $k0} {return 0}
  set hw [expr {[$L getWidth]/2}]
  set a [expr {[lindex $tracks $k0]-$hw}]; set c [expr {[lindex $tracks $k1]+$hw}]
  set die [$blk getDieArea]
  set b [expr {max([$die yMin],$y0-$guard)}]; set d [expr {min([$die yMax],$y1+$guard)}]
  set o [odb::dbObstruction_create $blk $L $a $b $c $d]
  # Existing PG-truth POST_GLOBAL_ROUTE cleanup owns these temporary guards too.
  lappend ::ot_pgtt_obs $o
  return [expr {$k1-$k0+1}]
}
proc ot_pgcap_add {} {
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  set layers {M5 M6 M7}; if {[info exists ::env(OT_PGCAP_LAYERS)] && $::env(OT_PGCAP_LAYERS) ne ""} { set layers $::env(OT_PGCAP_LAYERS) }
  set adj 1.0; if {[info exists ::env(OT_PGCAP_ADJ)] && $::env(OT_PGCAP_ADJ) ne ""} { set adj $::env(OT_PGCAP_ADJ) }
  set mg 0; if {[info exists ::env(OT_PGCAP_MARGIN_DBU)] && $::env(OT_PGCAP_MARGIN_DBU) ne ""} { set mg $::env(OT_PGCAP_MARGIN_DBU) }
  set gcum 0.57; if {[info exists ::env(OT_PGCAP_GCELL_UM)] && $::env(OT_PGCAP_GCELL_UM) ne ""} { set gcum $::env(OT_PGCAP_GCELL_UM) }
  set die [$blk getDieArea]; set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set finite [expr {[info exists ::env(OT_PGCAP_FINITE_EXTENT)] && $::env(OT_PGCAP_FINITE_EXTENT) eq "1"}]
  set local_tracks [expr {[info exists ::env(OT_PGCAP_M5_LEGAL_TRACKS)] && $::env(OT_PGCAP_M5_LEGAL_TRACKS) eq "1"}]
  set m5guards {}; set m5tracks {}; set m5skip 0; set m5guarded 0
  if {$local_tracks} {
    if {!$finite || ![info exists ::env(OT_PG_TRACK_TRUTH)] || $::env(OT_PG_TRACK_TRUTH) ne "1" || ![info exists ::ot_pgtt_obs]} {
      error "OT_PGCAP_M5_LEGAL_TRACKS requires finite extent and active PG-track-truth cleanup"
    }
    set ML [$tech findLayer M5]; set tg [$blk findTrackGrid $ML]
    if {$tg eq "NULL"} {error "M5 legal-track model needs the actual track grid"}
    set m5tracks [lsort -integer -unique [$tg getGridX]]
    foreach nn [$blk getNets] {
      if {![$nn isSpecial] || [$nn getSigType] ni {POWER GROUND}} continue
      foreach ss [$nn getSWires] {foreach ww [$ss getWires] {
        if {[$ww isVia]} continue
        set ll [$ww getTechLayer]; if {$ll eq "NULL" || [$ll getName] ne "M5"} continue
        set aa [$ww xMin];set bb [$ww yMin];set cc [$ww xMax];set dd [$ww yMax]
        if {($dd-$bb) <= ($cc-$aa)} continue
        set sp [$ll getSpacing]
        if {![catch {$ll getSpacing [expr {$cc-$aa}] [expr {$dd-$bb}]} wsp] && $wsp>$sp} {set sp $wsp}
        set guard [expr {$sp+([$ll getWidth]+1)/2}]
        lappend m5guards [list [expr {$aa-$guard}] [expr {$bb-$guard}] [expr {$cc+$guard}] [expr {$dd+$guard}]]
      }}
    }
  }
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
      if {$local_tracks && $ln eq "M5"} {
        set free [ot_pgcap_min_free_tracks $m5tracks $x0 $x1 [expr {$y0-$end_guard}] [expr {$y1+$end_guard}] $gc $m5guards]
        set own_guard [list [expr {$x0-$end_guard}] [expr {$y0-$end_guard}] [expr {$x1+$end_guard}] [expr {$y1+$end_guard}]]
        if {$free >= 3 && ![ot_pgcap_tight_pair $own_guard $m5guards]} {
          # Reopen only genuinely legal tracks. Exact wide-PG spacing and EOL
          # guards remain physical routing obstructions until PG-truth cleanup.
          incr m5guarded [ot_pgcap_guard_tracks $blk $L $m5tracks $x0 $y0 $x1 $y1 $end_guard]
          incr m5skip
          continue
        }
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
  if {$local_tracks} {puts "OT_PGCAP legal_m5_straps $m5skip guarded_tracks $m5guarded min_free 3"}
  if {[info exists nerr]} {puts "OT_PGCAP errors $nerr"}
  puts "OT_PGCAP region adjustments (adj $adj margin $mg dbu gcell_um $gcum eps_dbu $eps) by layer [array get n]"
}
