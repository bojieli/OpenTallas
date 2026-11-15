# pg_track_truth.tcl (FLOW-PGCAP-1 2026-11-13, generalized from HEAD-98's per-kit hook): GRT capacity = DRT-legal tracks
# next to PG stripes.  Sourced by grt_pre.tcl (PRE_GLOBAL_ROUTE) when OT_PG_TRACK_TRUTH=1; grt_post.tcl
# (POST_GLOBAL_ROUTE) calls ot_pgtt_remove before 5_1_grt.odb is written.
#
# Class (DRT-0255 "maze route cannot find path", HEAD hd_ctl_n / hd_host_e / hd_spn_end, S81 ot_s81sl_leaf__t6):
# FastRoute derates a gcell's capacity only for tracks whose wire OVERLAPS a PG stripe; it ignores min spacing.  On the
# die PDN template (M5 0.12/0.072/0.12, M6 and M7 pairs 0.288/0.096/0.288) the gap track of a VSS/VDD pair and the
# track next to each pair edge are counted free but are DRT-illegal, so a 0.57-um gcell row inside an M6 pair (column
# inside an M7 pair) carries GRT capacity with 0 or 1 legal tracks.  GRT lays guides along those rows; DRT fails where
# the row crosses the perpendicular strap pair.
#
# Fix: before global_route, add a temporary routing obstruction over every spacing-illegal track of every PG stripe on
# M4..MAX_ROUTING_LAYER (tracks parallel to the stripe), so GRT capacity equals the DRT-legal tracks.  The obstructions
# are destroyed before 5_1_grt.odb / route.guide are used by DRT, so DRT, PG and sign-off geometry are unchanged.
# A track t is illegal at a stripe [lo, hi] (across the preferred direction) when t + hw + sp > lo and t - hw - sp < hi
# (hw = half the default wire width, sp = the layer's min spacing; see OT_PG_TRACK_TRUTH_WIDE_SPACING).  Geometry-generic: it reads the
# stripes and the track grids of the kit, so it applies to any PDN.  OT_PG_TRACK_TRUTH=0 (or unset) turns it off.
# DRT0255 (FABLE-PD-DRT-1350, class A): with OT_PG_TRACK_TRUTH_MODE=region the per-track obstructions above are replaced by a
# per-gcell capacity cut: set_global_routing_region_adjustment (100 %) on the PG layer over the illegal-track span of every stripe
# (pair rows of M6, pair columns of M5 / M7).  GRT then cannot lay a guide of that layer through a gcell row whose DRT-legal
# tracks are 0 or 1 (the obstruction form still routed 56-70 um M6 guides there).  The adjustment lives in the router, so there is
# nothing to remove before 5_1_grt.odb (ot_pgtt_remove is a no-op); geometry, PG and sign-off are unchanged.  Default (unset or
# "obs") = the obstruction form, byte-identical.
proc ot_pgtt_illegal_span {lo hi hw sp} {
  # the coordinate span (dbu) in which a track centre is illegal next to a stripe [lo, hi]: wire edge within sp of the stripe
  return [list [expr {$lo - $hw - $sp}] [expr {$hi + $hw + $sp}]]
}
proc ot_pgtt_region_mode {} {
  return [expr {[info exists ::env(OT_PG_TRACK_TRUTH_MODE)] && $::env(OT_PG_TRACK_TRUTH_MODE) eq "region"}]
}
proc ot_pgtt_add {} {
  if {![info exists ::env(OT_PG_TRACK_TRUTH)] || $::env(OT_PG_TRACK_TRUTH) ne "1"} { return }
  if {[info exists ::ot_pgtt_obs] && [llength $::ot_pgtt_obs]} { return }
  set ::ot_pgtt_obs {}
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  set maxl 99
  if {[info exists ::env(MAX_ROUTING_LAYER)]} {
    set ml [$tech findLayer $::env(MAX_ROUTING_LAYER)]
    if {$ml ne "NULL"} { set maxl [$ml getRoutingLevel] }
  }
  set minl 4
  if {[info exists ::env(OT_PG_TRACK_TRUTH_MIN_LEVEL)] && $::env(OT_PG_TRACK_TRUTH_MIN_LEVEL) ne ""} {
    set minl $::env(OT_PG_TRACK_TRUTH_MIN_LEVEL)
  }
  array set cnt {}; array set ntr {}; array unset ::ot_pgtt_grid; array unset ::ot_pgtt_seen; set ::ot_pgtt_regions {}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} { continue }
    set st [$net getSigType]
    if {$st ne "POWER" && $st ne "GROUND"} { continue }
    foreach sw [$net getSWires] {
      foreach w [$sw getWires] {
        if {[$w isVia]} { continue }
        set L [$w getTechLayer]
        if {$L eq "NULL" || [$L getType] ne "ROUTING"} { continue }
        set lv [$L getRoutingLevel]
        if {$lv < $minl || $lv > $maxl} { continue }
        set dir [$L getDirection]
        set x0 [$w xMin]; set y0 [$w yMin]; set x1 [$w xMax]; set y1 [$w yMax]
        if {$dir eq "HORIZONTAL"} {
          if {($x1 - $x0) <= ($y1 - $y0)} { continue }
          set lo $y0; set hi $y1; set a0 $x0; set a1 $x1
        } else {
          if {($y1 - $y0) <= ($x1 - $x0)} { continue }
          set lo $x0; set hi $x1; set a0 $y0; set a1 $y1
        }
        set ln [$L getName]
        if {![info exists ::ot_pgtt_grid($ln)]} {
          set tg [$blk findTrackGrid $L]
          if {$tg eq "NULL"} { set ::ot_pgtt_grid($ln) {}; continue }
          if {$dir eq "HORIZONTAL"} { set g [$tg getGridY] } else { set g [$tg getGridX] }
          set ::ot_pgtt_grid($ln) [lsort -integer -unique $g]
        }
        set g $::ot_pgtt_grid($ln)
        if {[llength $g] == 0} { continue }
        set hw [expr {[$L getWidth] / 2}]
        set sp [$L getSpacing]
        # OT_PG_TRACK_TRUTH_WIDE_SPACING=1 (opt-in, not yet proven): also use the width-dependent spacing of the stripe
        # (ASAP7 M4/M5 SPACINGTABLE 0.072 for width > 0.025).  Default = min spacing, the form HEAD-98 routed DRC 0.
        if {[info exists ::env(OT_PG_TRACK_TRUTH_WIDE_SPACING)] && $::env(OT_PG_TRACK_TRUTH_WIDE_SPACING) eq "1"} {
          if {![catch {$L getSpacing [expr {$hi - $lo}] [expr {$a1 - $a0}]} sw_sp] && $sw_sp > $sp} { set sp $sw_sp }
        }
        if {[ot_pgtt_region_mode]} {
          # per-gcell capacity cut over the illegal-track span (whole stripe length); one call per stripe, deduplicated
          lassign [ot_pgtt_illegal_span $lo $hi $hw $sp] s0 s1
          set kmin [expr {[lsearch -sorted -integer -bisect $g [expr {$lo - $hw - $sp}]] + 1}]
          set kmax [lsearch -sorted -integer -bisect $g [expr {$hi + $hw + $sp - 1}]]
          if {$kmax < $kmin || $kmax < 0} { continue }     # no track of this layer is illegal here: nothing to cut
          if {$dir eq "HORIZONTAL"} { set reg [list $a0 $s0 $a1 $s1] } else { set reg [list $s0 $a0 $s1 $a1] }
          if {[info exists ::ot_pgtt_seen($ln,$reg)]} { continue }
          set ::ot_pgtt_seen($ln,$reg) 1
          lappend ::ot_pgtt_regions [list $ln $reg]
          if {![info exists cnt($ln)]} { set cnt($ln) 0; set ntr($ln) 0 }
          incr cnt($ln); incr ntr($ln) [expr {$kmax - $kmin + 1}]
          continue
        }
        # illegal tracks: lo - hw - sp < t < hi + hw + sp
        set kmin [expr {[lsearch -sorted -integer -bisect $g [expr {$lo - $hw - $sp}]] + 1}]
        set kmax [lsearch -sorted -integer -bisect $g [expr {$hi + $hw + $sp - 1}]]
        if {$kmax < $kmin || $kmax < 0} { continue }
        set t0 [expr {[lindex $g $kmin] - $hw}]; set t1 [expr {[lindex $g $kmax] + $hw}]
        if {$dir eq "HORIZONTAL"} {
          set o [odb::dbObstruction_create $blk $L $a0 $t0 $a1 $t1]
        } else {
          set o [odb::dbObstruction_create $blk $L $t0 $a0 $t1 $a1]
        }
        lappend ::ot_pgtt_obs $o
        if {![info exists cnt($ln)]} { set cnt($ln) 0; set ntr($ln) 0 }
        incr cnt($ln); incr ntr($ln) [expr {$kmax - $kmin + 1}]
      }
    }
  }
  if {[ot_pgtt_region_mode]} {
    set dbu [$blk getDbUnitsPerMicron]
    foreach r $::ot_pgtt_regions {
      lassign $r ln reg
      set um [lmap v $reg {expr {double($v) / $dbu}}]
      set_global_routing_region_adjustment $um -layer $ln -adjustment 1.0
    }
    set per {}
    foreach ln [lsort [array names cnt]] { lappend per "$ln=$cnt($ln)/$ntr($ln)" }
    puts "OT_PG_TRACK_TRUTH region [llength $::ot_pgtt_regions] GRT capacity cuts, 100 % per gcell (layer=stripes/tracks) [join $per { }]"
    return
  }
  set per {}
  foreach ln [lsort [array names cnt]] { lappend per "$ln=$cnt($ln)/$ntr($ln)" }
  puts "OT_PG_TRACK_TRUTH add [llength $::ot_pgtt_obs] temporary GRT obstructions (layer=stripes/tracks) [join $per { }]"
}
proc ot_pgtt_remove {} {
  if {![info exists ::ot_pgtt_obs] || ![llength $::ot_pgtt_obs]} { return }
  foreach o $::ot_pgtt_obs { odb::dbObstruction_destroy $o }
  puts "OT_PG_TRACK_TRUTH removed [llength $::ot_pgtt_obs] temporary GRT obstructions before 5_1_grt.odb is written"
  set ::ot_pgtt_obs {}
}
