# PATH-KV-ASTK2 10-25 (GEOM 10:05 FAIL on kv3_astk W2: every zone placed in 2-3 islands): PRE_GLOBAL_PLACE (after
# face_flops.tcl) one INCLUSIVE placement region per zone, given as explicit boxes by the generated wrapper
# (zone_pre_gpl.tcl sets ot_zone_spec = {name regexp x0 y0 x1 y1 ...} in um, core coordinates).  Every unfixed core
# instance whose name matches a zone regexp joins that zone's group, so GPL keeps the zone contiguous inside its box
# (named registers / kept modules carry the zone; unnamed comb follows by wirelength).  The regions are GPL guides:
# zone_fence_release.tcl removes them before detailed placement (DPL / repair buffers free).
uplevel #0 {
if {![info exists ot_zone_spec]} { error "OT_ZONE_FENCE: ot_zone_spec not set" }
set zf_blk [ord::get_db_block]
set zf_u [[ord::get_db_tech] getDbUnitsPerMicron]
set zf_j 0
foreach {zf_nm zf_re zx0 zy0 zx1 zy1} $ot_zone_spec {
  set zf_insts {}; set zf_area 0.0
  foreach i [$zf_blk getInsts] {
    if {![[$i getMaster] isCore]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED}} continue
    if {![regexp $zf_re [$i getName]]} continue
    lappend zf_insts $i
    set zf_area [expr {$zf_area + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight] / $zf_u / $zf_u}]
  }
  if {[llength $zf_insts] == 0} { error "OT_ZONE_FENCE $zf_nm: no instance matches $zf_re" }
  set nm "ot_zone_fence_$zf_nm"
  set reg [odb::dbRegion_create $zf_blk $nm]
  $reg setRegionType INCLUSIVE
  odb::dbBox_create $reg [expr {round($zx0 * $zf_u)}] [expr {round($zy0 * $zf_u)}] [expr {round($zx1 * $zf_u)}] [expr {round($zy1 * $zf_u)}]
  set g [odb::dbGroup_create $reg $nm]
  $g setType VOLTAGE_DOMAIN
  foreach i $zf_insts { $g addInst $i }
  set box [expr {($zx1 - $zx0) * ($zy1 - $zy0)}]
  puts [format "OT_ZONE_FENCE %s cells %d named area %.0f um2 box %.1f %.1f %.1f %.1f (%.0f um2, named fill %.2f)" $nm [llength $zf_insts] $zf_area $zx0 $zy0 $zx1 $zy1 $box [expr {$zf_area / $box}]]
  incr zf_j
}
puts "OT_ZONE_FENCE $zf_j zone regions (GPL guide, released before DPL)"
}
