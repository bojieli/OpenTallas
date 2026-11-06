# Opt-in native hard-macro clock plan. Run in OpenROAD with IN, PLAN,
# OT_LANDING_MASTER and OT_LANDING_COUNT; output is a fresh private checkpoint.
# No wire or original port is changed here. Every actual enclosure/grid is native.
foreach key {IN PLAN OT_LANDING_MASTER OT_LANDING_COUNT} {
  if {![info exists ::env($key)] || $::env($key) eq ""} {error "OT_CLAND missing $key"}
}
if {[file exists $::env(PLAN)] || [file normalize $::env(IN)] eq [file normalize $::env(PLAN)]} {
  error "OT_CLAND output must be fresh and distinct"
}
read_db $::env(IN)
set b [ord::get_db_block]; set t [ord::get_db_tech]; set u [$t getDbUnitsPerMicron]
set m5 [$t findLayer M5]; set m6 [$t findLayer M6]; set via [$t findVia VIA56]
if {$m5 eq "NULL" || $m6 eq "NULL" || $via eq "NULL"} {error "OT_CLAND requires native M5/M6/VIA56"}
if {[$via getBottomLayer] ne $m5 || [$via getTopLayer] ne $m6} {error "OT_CLAND VIA56 layer mismatch"}
proc via_enclosure {via layer} {
  set boxes {}; foreach box [$via getBoxes] {if {[$box getTechLayer] eq $layer} {lappend boxes [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
  if {[llength $boxes] != 1} {error "OT_CLAND requires one native via enclosure on [$layer getName]"}
  return [lindex $boxes 0]
}
lassign [via_enclosure $via $m5] vl vb vr vt
lassign [via_enclosure $via $m6] ul ub ur ut
set gx [$b findTrackGrid $m5]; set gy [$b findTrackGrid $m6]
if {$gx eq "NULL" || $gy eq "NULL"} {error "OT_CLAND missing native track grid"}
set xs [$gx getGridX]; set ys [$gy getGridY]
proc closest_in {tracks lo hi target} {
  set best ""; foreach q $tracks {if {$q >= $lo && $q <= $hi && ($best eq "" || abs($q-$target)<abs($best-$target))} {set best $q}}
  if {$best eq ""} {error "OT_CLAND no legal native track in interval $lo..$hi"}
  return $best
}
# Preserve actual M6 PG and its spacing. This is not a substitute for final DRC.
set obstacles {}
foreach net [$b getNets] {foreach sw [$net getSWires] {foreach box [$sw getWires] {if {[$box getTechLayer] eq $m6} {lappend obstacles [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}}}
set spacing [$m6 getSpacing]
set half [expr {max(abs($ub),abs($ut),[$m6 getWidth]/2)}]
puts "OT_CLAND TECH M5via=[list $vl $vb $vr $vt] M6via=[list $ul $ub $ur $ut] M6spacing=$spacing M6width=[$m6 getWidth]"
set plans {}; set seen {}
foreach inst [$b getInsts] {
  if {[[$inst getMaster] getName] ne $::env(OT_LANDING_MASTER)} continue
  if {[$inst getOrient] ne "R0"} {error "OT_CLAND only measured R0 orientation is supported"}
  foreach obs [[$inst getMaster] getObstructions] {
    set layer [$obs getTechLayer]
    if {[$layer getType] eq "ROUTING" && [$layer getRoutingLevel] >= [$m6 getRoutingLevel]} {error "OT_CLAND M6 escape requires actual child OBS below M6"}
  }
  set it [$inst findITerm clk]
  if {$it eq "NULL" || [$it getNet] eq "NULL"} {error "OT_CLAND missing connected native clk"}
  set net [$it getNet]
  if {[$net getSigType] ne "CLOCK" || [llength [$net getBTerms]] || [llength [$net getITerms]] != 2} {error "OT_CLAND expected exactly one driver/one receiver CLOCK net"}
  if {[$net getNonDefaultRule] ne "NULL"} {error "OT_CLAND native NDR unsupported"}
  set driver ""; foreach other [$net getITerms] {if {$other ne $it} {set driver $other}}
  if {[$driver getIoType] ne "OUTPUT" || [[[$driver getInst] getMaster] isBlock]} {error "OT_CLAND expected real standard-cell output driver"}
  if {[dict exists $seen [$net getName]]} {error "OT_CLAND duplicate selected clock net"}
  dict set seen [$net getName] 1
  set shapes {}; foreach mp [[$it getMTerm] getMPins] {foreach box [$mp getGeometry] {if {[$box getTechLayer] ne $m5} {error "OT_CLAND native clk must have only M5 rectangles"}; lappend shapes $box}}
  if {[llength $shapes] != 1} {error "OT_CLAND requires one actual native clk PORT rectangle"}
  set pb [$it getBBox]; set mb [$inst getBBox]
  set px [closest_in $xs [expr {[$pb xMin]-$vl}] [expr {[$pb xMax]-$vr}] [expr {([$pb xMin]+[$pb xMax])/2}]]
  set left [expr {$px-[$mb xMin] < [$mb xMax]-$px}]
  set wanted [expr {$left ? [$mb xMin]-round(.3*$u) : [$mb xMax]+round(.3*$u)}]
  set xe [closest_in $xs [lindex $xs 0] [lindex $xs end] $wanted]
  if {($left && $xe+$vr >= [$mb xMin]) || (!$left && $xe+$vl <= [$mb xMax])} {error "OT_CLAND outside takeoff still intersects macro"}
  set ylo [expr {[$pb yMin]-$vb}]; set yhi [expr {[$pb yMax]-$vt}]; set ypick ""
  foreach y $ys {
    if {$y<$ylo || $y>$yhi} continue
    set x0 [expr {min($xe,$px)+min($ul,-[$m6 getWidth]/2)-$spacing}]
    set x1 [expr {max($xe,$px)+max($ur,[$m6 getWidth]/2)+$spacing}]
    set blocked 0
    foreach box $obstacles {lassign $box a c d e; if {$a<$x1 && $d>$x0 && $c<$y+$half+$spacing && $e>$y-$half-$spacing} {set blocked 1; break}}
    if {!$blocked} {set ypick $y; break}
  }
  if {$ypick eq ""} {error "OT_CLAND no PG-clear M6 track inside real PORT"}
  set down [expr {[$pb yMin]-[$mb yMin] < [$mb yMax]-[$pb yMax]}]
  set stub [expr {$ypick+($down ? -1:1)*round(.6*$u)}]
  lappend plans [list $net $inst $driver $px $ypick $xe $stub]
}
if {[llength $plans] != $::env(OT_LANDING_COUNT)} {error "OT_CLAND selected count [llength $plans], expected $::env(OT_LANDING_COUNT)"}
set f [open $::env(PLAN) w]
foreach plan $plans {
  lassign $plan net inst driver px py xe stub
  puts $f [join [list [$net getName] $px $py $xe $stub] \t]
}
close $f
puts "OT_CLAND PLAN [llength $plans] native M5/VIA56/M6; 0 added cycles"
