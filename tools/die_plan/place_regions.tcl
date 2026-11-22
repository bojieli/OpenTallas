# place_regions.tcl -- "region before cycle" (FABLE-CLOSURE-STRATEGY lever 5; FABLE-FIX-S81-GLUE 2026-11-19).
# GENERATED-KIT HOOK (gen_phys copies it; sourced at the end of face_flops.tcl, PRE_GLOBAL_PLACE, when the kit has
# place_regions_data.tcl): the standard cells of a named logic cone go into one placement region (odb dbRegion + dbGroup,
# which global and detailed placement honour) sized for a target utilisation, so a sparse partition cannot scatter the cone.
# Why: QC tt_ctlm u_core (10 % utilised 778 x 518 um partition): worst path flops 57 um apart, path 835 um through 22 gates
# placed across the partition, TT -267 ps; with the region 99.2 % of the 200,217 movable cone cells sit inside it.
# Data (plan key partition_types.<type>.place_regions, written by gen_phys as place_regions_data.tcl):
#   set ::ot_place_regions { {name inst_re util cx cy near_re} ... }
#   inst_re  regex on the instance name (bus-bit escapes removed); movable standard cells only (FIRM / LOCKED cells, i.e. pin
#            registers, rings, stations, and macros are never grouped)
#   util     target utilisation of the region (cell area / region area)
#   cx cy    centre in um, or {} {} with near_re: the centre is then the centroid of the instances matching near_re (the cone's
#            macros and / or its FIRM pin registers); with neither the centre is the centroid of the cone's own macros matching
#            inst_re, else the core centre
# The region is a square clipped to the core (it grows along the free axis to keep its area) and grown until its area that is
# not under a macro holds the cells at the target utilisation.  A region without cells is an
# error (a plan key that matches nothing must not pass silently).  One line per region: OT_PLACE_REGION ...
uplevel #0 {
if {[info exists ::ot_place_regions]} {
set pr_blk [ord::get_db_block]
set pr_dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
set pr_core [$pr_blk getCoreArea]
set pr_cx0 [expr {[$pr_core xMin]/$pr_dbu}]; set pr_cy0 [expr {[$pr_core yMin]/$pr_dbu}]
set pr_cx1 [expr {[$pr_core xMax]/$pr_dbu}]; set pr_cy1 [expr {[$pr_core yMax]/$pr_dbu}]
set pr_site [[lindex [$pr_blk getRows] 0] getSite]; set pr_sw [$pr_site getWidth]; set pr_rh [$pr_site getHeight]
set pr_insts {}
foreach i [$pr_blk getInsts] { lappend pr_insts [list [string map {\\ {}} [$i getName]] $i] }
set pr_macros {}
foreach pr_p $pr_insts { set i [lindex $pr_p 1]; if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend pr_macros [list [expr {[$b xMin]/$pr_dbu-2.0}] [expr {[$b yMin]/$pr_dbu-2.0}] [expr {[$b xMax]/$pr_dbu+2.0}] [expr {[$b yMax]/$pr_dbu+2.0}]] } }
foreach pr_row $::ot_place_regions {
  lassign $pr_row pr_name pr_re pr_util pr_x pr_y pr_near pr_kind pr_box pr_rad
  if {$pr_kind eq ""} { set pr_kind fence }
  set pr_grp {}; set pr_a 0.0; set pr_sx 0.0; set pr_sy 0.0; set pr_k 0; set pr_mx 0.0; set pr_my 0.0; set pr_mk 0
  foreach pr_p $pr_insts {
    lassign $pr_p pr_n pr_i
    set pr_m [$pr_i getMaster]
    if {$pr_near ne "" && [regexp -- $pr_near $pr_n]} {
      set pr_b [$pr_i getBBox]; set pr_sx [expr {$pr_sx + ([$pr_b xMin]+[$pr_b xMax])/2.0/$pr_dbu}]; set pr_sy [expr {$pr_sy + ([$pr_b yMin]+[$pr_b yMax])/2.0/$pr_dbu}]; incr pr_k
    }
    if {![regexp -- $pr_re $pr_n]} continue
    if {[$pr_m isBlock]} {
      set pr_b [$pr_i getBBox]; set pr_mx [expr {$pr_mx + ([$pr_b xMin]+[$pr_b xMax])/2.0/$pr_dbu}]; set pr_my [expr {$pr_my + ([$pr_b yMin]+[$pr_b yMax])/2.0/$pr_dbu}]; incr pr_mk
      continue
    }
    if {[$pr_i getPlacementStatus] in {FIRM LOCKED COVER}} continue
    lappend pr_grp $pr_i
    set pr_a [expr {$pr_a + [$pr_m getWidth]*[$pr_m getHeight]/$pr_dbu/$pr_dbu}]
  }
  if {![llength $pr_grp]} { error "OT_PLACE_REGION $pr_name: inst_re '$pr_re' matches no movable standard cell" }
  # FLOW-NOADV-R3 11-20 (FABLE-PD-S81-1840): members must cover at least half of the cells of their logic cone.  S81 serdes_tx_encoder: 5,926 member
  # flops against 5,975 gates of the same cone outside the group = DPL-0033 on every J5 serdes.  Under half: the cone's combinational cells join the group
  # (OT_PLACE_REGION_EXTEND); a cone more than 8 x the members is not separable: that region is dropped (OT_PLACE_REGION_DROP).
  if {[file exists /work/place_regions_cone.tcl]} {
    source /work/place_regions_cone.tcl
    if {![llength [info procs ot_pr_nbrs_in]]} {
      proc ot_pr_nbrs_in {i} { set o {}; foreach it [$i getITerms] { if {![$it isInputSignal]} continue; set n [$it getNet]; if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [llength [$n getITerms]] > 256} continue; foreach t [$n getITerms] { if {[$t isOutputSignal]} { lappend o [$t getInst] } } }; return $o }
      proc ot_pr_nbrs_out {i} { set o {}; foreach it [$i getITerms] { if {![$it isOutputSignal]} continue; set n [$it getNet]; if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [llength [$n getITerms]] > 256} continue; foreach t [$n getITerms] { if {[$t isInputSignal]} { lappend o [$t getInst] } } }; return $o }
      proc ot_pr_is_cand {i} {
        global ot_pr_taken
        if {[info exists ot_pr_taken($i)]} { return 0 }
        set m [$i getMaster]
        if {[$m isBlock] || [$m isSequential] || [$i getPlacementStatus] in {FIRM LOCKED COVER}} { return 0 }
        return 1
      }
    }
    foreach pr_t $pr_grp { set ot_pr_taken($pr_t) 1 }
    # S81-DIE-R5 11-20 (COORD; J6 C1d/C2d drop the serdes regions, FABLE-PD-S81-2340): a cone that is not separable (> 8 x the members)
    # gets NO region, loudly: its members place with the design (no group, no box).  The refusal stopped every J5 serdes at global place
    # (serdes_tx_encoder: > 47,400 cone cells for 5,925 members); the region-less form passed DPL on serdes t4 and is what J6 builds.
    if {[catch {ot_pr_cone $pr_grp ot_pr_nbrs_in ot_pr_nbrs_out ot_pr_is_cand 8} pr_extra]} {
      if {![string match "cone has more than*" $pr_extra]} { error $pr_extra $::errorInfo }
      foreach pr_t $pr_grp { unset -nocomplain ot_pr_taken($pr_t) }
      puts "OT_PLACE_REGION_DROP $pr_name: $pr_extra ([llength $pr_grp] members): no region for this cone, its cells place with the design"
      continue
    }
    set pr_cov [ot_pr_coverage [llength $pr_grp] [llength $pr_extra]]
    if {$pr_cov < 0.5} {
      foreach pr_e $pr_extra {
        lappend pr_grp $pr_e; set ot_pr_taken($pr_e) 1
        set pr_em [$pr_e getMaster]; set pr_a [expr {$pr_a + [$pr_em getWidth]*[$pr_em getHeight]/$pr_dbu/$pr_dbu}]
      }
      puts [format "OT_PLACE_REGION_EXTEND %s: members cover %.3f of the cone (%d members, %d cone cells) < 0.5: the cone's combinational cells joined the group (%d cells)" $pr_name $pr_cov [expr {[llength $pr_grp]-[llength $pr_extra]}] [llength $pr_extra] [llength $pr_grp]]
    } else {
      puts [format "OT_PLACE_REGION_COVERAGE %s: members cover %.3f of the cone (%d members, %d cone cells outside the region group)" $pr_name $pr_cov [llength $pr_grp] [llength $pr_extra]]
    }
  }
  if {$pr_box ne ""} { lassign $pr_box pr_b0 pr_b1 pr_b2 pr_b3; set pr_x [expr {($pr_b0+$pr_b2)/2.0}]; set pr_y [expr {($pr_b1+$pr_b3)/2.0}]; set pr_how "plan box"
  } elseif {$pr_x ne "" && $pr_y ne ""} { set pr_how plan
  } elseif {$pr_near ne ""} {
    if {!$pr_k} { error "OT_PLACE_REGION $pr_name: near_re '$pr_near' matches no instance" }
    set pr_x [expr {$pr_sx/$pr_k}]; set pr_y [expr {$pr_sy/$pr_k}]; set pr_how "near ($pr_k instances)"
  } elseif {$pr_mk} { set pr_x [expr {$pr_mx/$pr_mk}]; set pr_y [expr {$pr_my/$pr_mk}]; set pr_how "cone macros ($pr_mk)"
  } else { set pr_x [expr {($pr_cx0+$pr_cx1)/2.0}]; set pr_y [expr {($pr_cy0+$pr_cy1)/2.0}]; set pr_how "core centre" }
  # the box grows (5 % of its area per step) until its area NOT under a macro (bbox + 2 um) holds the cells at the target
  set pr_need [expr {$pr_a/$pr_util}]; set pr_area $pr_need; set pr_ar 1.0
  # PLACE-GROUP (FABLE-FIX-CONE-SCATTER 11-22): box_um keeps its aspect and starts at its own area, radius_um starts at (2r)^2; both grow
  # (same 5 % steps) only when the cells at the target utilisation do not fit
  if {$pr_box ne ""} { set pr_ar [expr {($pr_b3-$pr_b1)/double($pr_b2-$pr_b0)}]; set pr_area [expr {max($pr_need, ($pr_b2-$pr_b0)*($pr_b3-$pr_b1))}]
  } elseif {$pr_rad ne ""} { set pr_area [expr {max($pr_need, 4.0*$pr_rad*$pr_rad)}] }
  for {set pr_it 0} {$pr_it < 400} {incr pr_it} {
    set pr_w [expr {sqrt($pr_area/$pr_ar)}]; set pr_h [expr {$pr_w*$pr_ar}]
    if {$pr_w > $pr_cx1-$pr_cx0} { set pr_w [expr {$pr_cx1-$pr_cx0}]; set pr_h [expr {$pr_area/$pr_w}] }
    if {$pr_h > $pr_cy1-$pr_cy0} { set pr_h [expr {$pr_cy1-$pr_cy0}]; set pr_w [expr {min($pr_area/$pr_h, $pr_cx1-$pr_cx0)}] }
    set pr_x0 [expr {max($pr_cx0, min($pr_x-$pr_w/2.0, $pr_cx1-$pr_w))}]; set pr_y0 [expr {max($pr_cy0, min($pr_y-$pr_h/2.0, $pr_cy1-$pr_h))}]
    set pr_blk_a 0.0
    foreach pr_mb $pr_macros {
      lassign $pr_mb a0 b0 a1 b1
      set ox [expr {min($a1, $pr_x0+$pr_w) - max($a0, $pr_x0)}]; set oy [expr {min($b1, $pr_y0+$pr_h) - max($b0, $pr_y0)}]
      if {$ox > 0 && $oy > 0} { set pr_blk_a [expr {$pr_blk_a + $ox*$oy}] }
    }
    set pr_free [expr {$pr_w*$pr_h - $pr_blk_a}]
    if {$pr_free >= $pr_need || ($pr_w >= $pr_cx1-$pr_cx0 && $pr_h >= $pr_cy1-$pr_cy0)} break
    set pr_area [expr {$pr_area*1.05}]
  }
  if {$pr_free < $pr_need} { error "OT_PLACE_REGION $pr_name: the core has $pr_free um2 free of macros, the region needs $pr_need" }
  set pr_r [odb::dbRegion_create $pr_blk ot_region_$pr_name]
  # SNAP (11-19, DPL-0033 on QC glue kit H and S81 leaf t27fence): the box goes OUTWARD onto the placement grid (site
  # width in x, row height in y, from the core origin).  An off-grid edge lets the legaliser put a member in the last
  # site column / row with its edge a fraction of a site outside the box, and check_placement fails the region check
  # (kit H: 41 straddling members = "Region placement check failed (41)", none outside, utilisation unchanged).
  set pr_bx0 [expr {[$pr_core xMin] + ((int($pr_x0*$pr_dbu) - [$pr_core xMin]) / $pr_sw) * $pr_sw}]
  set pr_by0 [expr {[$pr_core yMin] + ((int($pr_y0*$pr_dbu) - [$pr_core yMin]) / $pr_rh) * $pr_rh}]
  set pr_bx1 [expr {min([$pr_core xMax], [$pr_core xMin] + ((int(($pr_x0+$pr_w)*$pr_dbu) - [$pr_core xMin] + $pr_sw - 1) / $pr_sw) * $pr_sw)}]
  set pr_by1 [expr {min([$pr_core yMax], [$pr_core yMin] + ((int(($pr_y0+$pr_h)*$pr_dbu) - [$pr_core yMin] + $pr_rh - 1) / $pr_rh) * $pr_rh)}]
  odb::dbBox_create $pr_r $pr_bx0 $pr_by0 $pr_bx1 $pr_by1
  set pr_g [odb::dbGroup_create $pr_r ot_region_${pr_name}_grp]
  $pr_g setType PHYSICAL_CLUSTER
  foreach pr_i $pr_grp { $pr_g addInst $pr_i }
  puts [format "OT_PLACE_REGION %s (%s): %d cells %.0f um2 util %.2f of the macro-free area, box (%.3f %.3f)-(%.3f %.3f) um on the site / row grid, centre %s" $pr_name $pr_kind [llength $pr_grp] $pr_a [expr {$pr_a/$pr_free}] [expr {$pr_bx0/$pr_dbu}] [expr {$pr_by0/$pr_dbu}] [expr {$pr_bx1/$pr_dbu}] [expr {$pr_by1/$pr_dbu}] $pr_how]
}
}
}
