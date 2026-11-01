# DIE-HEAD-53 ftpin (GEOM-98 11-01, opt-in OT_ORIGIN_AT_PIN=2; gen_phys appends it to face_flops_release.tcl, i.e.
# PRE_DETAIL_PLACE after GPL, only when OT_ORIGIN_AT_PIN=2 at generation).  The landing origin start strobe
# cland_tstart_in is an interior M7 pin: the face pass snaps its negedge capture sf to the nearest core edge and GPL
# leaves the first synchroniser s0 at its fan-out centroid, while AUTO-GEOM judges the pin at the FARTHEST of the
# proved writer group sf+s0 (origin_start).  sf moves to the pin.  s0 also has a far D-cone source (its reset relay),
# so s0 goes on the pin -> farthest-source line at d = clamp((dist - 405 + 150) / 2, 0, 150) um: the middle of the
# window that keeps pin_reg <= 150 um and that r2r hop <= 405 um (hd_mesh_e: pin 288,34 -> u_cland_rst_m_tx_ft_i
# 822,22, dist 546 -> d 145.5).  Both stay PLACED; DPL legalises them next.  Mode 1 (face_flops.tcl) = both at the pin.
if {[info exists ::env(OT_ORIGIN_AT_PIN)] && $::env(OT_ORIGIN_AT_PIN) eq "2"} {
  set og_blk [ord::get_db_block]
  set og_bt [$og_blk findBTerm cland_tstart_in]
  if {$og_bt ne "NULL" && $og_bt ne ""} {
    set og_core [$og_blk getCoreArea]
    set og_row [lindex [$og_blk getRows] 0]
    set og_sw [[$og_row getSite] getWidth]; set og_rh [[$og_row getSite] getHeight]
    set og_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
    set bb [$og_bt getBBox]
    set og_px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set og_py [expr {([$bb yMin] + [$bb yMax]) / 2}]
    set og_sf ""; set og_s0 ""
    foreach i [$og_blk getInsts] {
      if {[regexp {(^|[./])u_cland_origin/(sf|s0)\$} [$i getName] -> _ k]} { set og_$k $i }
    }
    proc og_move {i x y} {
      upvar og_core c og_sw sw og_rh rh
      set w [[$i getMaster] getWidth]
      set x [expr {max([$c xMin], min([$c xMax] - $w, round($x)))}]; set y [expr {max([$c yMin], min([$c yMax] - $rh, round($y)))}]
      set x [expr {[$c xMin] + (($x - [$c xMin]) / $sw) * $sw}]; set y [expr {[$c yMin] + (($y - [$c yMin]) / $rh) * $rh}]
      if {[$i getPlacementStatus] in {FIRM LOCKED}} { $i setPlacementStatus PLACED }
      $i setLocation $x $y
      $i setPlacementStatus PLACED
    }
    set og_dd 0.0; set og_far ""; set og_fd -1
    if {$og_sf ne ""} { og_move $og_sf $og_px $og_py }
    if {$og_s0 ne ""} {
      set nets {}
      foreach it [$og_s0 getITerms] { if {[[$it getMTerm] getName] eq "D"} { lappend nets [$it getNet] } }
      set seen {}; set depth 0
      while {[llength $nets] && $depth < 8} {
        set nxt {}
        foreach net $nets {
          if {$net eq "NULL" || $net eq "" || [dict exists $seen $net]} continue
          dict set seen $net 1
          foreach it [$net getITerms] {
            if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
            set i [$it getInst]
            if {[string match "*DFF*" [[$i getMaster] getName]]} {
              if {$i eq $og_sf || $i eq $og_s0} continue
              set b [$i getBBox]
              set d [expr {abs(([$b xMin] + [$b xMax]) / 2.0 - $og_px) + abs(([$b yMin] + [$b yMax]) / 2.0 - $og_py)}]
              if {$d > $og_fd} { set og_fd $d; set og_far $i }
              continue
            }
            foreach ii [$i getITerms] {
              set m2 [$ii getMTerm]
              if {[$m2 getIoType] eq "INPUT" && [$m2 getSigType] ni {CLOCK POWER GROUND}} { lappend nxt [$ii getNet] }
            }
          }
        }
        set nets $nxt; incr depth
      }
      set tx $og_px; set ty $og_py
      if {$og_far ne "" && $og_fd > 0} {
        set b [$og_far getBBox]
        set rx [expr {([$b xMin] + [$b xMax]) / 2.0}]; set ry [expr {([$b yMin] + [$b yMax]) / 2.0}]
        set og_dd [expr {max(0.0, min(150.0 * $og_dbu, ($og_fd - 405.0 * $og_dbu + 150.0 * $og_dbu) / 2.0))}]
        set tx [expr {$og_px + ($rx - $og_px) * $og_dd / $og_fd}]; set ty [expr {$og_py + ($ry - $og_py) * $og_dd / $og_fd}]
      }
      og_move $og_s0 $tx $ty
    }
    puts "OT_ORIGIN_PIN sf at cland_tstart_in; s0 [expr {$og_dd / $og_dbu}] um toward [expr {$og_far eq "" ? "-" : [$og_far getName]}] ([expr {$og_fd / double($og_dbu)}] um)"
  }
}
