# DIE-HEAD-53 ftpin (GEOM-98 11-01, opt-in OT_ORIGIN_AT_PIN=2; gen_phys appends it after the landing placement only
# when OT_ORIGIN_AT_PIN is set at generation).  The landing origin start strobe cland_tstart_in is an interior M7 pin:
# the face pass snaps its negedge capture sf to the nearest core edge and GPL leaves the first synchroniser s0 at its
# fan-out centroid, while AUTO-GEOM judges the pin at the FARTHEST of the proved writer group sf+s0 (origin_start).
# sf goes FIRM at the pin.  s0 also has a D-cone source placed far away (its reset relay, placed with the rings just
# above), so s0 goes on the pin -> farthest-source line at d = clamp((dist - 405 + 150) / 2, 0, 150) um: the middle of
# the window that keeps pin_reg <= 150 and that r2r hop <= 405 (hd_mesh_e: pin 288,34 -> u_cland_rst_m_tx_ft_i
# 822,22, dist 546 -> d 145.5).  Mode 1 (face_flops.tcl station pass) puts both at the pin.
if {[info exists ::env(OT_ORIGIN_AT_PIN)] && $::env(OT_ORIGIN_AT_PIN) eq "2"} {
  set og_bt [$ff_blk findBTerm cland_tstart_in]
  if {$og_bt ne "NULL" && $og_bt ne ""} {
    set bb [$og_bt getBBox]
    set og_px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set og_py [expr {([$bb yMin] + [$bb yMax]) / 2}]
    set og_sf ""; set og_s0 ""
    foreach i [$ff_blk getInsts] {
      if {[regexp {(^|[./])u_cland_origin/(sf|s0)\$} [$i getName] -> _ k]} { set og_$k $i }
    }
    set og_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
    set og_n 0
    if {$og_sf ne ""} {
      set got [ff_put_near $og_sf $og_px $og_py]
      if {$got ne ""} { puts $og_fh "[$og_sf getName]\torigin\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\tcland_tstart_in"; incr og_n }
    }
    if {$og_s0 ne ""} {
      # placed flops in s0's D cone (<= 8 levels), other than sf / s0
      set nets {}
      foreach it [$og_s0 getITerms] { if {[[$it getMTerm] getName] eq "D"} { lappend nets [$it getNet] } }
      set seen {}; set far ""; set fd -1; set depth 0
      while {[llength $nets] && $depth < 8} {
        set nxt {}
        foreach net $nets {
          if {$net eq "NULL" || $net eq "" || [dict exists $seen $net]} continue
          dict set seen $net 1
          foreach it [$net getITerms] {
            if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
            set i [$it getInst]
            if {[ff_is_ff $i]} {
              if {$i eq $og_sf || $i eq $og_s0 || [$i getPlacementStatus] ni {PLACED FIRM LOCKED FIXED}} continue
              set b [$i getBBox]
              set d [expr {abs(([$b xMin] + [$b xMax]) / 2.0 - $og_px) + abs(([$b yMin] + [$b yMax]) / 2.0 - $og_py)}]
              if {$d > $fd} { set fd $d; set far $i }
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
      set tx $og_px; set ty $og_py; set dd 0.0
      if {$far ne ""} {
        set b [$far getBBox]
        set rx [expr {([$b xMin] + [$b xMax]) / 2.0}]; set ry [expr {([$b yMin] + [$b yMax]) / 2.0}]
        set dd [expr {max(0.0, min(150.0 * $ff_dbu, ($fd - 405.0 * $ff_dbu + 150.0 * $ff_dbu) / 2.0))}]
        set tx [expr {round($og_px + ($rx - $og_px) * $dd / $fd)}]; set ty [expr {round($og_py + ($ry - $og_py) * $dd / $fd)}]
      }
      set got [ff_put_near $og_s0 $tx $ty]
      if {$got ne ""} { puts $og_fh "[$og_s0 getName]\torigin\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\tcland_tstart_in"; incr og_n }
      puts "OT_ORIGIN_PIN s0 [expr {$dd / $ff_dbu}] um from cland_tstart_in toward [expr {$far eq "" ? "-" : [$far getName]}] ([expr {$fd / $ff_dbu}] um)"
    }
    close $og_fh
    puts "OT_ORIGIN_PIN placed $og_n of sf/s0 at cland_tstart_in"
  }
}
