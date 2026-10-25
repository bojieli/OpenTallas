# S81-CORES2/SW macro interface-register placement (PRE_GLOBAL_PLACE, after face_flops.tcl; COORD F6, GEOM 04:38-04:45).
# Every SRAM (master type BLOCK) interface register -- the flop that drives a macro data/address/control input through
# <= 2 buffer/inverter cells, and every flop whose D a macro output drives directly (<= 1 buffer) -- is placed FIRM in a
# band just outside the macro halo on the macro edge that carries that pin, at the row (E/W edge) or column (N/S edge)
# nearest the pin.  GPL then builds the logic around registers that already sit at the macro (no 68-122 um interface
# wires, so the macro clock pin and its registers can share one skew-group tap).  Flops that are already FIRM (partition
# pin registers at their face, face_flops.tcl) keep their place: a pin register that is also a macro interface register is
# a planned reg -> macro wire.  The names are appended to ot_face_flops.txt so face_flops_release.tcl (PRE_DETAIL_PLACE)
# releases them to PLACED for DPL.
# Env: OT_MIF_HALO_UM (gap macro edge -> first column, default 4.32), OT_MIF_MAX_COLS (band depth in flop columns, 16)
uplevel #0 {
set mif_blk [ord::get_db_block]
set mif_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set mif_core [$mif_blk getCoreArea]
set mif_x0 [$mif_core xMin]; set mif_y0 [$mif_core yMin]; set mif_x1 [$mif_core xMax]; set mif_y1 [$mif_core yMax]
set mif_rows [$mif_blk getRows]
set mif_site [[lindex $mif_rows 0] getSite]
set mif_sw [$mif_site getWidth]; set mif_rh [$mif_site getHeight]
set mif_cp [expr {$mif_sw * 40}]
set mif_orient {}
foreach r $mif_rows { dict set mif_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set mif_halo [expr {round(([info exists ::env(OT_MIF_HALO_UM)] ? $::env(OT_MIF_HALO_UM) : 4.32) * $mif_dbu)}]
set mif_maxc [expr {[info exists ::env(OT_MIF_MAX_COLS)] ? $::env(OT_MIF_MAX_COLS) : 16}]
proc mif_is_ff {i} { return [string match "*DFF*" [[$i getMaster] getName]] }
proc mif_is_buf {i} { set m [[$i getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
proc mif_drv_ff {net depth} {
  if {$net eq "NULL" || $net eq ""} { return "" }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
    set i [$it getInst]
    if {[mif_is_ff $i]} { return $i }
    if {$depth < 2 && [mif_is_buf $i]} {
      foreach t [$i getITerms] {
        if {[$t getSigType] ne "SIGNAL" || [[$t getMTerm] getIoType] ne "INPUT"} continue
        set f [mif_drv_ff [$t getNet] [expr {$depth + 1}]]; if {$f ne ""} { return $f }
      }
    }
  }
  return ""
}
proc mif_load_ffs {net depth} {
  set r {}
  if {$net eq "NULL" || $net eq ""} { return $r }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set i [$it getInst]
    if {[mif_is_ff $i]} { if {[[$it getMTerm] getName] eq "D"} { lappend r $i } ; continue }
    if {$depth < 1 && [mif_is_buf $i]} {
      foreach t [$i getITerms] {
        if {[$t getSigType] ne "SIGNAL" || [[$t getMTerm] getIoType] ne "OUTPUT"} continue
        set r [concat $r [mif_load_ffs [$t getNet] [expr {$depth + 1}]]]
      }
    }
  }
  return $r
}
# occupancy on the face_flops column grid (col = cp pitch, row = row height): every FIRM std cell and every macro + halo
set mif_occ {}
proc mif_key {x y} { global mif_x0 mif_y0 mif_cp mif_rh; return "[expr {($x - $mif_x0) / $mif_cp}],[expr {($y - $mif_y0) / $mif_rh}]" }
set mif_macros {}
foreach i [$mif_blk getInsts] {
  if {[[$i getMaster] getType] eq "BLOCK"} { lappend mif_macros $i; continue }
  if {[$i getPlacementStatus] eq "FIRM"} { lassign [$i getLocation] x y; dict set mif_occ [mif_key $x $y] 1 }
}
proc mif_free {x y w} {
  # site (x, y) free: inside the core, outside every macro + halo, grid cell not taken
  global mif_x0 mif_y0 mif_x1 mif_y1 mif_macros mif_halo mif_rh mif_occ
  if {$x < $mif_x0 || $y < $mif_y0 || $x + $w > $mif_x1 || $y + $mif_rh > $mif_y1} { return 0 }
  if {[dict exists $mif_occ [mif_key $x $y]]} { return 0 }
  foreach m $mif_macros {
    set b [$m getBBox]
    if {$x + $w > [$b xMin] - $mif_halo && $x < [$b xMax] + $mif_halo && $y + $mif_rh > [$b yMin] - $mif_halo && $y < [$b yMax] + $mif_halo} { return 0 }
  }
  return 1
}
set mif_done {}
set mif_n 0; set mif_skip_firm 0; set mif_miss 0
set mif_dist {}
set mif_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach m $mif_macros {
  set mb [$m getBBox]
  set mx0 [$mb xMin]; set my0 [$mb yMin]; set mx1 [$mb xMax]; set my1 [$mb yMax]
  set mn 0
  foreach it [$m getITerms] {
    if {[$it getSigType] ne "SIGNAL"} continue
    set net [$it getNet]
    if {$net eq "NULL" || [$net getSigType] eq "CLOCK"} continue
    set io [[$it getMTerm] getIoType]
    set ffs [expr {$io eq "INPUT" ? [list [mif_drv_ff $net 0]] : [mif_load_ffs $net 0]}]
    set pb [$it getBBox]
    set px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2}]
    set d [list [list [expr {$px - $mx0}] W] [list [expr {$mx1 - $px}] E] [list [expr {$py - $my0}] S] [list [expr {$my1 - $py}] N]]
    set edge [lindex [lsort -integer -index 0 $d] 0 1]
    foreach f $ffs {
      if {$f eq ""} continue
      if {[dict exists $mif_done [$f getName]]} continue
      dict set mif_done [$f getName] 1
      if {[$f getPlacementStatus] eq "FIRM"} { incr mif_skip_firm; continue }
      set w [[$f getMaster] getWidth]
      set placed 0
      if {$edge in {E W}} {
        set r0 [expr {($py - $mif_y0) / $mif_rh}]
        for {set c 0} {$c < $mif_maxc && !$placed} {incr c} {
          foreach dr {0 1 -1 2 -2 3 -3 4 -4} {
            set cy [expr {$mif_y0 + ($r0 + $dr) * $mif_rh}]
            set cx [expr {$edge eq "W" ? $mx0 - $mif_halo - ($c + 1) * $mif_cp : $mx1 + $mif_halo + $c * $mif_cp}]
            set cx [expr {$mif_x0 + (($cx - $mif_x0) / $mif_cp) * $mif_cp}]
            if {[mif_free $cx $cy $w]} { set placed 1; break }
          }
        }
      } else {
        set c0 [expr {($px - $mif_x0) / $mif_cp}]
        for {set r 0} {$r < 4 * $mif_maxc && !$placed} {incr r} {
          foreach dc {0 1 -1 2 -2} {
            set cx [expr {$mif_x0 + ($c0 + $dc) * $mif_cp}]
            set cy [expr {$edge eq "S" ? $my0 - $mif_halo - ($r + 1) * $mif_rh : $my1 + $mif_halo + $r * $mif_rh}]
            set cy [expr {$mif_y0 + (($cy - $mif_y0) / $mif_rh) * $mif_rh}]
            if {[mif_free $cx $cy $w]} { set placed 1; break }
          }
        }
      }
      if {!$placed} { incr mif_miss; continue }
      dict set mif_occ [mif_key $cx $cy] 1
      if {[dict exists $mif_orient $cy]} { $f setOrient [dict get $mif_orient $cy] }
      $f setLocation $cx $cy
      $f setPlacementStatus FIRM
      lappend mif_dist [expr {(abs($cx - $px) + abs($cy - $py)) / double($mif_dbu)}]
      puts $mif_out "[$f getName]\tMIF$edge\t[expr {$cx / double($mif_dbu)}]\t[expr {$cy / double($mif_dbu)}]\t[$m getName]/[[$it getMTerm] getName]"
      incr mif_n; incr mn
    }
  }
  puts "OT_MACRO_IF [$m getName]: $mn interface registers FIRM beside their pin edge"
}
close $mif_out
set mif_dist [lsort -real $mif_dist]
set nd [llength $mif_dist]
if {$nd} {
  puts "OT_MACRO_IF placed $mif_n registers (pin->reg um p50 [format %.1f [lindex $mif_dist [expr {$nd/2}]]] p90 [format %.1f [lindex $mif_dist [expr {int($nd*0.9)}]]] max [format %.1f [lindex $mif_dist end]]); $mif_skip_firm already FIRM (pin registers), $mif_miss without a free site"
} else { puts "OT_MACRO_IF placed 0 registers; $mif_skip_firm already FIRM, $mif_miss missing" }
}
