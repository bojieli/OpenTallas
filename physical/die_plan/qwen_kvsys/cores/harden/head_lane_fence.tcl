# GENERATED-COPY of physical/die_plan/qwen_kvsys/cores/harden/head_lane_fence.tcl (gen_core_kit_kv.py --head-lane-taps;
# KV-HEADCLK 2026-10-25, GEOM-REVIEW-4 06:05 / 06:53 verdicts on kv3_head_eighth e4/e6).
# PRE_GLOBAL_PLACE (after face_flops.tcl): one placement REGION per head lane (ot_qkh_lane8 g_d[k] instance group,
# 1525 flops / ~950 um2 each, 16 per even head), so GPL keeps every lane compact.  Without it GPL spread each lane into
# 3-5 islands over 100-170 um of the 216-um core, so no regional clock tap could cover a lane (f25 e6/e0 3_place).
# Layout: lanes sorted by (lane8 instance, g_d index) on a near-square grid over the core, boustrophedon rows from the
# S face (the clock pin / pin-register face) up; each region is the grid cell shrunk to the lane's cell area at
# OT_LANE_FILL (0.65), centred, so the corridors between regions keep the front / stin / stk / ctl logic.  The regions
# are GPL guides only: head_lane_fence_release.tcl removes them before detailed placement (DPL / repair buffers free).
# Env: OT_LANE_RE (regexp, capture 1 = lane key), OT_LANE_FILL (0.65)
uplevel #0 {
set lf_re [expr {[info exists ::env(OT_LANE_RE)] && $::env(OT_LANE_RE) ne "" ? $::env(OT_LANE_RE) : {^(u_g_t_[0-9a-z]+_u_l8\.g_d\\?\[[0-9]+\\?\])[./]}}]
set lf_fill [expr {[info exists ::env(OT_LANE_FILL)] ? $::env(OT_LANE_FILL) : 0.65}]
set lf_blk [ord::get_db_block]
set lf_u [[ord::get_db_tech] getDbUnitsPerMicron]
set lf_core [$lf_blk getCoreArea]
set lf_x0 [$lf_core xMin]; set lf_y0 [$lf_core yMin]; set lf_x1 [$lf_core xMax]; set lf_y1 [$lf_core yMax]
set lf_mem [dict create]; set lf_area [dict create]
foreach i [$lf_blk getInsts] {
  if {![[$i getMaster] isCore]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED}} continue
  if {![regexp $lf_re [$i getName] -> k]} continue
  dict lappend lf_mem $k $i
  dict set lf_area $k [expr {([dict exists $lf_area $k] ? [dict get $lf_area $k] : 0.0) + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight]}]
}
proc lf_key {k} {
  set t ""; set d 0
  regexp {u_g_t_([0-9a-z]+)_} $k -> t; regexp {g_d\\?\[([0-9]+)} $k -> d
  if {[string is integer -strict $t]} { set t [format %04d $t] }
  return "$t:[format %04d $d]"
}
set lf_keys [lsort -command {apply {{a b} {string compare [lf_key $a] [lf_key $b]}}} [dict keys $lf_mem]]
set lf_n [llength $lf_keys]
if {$lf_n < 2} {
  puts "OT_LANE_FENCE $lf_n lanes: nothing to fence"
} else {
  set lf_cols [expr {int(ceil(sqrt($lf_n)))}]
  set lf_rows [expr {int(ceil(double($lf_n) / $lf_cols))}]
  set cw [expr {double($lf_x1 - $lf_x0) / $lf_cols}]; set ch [expr {double($lf_y1 - $lf_y0) / $lf_rows}]
  set j 0
  foreach k $lf_keys {
    set r [expr {$j / $lf_cols}]; set c [expr {$j % $lf_cols}]
    if {$r % 2} { set c [expr {$lf_cols - 1 - $c}] }
    set side [expr {sqrt([dict get $lf_area $k] / $lf_fill)}]
    set bw [expr {min($cw, max($side, [dict get $lf_area $k] / $lf_fill / $ch))}]
    set bh [expr {min($ch, [dict get $lf_area $k] / $lf_fill / $bw)}]
    set cx [expr {$lf_x0 + ($c + 0.5) * $cw}]; set cy [expr {$lf_y0 + ($r + 0.5) * $ch}]
    set nm "ot_lane_fence_$j"
    set reg [odb::dbRegion_create $lf_blk $nm]
    $reg setRegionType INCLUSIVE
    odb::dbBox_create $reg [expr {round($cx - $bw / 2)}] [expr {round($cy - $bh / 2)}] [expr {round($cx + $bw / 2)}] [expr {round($cy + $bh / 2)}]
    set g [odb::dbGroup_create $reg $nm]
    $g setType VOLTAGE_DOMAIN
    foreach i [dict get $lf_mem $k] { $g addInst $i }
    puts [format "OT_LANE_FENCE %s %s cells %d area %.0f um2 box %.1f %.1f %.1f %.1f" $nm $k [llength [dict get $lf_mem $k]] [expr {[dict get $lf_area $k] / $lf_u / $lf_u}] [expr {($cx - $bw / 2) / $lf_u}] [expr {($cy - $bh / 2) / $lf_u}] [expr {($cx + $bw / 2) / $lf_u}] [expr {($cy + $bh / 2) / $lf_u}]]
    incr j
  }
  puts "OT_LANE_FENCE $lf_n lane regions on a ${lf_cols}x${lf_rows} grid (fill $lf_fill; GPL guide, released before DPL)"
}
}
