# HBM-CORES-KITS-41/VMW 11-01 (opt-in gen_core_kit_hbm.py --reg-guide JSON): register-family GPL guides.
# Sourced at PRE_GLOBAL_PLACE (end of face_flops.tcl).  ot_rg_spec = {name regex x0 y0 x1 y1 ...} (um, die coords).
# Every unfixed core instance whose name (ODB bracket escapes stripped) matches regex joins an INCLUSIVE placement
# region on the box (macro_reg_guide.tcl form); reg_guide_release.tcl removes the regions before detailed placement,
# so DPL / repair stay free and the registers stay where GPL put them.
# Fail closed: a guide with no member, or movable+fixed fill >= 0.80, is an error.
uplevel #0 {
if {![info exists ot_rg_spec]} { error "OT_REG_GUIDE: ot_rg_spec not set" }
set rg_blk [ord::get_db_block]
set rg_u [[ord::get_db_tech] getDbUnitsPerMicron]
set rg_names {}
foreach i [$rg_blk getInsts] {
  if {![[$i getMaster] isCore]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED}} continue
  lappend rg_names [string map {"\\" ""} [$i getName]] $i
}
set rg_n 0; set rg_cells 0
foreach {rg_nm rg_re zx0 zy0 zx1 zy1} $ot_rg_spec {
  set rg_insts {}; set rg_area 0.0
  foreach {nm i} $rg_names {
    if {[regexp -- $rg_re $nm]} {
      lappend rg_insts $i
      set rg_area [expr {$rg_area + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight] / $rg_u / $rg_u}]
    }
  }
  if {[llength $rg_insts] == 0} { error "OT_REG_GUIDE $rg_nm: no unfixed instance matches $rg_re" }
  set rg_fixed 0.0
  foreach fi [$rg_blk getInsts] {
    if {[$fi getPlacementStatus] ni {FIRM LOCKED}} continue
    set bb [$fi getBBox]
    set ix0 [expr {max($zx0, double([$bb xMin])/$rg_u)}]; set iy0 [expr {max($zy0, double([$bb yMin])/$rg_u)}]
    set ix1 [expr {min($zx1, double([$bb xMax])/$rg_u)}]; set iy1 [expr {min($zy1, double([$bb yMax])/$rg_u)}]
    if {$ix1 > $ix0 && $iy1 > $iy0} { set rg_fixed [expr {$rg_fixed + ($ix1-$ix0)*($iy1-$iy0)}] }
  }
  set rg_fill [expr {($rg_area + $rg_fixed) / (($zx1-$zx0)*($zy1-$zy0))}]
  if {$rg_fill >= 0.80} { error "OT_REG_GUIDE_CAPACITY $rg_nm: movable+fixed fill $rg_fill >= 0.80" }
  set reg [odb::dbRegion_create $rg_blk "ot_rg_$rg_nm"]
  $reg setRegionType INCLUSIVE
  odb::dbBox_create $reg [expr {round($zx0*$rg_u)}] [expr {round($zy0*$rg_u)}] [expr {round($zx1*$rg_u)}] [expr {round($zy1*$rg_u)}]
  set g [odb::dbGroup_create $reg "ot_rg_$rg_nm"]
  $g setType VOLTAGE_DOMAIN
  foreach i $rg_insts { $g addInst $i }
  puts [format "OT_REG_GUIDE %s cells %d area %.1f um2 box %.2f %.2f %.2f %.2f fixed %.0f fill %.3f" \
        $rg_nm [llength $rg_insts] $rg_area $zx0 $zy0 $zx1 $zy1 $rg_fixed $rg_fill]
  incr rg_n; incr rg_cells [llength $rg_insts]
}
puts "OT_REG_GUIDE $rg_n guides $rg_cells cells (GPL guide, released before DPL)"
}
