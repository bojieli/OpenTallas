# HBM-CORES-REBAL-10 (opt-in gen_core_kit_hbm.py --macro-reg-guide SCOPE): per-macro register guides.
# Sourced at PRE_GLOBAL_PLACE (end of face_flops.tcl).  ot_mrg_spec = {name {prefix ...} x0 y0 x1 y1 ...} (um, die coords) is
# written by the generator from the frozen macro placement: one box per static macro <P>.u_m = the macro's placed bbox
# grown by --macro-reg-guide-um on every side (clipped to the core area); its members are the unfixed core instances
# under the sibling scope <P>.<SCOPE>. (e.g. the WCOPY per-column write copy registers g_read[k].g_wcopy.*), i.e. the
# registers whose only fanout is that one macro.  Each box becomes an INCLUSIVE placement region (GPL guide, the
# PATH-KV-ASTK2 zone_fence.tcl form); macro_reg_guide_release.tcl removes them before detailed placement, so DPL /
# repair stay free and the registers stay where GPL put them: beside the macro pins they drive.
# --relay-reg-guide adds boxes of the same form for relay registers (several literal name prefixes per box).
# Fail closed: a box with no member, or movable+fixed fill >= 0.80, is an error.
uplevel #0 {
if {![info exists ot_mrg_spec]} { error "OT_MACRO_REG_GUIDE: ot_mrg_spec not set" }
set mrg_blk [ord::get_db_block]
set mrg_u [[ord::get_db_tech] getDbUnitsPerMicron]
# flat Yosys names: strip the ODB bracket escapes once, then compare literal prefixes
set mrg_names {}
foreach i [$mrg_blk getInsts] {
  if {![[$i getMaster] isCore]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED}} continue
  lappend mrg_names [string map {"\\" ""} [$i getName]] $i
}
set mrg_n 0; set mrg_cells 0
foreach {mrg_nm mrg_pf zx0 zy0 zx1 zy1} $ot_mrg_spec {
  set mrg_insts {}; set mrg_area 0.0
  foreach {nm i} $mrg_names {
    foreach pf $mrg_pf {
      if {[string equal -length [string length $pf] $nm $pf]} {
        lappend mrg_insts $i
        set mrg_area [expr {$mrg_area + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight] / $mrg_u / $mrg_u}]
        break
      }
    }
  }
  if {[llength $mrg_insts] == 0} { error "OT_MACRO_REG_GUIDE $mrg_nm: no unfixed instance under $mrg_pf" }
  set mrg_fixed 0.0
  foreach fi [$mrg_blk getInsts] {
    if {[$fi getPlacementStatus] ni {FIRM LOCKED}} continue
    set bb [$fi getBBox]
    set ix0 [expr {max($zx0, double([$bb xMin])/$mrg_u)}]; set iy0 [expr {max($zy0, double([$bb yMin])/$mrg_u)}]
    set ix1 [expr {min($zx1, double([$bb xMax])/$mrg_u)}]; set iy1 [expr {min($zy1, double([$bb yMax])/$mrg_u)}]
    if {$ix1 > $ix0 && $iy1 > $iy0} { set mrg_fixed [expr {$mrg_fixed + ($ix1-$ix0)*($iy1-$iy0)}] }
  }
  set mrg_box [expr {($zx1-$zx0)*($zy1-$zy0)}]
  set mrg_fill [expr {($mrg_area + $mrg_fixed) / $mrg_box}]
  if {$mrg_fill >= 0.80} { error "OT_MACRO_REG_GUIDE_CAPACITY $mrg_nm: movable+fixed fill $mrg_fill >= 0.80" }
  set reg [odb::dbRegion_create $mrg_blk "ot_mrg_$mrg_nm"]
  $reg setRegionType INCLUSIVE
  odb::dbBox_create $reg [expr {round($zx0*$mrg_u)}] [expr {round($zy0*$mrg_u)}] [expr {round($zx1*$mrg_u)}] [expr {round($zy1*$mrg_u)}]
  set g [odb::dbGroup_create $reg "ot_mrg_$mrg_nm"]
  $g setType VOLTAGE_DOMAIN
  foreach i $mrg_insts { $g addInst $i }
  puts [format "OT_MACRO_REG_GUIDE %s cells %d area %.1f um2 box %.2f %.2f %.2f %.2f fixed %.0f fill %.3f" \
        $mrg_nm [llength $mrg_insts] $mrg_area $zx0 $zy0 $zx1 $zy1 $mrg_fixed $mrg_fill]
  incr mrg_n; incr mrg_cells [llength $mrg_insts]
}
puts "OT_MACRO_REG_GUIDE $mrg_n guides $mrg_cells cells (GPL guide, released before DPL)"
}
