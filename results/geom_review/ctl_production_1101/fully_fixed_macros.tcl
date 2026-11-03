# GENERATED: explicit fully fixed macro contract; no global tool or halo change.
set ::ot_fixed_macro_expected {}
set ::ot_fixed_macro_core_um {4.32 4.32 367.2 367.2}
dict set ::ot_fixed_macro_expected {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b0} {ctl_sram_1r1w_64x128_p192 103.68 60.48 52.296 39.96 R0}
dict set ::ot_fixed_macro_expected {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b1} {ctl_sram_1r1w_64x128_p192 216.0 60.48 52.296 39.96 R0}
dict set ::ot_fixed_macro_expected {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b0} {ctl_sram_1r1w_64x128_p192 103.68 155.52 52.296 39.96 R0}
dict set ::ot_fixed_macro_expected {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b1} {ctl_sram_1r1w_64x128_p192 216.0 155.52 52.296 39.96 R0}
dict set ::ot_fixed_macro_expected {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b0} {ctl_sram_1r1w_64x128_p192 103.68 250.56 52.296 39.96 R0}
dict set ::ot_fixed_macro_expected {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b1} {ctl_sram_1r1w_64x128_p192 216.0 250.56 52.296 39.96 R0}

proc ot_fixed_macro_validate {} {
  set b [ord::get_db_block]
  set dbu [$b getDbUnitsPerMicron]
  set actual {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] isBlock]} {dict set actual [$i getName] $i}
  }
  if {[lsort [dict keys $actual]] ne [lsort [dict keys $::ot_fixed_macro_expected]]} {
    error "OT_FIXED_MACROS actual block inventory differs from the complete parent plan"
  }
  set core [$b getCoreArea]
  set core_box [list [$core xMin] [$core yMin] [$core xMax] [$core yMax]]
  set wanted_core [lmap x $::ot_fixed_macro_core_um {expr {round($x*$dbu)}}]
  if {$core_box ne $wanted_core} {error "OT_FIXED_MACROS core differs from the parent plan"}
  set boxes {}
  dict for {name spec} $::ot_fixed_macro_expected {
    lassign $spec master x y w h orient
    set i [dict get $actual $name];set m [$i getMaster]
    if {[$m getName] ne $master || [$i getPlacementStatus] ne "LOCKED"} {
      error "OT_FIXED_MACROS $name requires the exact planned master and LOCKED status"
    }
    if {[$m getWidth] != round($w*$dbu) || [$m getHeight] != round($h*$dbu) || [$i getOrient] ne $orient} {
      error "OT_FIXED_MACROS $name master dimensions/orientation differ from the parent plan"
    }
    set bb [$i getBBox]
    set box [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set wanted [list [expr {round($x*$dbu)}] [expr {round($y*$dbu)}] [expr {round(($x+$w)*$dbu)}] [expr {round(($y+$h)*$dbu)}]]
    if {$box ne $wanted} {error "OT_FIXED_MACROS $name moved from its exact parent-plan rectangle"}
    lassign $box ax ay bx by
    lassign $core_box cx cy dx dy
    if {$ax<$cx || $ay<$cy || $bx>$dx || $by>$dy} {error "OT_FIXED_MACROS $name lies outside the core"}
    dict for {other other_box} $boxes {
      lassign $other_box ox oy px py
      if {min($bx,$px)>max($ax,$ox) && min($by,$py)>max($ay,$oy)} {
        error "OT_FIXED_MACROS $name overlaps $other"
      }
    }
    dict set boxes $name $box
  }
  puts "OT_FIXED_MACROS PASS [dict size $actual] exact LOCKED parent-plan macros; optimization unnecessary"
}
if {[llength [info commands ::ot_fixed_macro_original]] || ![llength [info commands ::rtl_macro_placer]]} {
  error "OT_FIXED_MACROS requires one native macro placer before installing the scoped hook"
}
rename ::rtl_macro_placer ::ot_fixed_macro_original
proc ::rtl_macro_placer {args} {ot_fixed_macro_validate}
