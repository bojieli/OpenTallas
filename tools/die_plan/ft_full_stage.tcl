# Exact complete normal-FT map. Validate everything before moving any target.
uplevel #0 {
if {[info exists ff_full_outline]} {
  set die [$ff_blk getDieArea]
  if {abs(([$die xMax]-[$die xMin])/double($ff_dbu)-[lindex $ff_full_outline 0])>0.001 || abs(([$die yMax]-[$die yMin])/double($ff_dbu)-[lindex $ff_full_outline 1])>0.001} {error "FT_FULL_STAGE stale actual die outline"}
}
set ff_full_owned {}; set ff_full_rects {}; set ff_full_rows {}
foreach r [$ff_blk getRows] {
  lassign [$r getOrigin] x y
  set s [$r getSite]; set box [$r getBBox]
  dict lappend ff_full_rows $y [list $x [$box xMax] [$s getWidth] [$s getHeight] [$r getOrient]]
}
foreach r $ff_full_targets {
  lassign $r slot stage bit name master x y w h
  set i [$ff_blk findInst $name]
  if {$i eq "NULL" || $i eq "" || ![ff_is_ff $i] || [[$i getMaster] getName] ne $master} {error "FT_FULL_STAGE stale actual cell $name/$master"}
  set m [$i getMaster]
  foreach {value actual} [list $w [$m getWidth] $h [$m getHeight]] {
    if {abs($value*$ff_dbu-$actual)>1} {error "FT_FULL_STAGE stale footprint $name"}
  }
  set X [expr {round($x*$ff_dbu)}]; set Y [expr {round($y*$ff_dbu)}]
  set W [$m getWidth]; set H [$m getHeight]; set orient ""
  if {[dict exists $ff_full_rows $Y]} {
    foreach row [dict get $ff_full_rows $Y] {
      lassign $row x0 x1 sw rh o
      if {$H==$rh && $X >= $x0 && $X+$W <= $x1 && ($X-$x0)%$sw==0} {set orient $o; break}
    }
  }
  if {$orient eq "" || $X<$ff_x0 || $Y<$ff_y0 || $X+$W>$ff_x1 || $Y+$H>$ff_y1} {error "FT_FULL_STAGE not a legal core row/site $name"}
  dict set ff_full_owned $name 1
  dict set ff_full_rects $name [list $X $Y [expr {$X+$W}] [expr {$Y+$H}] $orient]
}
# Index chains once: this stays linear in actual bits/stages, not all-target squared.
set ff_full_expected {}; set ff_full_inputs {}
foreach r $ff_full_targets {
  lassign $r slot stage bit name
  dict set ff_full_expected [list $slot $stage $bit] $name
  if {$stage==0} {dict set ff_full_inputs $name [list $slot $bit]}
}
set ff_full_seen {}; set ff_full_pin_distances {}
foreach bt [$ff_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set slot [ff_slot_of [$bt getName] _i]
  if {![dict exists $ff_full_slots $slot]} continue
  set f [ff_from_in [$bt getNet] 0]
  if {$f eq "" || ![dict exists $ff_full_inputs [$f getName]]} {error "FT_FULL_STAGE unlisted actual input [$bt getName]"}
  lassign [dict get $ff_full_inputs [$f getName]] sl bit
  if {![regexp {\[([0-9]+)\]$} [$bt getName] -> actualbit] || $actualbit!=$bit} {error "FT_FULL_STAGE stale port-bit identity [$bt getName]"}
  if {$sl ne $slot || [dict exists $ff_full_seen [list $slot $bit]] || [ff_lands_ring [$bt getNet]]} {error "FT_FULL_STAGE aliased/landed input $slot/$bit"}
  dict set ff_full_seen [list $slot $bit] 1
  set onm [string map [list "${slot}_i" "${slot}_o"] [$bt getName]]
  set ob [$ff_blk findBTerm $onm]
  set k [dict get $ff_full_slots $slot]
  if {$ob eq "NULL" || $ob eq ""} {error "FT_FULL_STAGE absent output $onm"}
  foreach port [list $bt $ob] j [list 0 [expr {$k-1}]] {
    set name [dict get $ff_full_expected [list $slot $j $bit]]
    lassign [dict get $ff_full_rects $name] x0 y0 x1 y1
    set bb [$port getBBox]
    set distance [expr {(abs(($x0+$x1-[$bb xMin]-[$bb xMax])/2.0)+abs(($y0+$y1-[$bb yMin]-[$bb yMax])/2.0))/$ff_dbu}]
    if {$distance>150.000001} {error "FT_FULL_STAGE pin distance exceeds 150um $name"}
    lappend ff_full_pin_distances $distance
  }
  set chain [ff_landed_stations [$ob getNet] $k]
  if {[llength $chain]!=$k} {error "FT_FULL_STAGE broken k-chain $slot/$bit"}
  for {set j 0} {$j<$k} {incr j} {
    if {[dict get $ff_full_expected [list $slot $j $bit]] ne [[lindex $chain $j] getName]} {error "FT_FULL_STAGE stale chain $slot/$bit/$j"}
  }
}
if {[dict size $ff_full_seen]!=[dict size $ff_full_inputs]} {error "FT_FULL_STAGE missing actual input bits"}
set distances [lsort -real $ff_full_pin_distances]
set p90 [lindex $distances [expr {int(ceil(0.9*[llength $distances]))-1}]]
if {$p90>30.000001} {error "FT_FULL_STAGE endpoint pin p90 exceeds 30um: $p90"}
# Row buckets include fixed taps, macros, hard placement blockages and other fixed reservations.
set ff_full_buckets {}
proc ff_full_obstacle {name rect} {
  global ff_full_buckets ff_rh
  lassign $rect x0 y0 x1 y1
  for {set row [expr {int(floor(double($y0)/$ff_rh))}]} {$row*$ff_rh<$y1} {incr row} {
    dict lappend ff_full_buckets $row [list $name $x0 $y0 $x1 $y1]
  }
}
foreach i [$ff_blk getInsts] {
  if {[dict exists $ff_full_owned [$i getName]]} continue
  set m [$i getMaster]
  if {[$m isBlock] || [$i getPlacementStatus] in {FIRM LOCKED COVER} || [string match *TAP* [$m getName]]} {
    set b [$i getBBox]; ff_full_obstacle [$i getName] [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
}
foreach b [$ff_blk getBlockages] {
  if {[$b isSoft] || [$b getMaxDensity]>0} continue
  set box [$b getBBox]; ff_full_obstacle blockage [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
}
foreach name [dict keys $ff_full_rects] {
  lassign [dict get $ff_full_rects $name] x0 y0 x1 y1 o
  set row [expr {int(floor(double($y0)/$ff_rh))}]
  if {[dict exists $ff_full_buckets $row]} {
    foreach obstacle [dict get $ff_full_buckets $row] {
      lassign $obstacle other a b c d
      if {$x0<$c && $a<$x1 && $y0<$d && $b<$y1} {error "FT_FULL_STAGE obstacle $name overlaps $other"}
    }
  }
  ff_full_obstacle $name [list $x0 $y0 $x1 $y1]
}
if {![info exists ::ff_full_validate_only] || !$::ff_full_validate_only} {
set log [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach name [dict keys $ff_full_rects] {
  lassign [dict get $ff_full_rects $name] x y xx yy orient
  set i [$ff_blk findInst $name]; $i setOrient $orient; $i setLocation $x $y; $i setPlacementStatus FIRM
  puts $log "$name\tfullstage\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\texact"
}
close $log
}
puts "FT_FULL_STAGE exact_existing_flops=[dict size $ff_full_rects] data_cycles_added=0"
}
