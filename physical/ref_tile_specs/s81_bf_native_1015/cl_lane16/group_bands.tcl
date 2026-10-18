# PRE_GLOBAL_PLACE hook (spec pin_hook_before_flops) for ot_v41_bf_lane16_cl (S-ELEM BF-COL, 2026-10-17).
# lane16 = four ot_v41_bf_lane4_cl groups u_g0..u_g3, one CTS root per group (fclk<g>), and a per-group quarter-face
# pin plan (group g owns the W and E pins in y = [g, g+1) * H/4).  Without regions, global placement mixed the four
# groups over the whole 164 x 194 um outline: r4b CTS average sink wire 166-186 um per root (lane4_cl alone: 106 um),
# FF hold ws -66 ps on 18,015 endpoints and a stalled hold repair (16k+ buffers, TNS flat).  This hook gives each
# group an EXCLUSIVE band region (the full core width, its own quarter of the core height, matching its pins), so each
# root's tree covers one quarter of the tile.  Membership: every non-fixed instance whose name starts with u_g<g>.
# Fails closed on any unowned movable instance or a band whose row fill would exceed 0.70.
set lbg_block [ord::get_db_block]
set lbg_dbu [$lbg_block getDbUnitsPerMicron]
set lbg_core [$lbg_block getCoreArea]
set lbg_die [$lbg_block getDieArea]
set lbg_x0 [$lbg_core xMin]; set lbg_x1 [$lbg_core xMax]
set lbg_cy0 [$lbg_core yMin]; set lbg_cy1 [$lbg_core yMax]
set lbg_dh [expr {[$lbg_die yMax] - [$lbg_die yMin]}]
set lbg_members [dict create]
set lbg_orphan {}
foreach inst [$lbg_block getInsts] {
  if {[$inst isFixed]} { continue }
  set master [$inst getMaster]
  if {[$master isBlock] || [$master isPad]} { continue }
  set name [string map [list "\\" ""] [$inst getName]]
  if {[regexp {^u_g([0-3])[./]} $name -> g]} {
    dict lappend lbg_members $g $inst
  } else {
    lappend lbg_orphan $name
  }
}
# ABC renames the flattened combinational cells (_090596_): each joins the group it is wired to, by a breadth-first
# walk over signal nets from the named cells (the four groups share no logic, so a cell wired to two groups is an error).
array set lbg_of {}
set lbg_queue {}
dict for {g insts} $lbg_members { foreach i $insts { set lbg_of([$i getName]) $g; lappend lbg_queue $i } }
set lbg_conflict 0
set qi 0
while {$qi < [llength $lbg_queue]} {
  set i [lindex $lbg_queue $qi]; incr qi
  set g $lbg_of([$i getName])
  foreach it [$i getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || $n eq "" || [$n getSigType] in {POWER GROUND CLOCK}} { continue }
    if {[llength [$n getITerms]] > 2000} { continue }
    foreach o [$n getITerms] {
      set j [$o getInst]
      set jn [$j getName]
      if {[info exists lbg_of($jn)]} {
        if {$lbg_of($jn) ne $g} { incr lbg_conflict }
        continue
      }
      if {[$j isFixed] || [[$j getMaster] isBlock]} { continue }
      set lbg_of($jn) $g; dict lappend lbg_members $g $j; lappend lbg_queue $j
    }
  }
}
set lbg_left {}
foreach name $lbg_orphan { if {![info exists lbg_of($name)] && ![info exists lbg_of([string map [list "\\" ""] $name])]} { lappend lbg_left $name } }
if {$lbg_conflict} { error "LANE16_BANDS: $lbg_conflict nets join two groups" }
if {[llength $lbg_left]} {
  error "LANE16_BANDS: [llength $lbg_left] movable instances not wired to u_g0..u_g3, e.g. [lrange $lbg_left 0 4]"
}
puts "LANE16_BANDS walk: [llength $lbg_orphan] unnamed cells joined their group"
set lbg_report [open lane16_group_bands.tsv w]
puts $lbg_report "group\tinsts\tcell_area_um2\trow_capacity_um2\tfill\ty0_um\ty1_um"
for {set g 0} {$g < 4} {incr g} {
  if {![dict exists $lbg_members $g]} { error "LANE16_BANDS: group u_g$g has no instances" }
  # band edges: the group's pin quarter of the die height, clipped to the core and snapped to the row grid below
  set y0 [expr {max($lbg_cy0, [$lbg_die yMin] + round($g * $lbg_dh / 4.0))}]
  set y1 [expr {min($lbg_cy1, [$lbg_die yMin] + round(($g + 1) * $lbg_dh / 4.0))}]
  set rows [$lbg_block getRows]
  set rh [[[lindex $rows 0] getSite] getHeight]
  set y0 [expr {$lbg_cy0 + (($y0 - $lbg_cy0) / $rh) * $rh}]
  set y1 [expr {$g == 3 ? $lbg_cy1 : $lbg_cy0 + (($y1 - $lbg_cy0) / $rh) * $rh}]
  set region [odb::dbRegion_create $lbg_block lane16_g$g]
  $region setRegionType EXCLUSIVE
  odb::dbBox_create $region $lbg_x0 $y0 $lbg_x1 $y1
  set group [odb::dbGroup_create $region lane16_g$g]
  set area 0.0
  foreach inst [dict get $lbg_members $g] {
    if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} { error "LANE16_BANDS: already grouped: [$inst getName]" }
    $group addInst $inst
    set m [$inst getMaster]
    set area [expr {$area + double([$m getWidth]) * [$m getHeight] / ($lbg_dbu * $lbg_dbu)}]
  }
  set cap 0.0
  foreach row $rows {
    set bb [$row getBBox]
    set ov [expr {max(0, min($lbg_x1, [$bb xMax]) - max($lbg_x0, [$bb xMin])) * max(0, min($y1, [$bb yMax]) - max($y0, [$bb yMin]))}]
    set cap [expr {$cap + double($ov) / ($lbg_dbu * $lbg_dbu)}]
  }
  set fill [expr {$cap > 0 ? $area / $cap : 99}]
  puts $lbg_report "u_g$g\t[llength [dict get $lbg_members $g]]\t[format %.1f $area]\t[format %.1f $cap]\t[format %.3f $fill]\t[expr {$y0/double($lbg_dbu)}]\t[expr {$y1/double($lbg_dbu)}]"
  puts "LANE16_BANDS u_g$g insts [llength [dict get $lbg_members $g]] area [format %.1f $area] capacity [format %.1f $cap] fill [format %.3f $fill] y [expr {$y0/double($lbg_dbu)}]..[expr {$y1/double($lbg_dbu)}]"
  if {$fill > 0.70} { error "LANE16_BANDS: u_g$g fill $fill > 0.70" }
}
close $lbg_report
puts "LANE16_BANDS PASS 4 EXCLUSIVE bands"
