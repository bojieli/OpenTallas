# CHILD POCKET GUARD (cluster parents; spec "boundary_tcl": sourced from every ref_tile stage hook, acts only from
# pre_grt.tcl (add) and post_drt.tcl (remove), a no-op everywhere else).
#
# Why (HH-7 2026-10-19, hv16_dbk_cpl-q1-65c2387ab DRC 1): "Metal Spacing inst:u_dbk.L[0].u_bank net:net4693" on M4 at
# (158.97, 61.20), 72.6 um INSIDE the landing bank (bank wd[76] -> parent wd[76] S-face pin).  The bank abstract closes
# pockets only on its top OBS layer (M5, OT_OBS_CLOSED); its M4 OBS leaves a free band (rel y 2.1..18.5 around x 67.5..78)
# that the parent detailed router used as a shortcut and ended against a 0.1 um OBS strip.  Under the hierarchy layer
# contract the parent owns only the layers ABOVE the child cap over a hard child (M6 here); M2..M4 inside a hard child
# belong to the child.  This guard makes that explicit for the router: one obstruction per hard child per layer in
# OT_CPG_LAYERS (default M2 M3 M4), the child box inset by OT_CPG_INSET_UM (0.5 um) so every face pin stub (0.084 um deep)
# keeps its exterior access.  Added before GRT, removed after DRT: the exported view carries only real metal.
namespace eval ot_cpg {
  proc envd {k d} { expr {[info exists ::env($k)] ? $::env($k) : $d} }
  proc caller {} {
    for {set i [expr {[info frame] - 1}]} {$i > 0} {incr i -1} {
      set f [info frame $i]
      if {[dict exists $f file]} {
        set t [file tail [dict get $f file]]
        if {$t ne "child_pocket_guard.tcl"} { return $t }
      }
    }
    return ""
  }
  proc rects {} {
    set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
    set ins [expr {round([envd OT_CPG_INSET_UM 0.5] * $u)}]
    set out {}
    foreach i [$b getInsts] {
      if {![[$i getMaster] isBlock]} continue
      set r [$i getBBox]
      set x0 [expr {[$r xMin] + $ins}]; set y0 [expr {[$r yMin] + $ins}]
      set x1 [expr {[$r xMax] - $ins}]; set y1 [expr {[$r yMax] - $ins}]
      if {$x1 > $x0 && $y1 > $y0} { lappend out [list $x0 $y0 $x1 $y1] }
    }
    return $out
  }
  proc run {mode} {
    set b [ord::get_db_block]; set t [ord::get_db_tech]
    set rs [rects]
    if {![llength $rs]} { puts "OT_CHILD_POCKET_GUARD: skipped (no hard children)"; return }
    foreach ln [envd OT_CPG_LAYERS {M2 M3 M4}] {
      set l [$t findLayer $ln]
      if {$l eq "NULL"} { error "OT_CHILD_POCKET_GUARD: layer $ln not in the tech" }
      set mine {}
      foreach o [$b getObstructions] {
        set bx [$o getBBox]
        if {[[$bx getTechLayer] getName] ne $ln} continue
        if {[lsearch -exact $rs [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]] >= 0} { lappend mine $o }
      }
      if {$mode eq "add"} {
        if {[llength $mine]} { error "OT_CHILD_POCKET_GUARD: add requested but [llength $mine] guards exist on $ln" }
        foreach r $rs { odb::dbObstruction_create $b $l {*}$r }
        puts "OT_CHILD_POCKET_GUARD: created [llength $rs] on $ln (inset [envd OT_CPG_INSET_UM 0.5] um)"
      } else {
        if {[llength $mine] != [llength $rs]} { error "OT_CHILD_POCKET_GUARD: expected [llength $rs] guards on $ln, found [llength $mine]" }
        foreach o $mine { odb::dbObstruction_destroy $o }
        puts "OT_CHILD_POCKET_GUARD: removed [llength $mine] on $ln"
      }
    }
  }
}
set ot_cpg_stage [ot_cpg::caller]
if {[string match *pre_grt.tcl $ot_cpg_stage]} {
  ot_cpg::run add
} elseif {[string match *post_drt.tcl $ot_cpg_stage]} {
  ot_cpg::run remove
}
